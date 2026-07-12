#!/usr/bin/env python3
"""DTLarchive - extrait des connaissances de conversations ChatGPT et les compare à la KB DTL4u."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

APP_NAME = "DTLarchive"
APP_VERSION = "v1.0.0"
SCHEMA_VERSION = "1.0"

TECH_KEYWORDS = {
    "windows": 3, "windows 10": 4, "windows 11": 4, "powershell": 4, "cmd": 3,
    "reseau": 3, "network": 3, "ethernet": 4, "wifi": 3, "dns": 5, "dhcp": 5,
    "smb": 6, "partage": 4, "unc": 5, "net use": 6, "net view": 6,
    "erreur 53": 7, "erreur 67": 7, "erreur 86": 7, "erreur 1326": 7,
    "1272": 6, "6118": 6, "ping": 4, "test-netconnection": 6, "port 445": 7,
    "ipv4": 5, "ipv6": 5, "pare-feu": 4, "firewall": 4, "ntfs": 5,
    "identification": 3, "credentials": 4, "mot de passe": 2,
    "imprimante": 4, "printer": 4, "scan": 3, "rdp": 5, "bureau a distance": 5,
    "service": 2, "fdrespub": 7, "lanmanserver": 7, "registre": 3,
    "glpi": 6, "xampp": 5, "apache": 4, "mariadb": 4, "php": 3,
    "sauvegarde": 4, "backup": 4, "robocopy": 6, "efs": 6, "certificat": 2,
    "excel": 2, "chiffre": 3, "pilote": 3, "driver": 3, "ecran": 2,
    "python": 3, "script": 2, "git": 3, "github": 3, "pyinstaller": 5,
}

NOISE_KEYWORDS = {
    "film", "serie", "acteur", "actrice", "roman", "vin", "restaurant",
    "jeu", "arc raiders", "gta", "netflix", "politique", "presidentielle",
    "recette", "chanson", "biopic",
}

CONFIRMATION_PATTERNS = [
    r"\b(ca marche|ça marche|resolu|résolu|corrige|corrigé|fonctionne|ok maintenant)\b",
    r"\b(aucun changement|toujours pareil|ne marche pas|n'a pas marche|n’a pas marché)\b",
    r"\b(j'ai trouve|j’ai trouvé|la cause etait|la cause était|c'etait|c’était)\b",
]
SUCCESS_PATTERNS = [
    r"\b(ca marche|ça marche|resolu|résolu|corrige|corrigé|fonctionne|instantane|instantané)\b",
    r"\b(ok|reussi|réussi)\b",
]
FAILURE_PATTERNS = [
    r"\b(aucun changement|toujours pareil|ne marche pas|n'a pas marche|n’a pas marché)\b",
    r"\b(erreur|echec|échec|impossible)\b",
]
COMMAND_RE = re.compile(
    r"(?im)^\s*(?:PS [^>]*>\s*)?(?P<cmd>"
    r"(?:ping|ipconfig|net(?:sh)?|sc|reg|route|arp|nslookup|tracert|pathping|"
    r"Test-NetConnection|Get-[A-Za-z0-9_-]+|Set-[A-Za-z0-9_-]+|"
    r"Get-CimInstance|Get-WmiObject|curl|robocopy|sfc|dism|chkdsk|tasklist|"
    r"systeminfo|whoami|dir|type|python|py|git)\b[^\r\n]*)"
)
ERROR_CODE_RE = re.compile(r"\b(?:erreur\s*)?(53|67|86|1272|1326|6118)\b", re.I)
PATH_RE = re.compile(r"\\\\[A-Za-z0-9_.-]+\\[^\s\"']+|[A-Za-z]:\\[^\r\n\"']+", re.I)


@dataclass
class Message:
    id: str
    role: str
    text: str
    create_time: float | None = None


@dataclass
class Conversation:
    source_file: str
    id: str
    title: str
    create_time: float | None
    update_time: float | None
    messages: list[Message]


@dataclass
class KnowledgeCandidate:
    id: str
    source_file: str
    conversation_id: str
    conversation_title: str
    start_message_id: str
    end_message_id: str
    score: int
    status: str
    confidence: str
    user_confirmed: bool
    problem: str
    context: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    assistant_proposals: list[str] = field(default_factory=list)
    outcome: str = ""
    error_codes: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    kb_match: dict[str, Any] = field(default_factory=dict)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", text).strip()


def compact(text: str, limit: int = 500) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = normalize(item)
        if item and key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def text_from_content(content: Any) -> str:
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if isinstance(parts, list):
        values: list[str] = []
        for part in parts:
            if isinstance(part, str):
                values.append(part)
            elif isinstance(part, dict):
                if isinstance(part.get("text"), str):
                    values.append(part["text"])
                elif isinstance(part.get("content"), str):
                    values.append(part["content"])
        return "\n".join(values).strip()
    text = content.get("text")
    return text.strip() if isinstance(text, str) else ""


def current_branch_messages(mapping: dict[str, Any], current_node: str | None) -> list[Message]:
    """Suit les parents depuis current_node. Repli chronologique si l'arbre est incomplet."""
    messages: list[Message] = []
    visited: set[str] = set()
    node_id = current_node
    while node_id and node_id in mapping and node_id not in visited:
        visited.add(node_id)
        node = mapping[node_id]
        raw = node.get("message")
        if isinstance(raw, dict):
            author = raw.get("author") or {}
            role = author.get("role") or ""
            text = text_from_content(raw.get("content"))
            if role in {"user", "assistant"} and text:
                messages.append(Message(
                    id=str(raw.get("id") or node_id),
                    role=role,
                    text=text,
                    create_time=raw.get("create_time"),
                ))
        node_id = node.get("parent")
    messages.reverse()
    if messages:
        return messages

    fallback: list[Message] = []
    for node_id, node in mapping.items():
        raw = node.get("message")
        if not isinstance(raw, dict):
            continue
        role = ((raw.get("author") or {}).get("role") or "")
        text = text_from_content(raw.get("content"))
        if role in {"user", "assistant"} and text:
            fallback.append(Message(str(raw.get("id") or node_id), role, text, raw.get("create_time")))
    return sorted(fallback, key=lambda m: (m.create_time is None, m.create_time or 0))


def iter_conversations(path: Path) -> Iterator[Conversation]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[AVERTISSEMENT] {path}: {exc}", file=sys.stderr)
        return
    records = payload if isinstance(payload, list) else [payload]
    for raw in records:
        if not isinstance(raw, dict):
            continue
        mapping = raw.get("mapping")
        if not isinstance(mapping, dict):
            continue
        messages = current_branch_messages(mapping, raw.get("current_node"))
        if not messages:
            continue
        yield Conversation(
            source_file=path.name,
            id=str(raw.get("conversation_id") or raw.get("id") or ""),
            title=str(raw.get("title") or "(sans titre)"),
            create_time=raw.get("create_time"),
            update_time=raw.get("update_time"),
            messages=messages,
        )


def technical_score(text: str) -> tuple[int, list[str]]:
    n = normalize(text)
    hits: list[str] = []
    score = 0
    for keyword, weight in TECH_KEYWORDS.items():
        if normalize(keyword) in n:
            score += weight
            hits.append(keyword)
    noise = sum(1 for keyword in NOISE_KEYWORDS if keyword in n)
    if noise and score < 8:
        score -= noise * 3
    if COMMAND_RE.search(text):
        score += 6
    if ERROR_CODE_RE.search(text):
        score += 5
    return score, hits


def make_windows(messages: Sequence[Message], max_gap: int = 2) -> list[list[Message]]:
    relevant = [technical_score(m.text)[0] >= 3 for m in messages]
    windows: list[list[Message]] = []
    start: int | None = None
    last_relevant: int | None = None
    for i, is_relevant in enumerate(relevant):
        if is_relevant:
            if start is None:
                start = max(0, i - 1)
            last_relevant = i
        elif start is not None and last_relevant is not None and i - last_relevant > max_gap:
            windows.append(list(messages[start:i]))
            start = None
            last_relevant = None
    if start is not None:
        windows.append(list(messages[start:]))
    return windows


def sentences(text: str) -> list[str]:
    clean = re.sub(r"```.*?```", " ", text, flags=re.S)
    chunks = re.split(r"(?<=[.!?])\s+|\n+", clean)
    return [compact(c, 320) for c in chunks if len(c.strip()) >= 12]


def extract_candidate(conv: Conversation, window: list[Message], index: int) -> KnowledgeCandidate | None:
    joined = "\n".join(m.text for m in window)
    score, hits = technical_score(joined)
    if score < 8:
        return None

    users = [m for m in window if m.role == "user"]
    assistants = [m for m in window if m.role == "assistant"]
    if not users:
        return None

    user_confirmed = any(
        re.search(pattern, normalize(m.text), re.I)
        for m in users for pattern in CONFIRMATION_PATTERNS
    )
    success = any(re.search(p, normalize(m.text), re.I) for m in users for p in SUCCESS_PATTERNS)
    failure = any(re.search(p, normalize(m.text), re.I) for m in users for p in FAILURE_PATTERNS)

    if success:
        status = "CONFIRMED_SUCCESS"
        confidence = "high"
    elif user_confirmed and failure:
        status = "CONFIRMED_FAILURE"
        confidence = "high"
    elif user_confirmed:
        status = "USER_CONFIRMED"
        confidence = "medium"
    else:
        status = "UNVERIFIED"
        confidence = "low"

    problem = compact(users[0].text, 700)
    observations: list[str] = []
    context: list[str] = []
    for m in users:
        for sentence in sentences(m.text):
            n = normalize(sentence)
            if any(token in n for token in ("j'ai", "j’ai", "il y a", "affiche", "renvoie", "erreur", "depuis", "sur ", "avec ")):
                observations.append(sentence)
            else:
                context.append(sentence)

    proposals: list[str] = []
    for m in assistants:
        for sentence in sentences(m.text):
            if any(token in normalize(sentence) for token in (
                "verifier", "essayez", "lancez", "ouvrez", "solution", "cause",
                "corriger", "utilisez", "commande", "il faut",
            )):
                proposals.append(sentence)

    commands = unique(m.group("cmd").strip() for m in COMMAND_RE.finditer(joined))
    errors = sorted(set(ERROR_CODE_RE.findall(joined)), key=int)
    paths = unique(PATH_RE.findall(joined))

    outcome = ""
    for m in reversed(users):
        if any(re.search(p, normalize(m.text), re.I) for p in CONFIRMATION_PATTERNS):
            outcome = compact(m.text, 700)
            break

    digest = hashlib.sha256(
        f"{conv.source_file}|{conv.id}|{window[0].id}|{window[-1].id}".encode("utf-8")
    ).hexdigest()[:16]
    return KnowledgeCandidate(
        id=f"KA-{digest}",
        source_file=conv.source_file,
        conversation_id=conv.id,
        conversation_title=conv.title,
        start_message_id=window[0].id,
        end_message_id=window[-1].id,
        score=score,
        status=status,
        confidence=confidence,
        user_confirmed=user_confirmed,
        problem=problem,
        context=unique(context)[:12],
        commands=commands[:20],
        observations=unique(observations)[:20],
        assistant_proposals=unique(proposals)[:20],
        outcome=outcome,
        error_codes=errors,
        paths=paths[:20],
        keywords=sorted(set(hits)),
    )


def flatten_strings(value: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from flatten_strings(child, child_path)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from flatten_strings(child, f"{path}[{i}]")
    elif isinstance(value, str) and value.strip():
        yield path, value


def token_set(text: str) -> set[str]:
    stop = {
        "avec", "dans", "pour", "que", "qui", "une", "des", "les", "est", "sur",
        "pas", "plus", "vous", "nous", "the", "and", "this", "that", "from",
    }
    return {t for t in re.findall(r"[a-z0-9]{3,}", normalize(text)) if t not in stop}


def compare_with_kb(candidate: KnowledgeCandidate, kb_strings: list[tuple[str, str]]) -> dict[str, Any]:
    query = " ".join([
        candidate.problem, candidate.outcome,
        " ".join(candidate.commands), " ".join(candidate.observations),
        " ".join(candidate.error_codes),
    ])
    qtokens = token_set(query)
    scored: list[tuple[float, str, str]] = []
    for path, text in kb_strings:
        tokens = token_set(text)
        if not tokens or not qtokens:
            continue
        overlap = len(qtokens & tokens)
        if not overlap:
            continue
        score = overlap / max(1, min(len(qtokens), len(tokens)))
        if any(code in text for code in candidate.error_codes):
            score += 0.20
        scored.append((min(score, 1.0), path, compact(text, 240)))
    scored.sort(reverse=True)
    best = scored[:5]
    top = best[0][0] if best else 0.0

    if candidate.status == "UNVERIFIED":
        classification = "UNVERIFIED"
    elif top >= 0.72:
        classification = "EXISTING"
    elif top >= 0.38:
        classification = "ENRICH"
    else:
        classification = "NEW"

    return {
        "classification": classification,
        "similarity": round(top, 3),
        "matches": [
            {"score": round(score, 3), "path": path, "text": text}
            for score, path, text in best
        ],
    }


def load_kb(path: Path) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("La KB doit être un objet JSON.")
    return payload, list(flatten_strings(payload))


def candidate_addition(candidate: KnowledgeCandidate) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "title": compact(candidate.problem, 120),
        "problem": candidate.problem,
        "context": candidate.context,
        "observations": candidate.observations,
        "commands": candidate.commands,
        "outcome": candidate.outcome,
        "error_codes": candidate.error_codes,
        "confidence": candidate.confidence,
        "provenance": {
            "source_file": candidate.source_file,
            "conversation_id": candidate.conversation_id,
            "conversation_title": candidate.conversation_title,
            "start_message_id": candidate.start_message_id,
            "end_message_id": candidate.end_message_id,
            "user_confirmed": candidate.user_confirmed,
        },
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_html_report(path: Path, candidates: list[KnowledgeCandidate], stats: dict[str, Any]) -> None:
    rows = []
    for c in candidates:
        cls = c.kb_match.get("classification", "")
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(c.id)}</code></td>"
            f"<td>{html.escape(c.conversation_title)}</td>"
            f"<td>{html.escape(c.status)}</td>"
            f"<td>{html.escape(cls)}</td>"
            f"<td>{c.score}</td>"
            f"<td>{html.escape(compact(c.problem, 220))}</td>"
            f"<td>{html.escape(compact(c.outcome, 180))}</td>"
            "</tr>"
        )
    cards = "".join(
        f"<div class='stat'><strong>{html.escape(str(value))}</strong><span>{html.escape(str(key))}</span></div>"
        for key, value in stats.items()
    )
    doc = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<title>{APP_NAME} {APP_VERSION}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#0b0d0f;color:#e8eaed}}
header,main{{max-width:1500px;margin:auto;padding:24px}}
h1{{margin-bottom:4px}} .muted{{color:#9aa0a6}}
.stats{{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}}
.stat{{background:#171a1f;border:1px solid #30363d;border-radius:8px;padding:14px 18px;min-width:130px}}
.stat strong{{display:block;font-size:24px}} .stat span{{color:#9aa0a6}}
table{{width:100%;border-collapse:collapse;background:#131619}}
th,td{{padding:10px;border:1px solid #30363d;vertical-align:top;text-align:left}}
th{{position:sticky;top:0;background:#20242a}} tr:hover{{background:#1a1f25}}
code{{color:#79c0ff}} a{{color:#58a6ff}}
</style></head><body>
<header><h1>{APP_NAME} {APP_VERSION}</h1>
<div class="muted">Rapport généré le {dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</div>
<div class="stats">{cards}</div></header>
<main><table><thead><tr>
<th>ID</th><th>Conversation</th><th>Validation</th><th>Comparaison KB</th>
<th>Score</th><th>Problème</th><th>Résultat utilisateur</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table></main>
</body></html>"""
    path.write_text(doc, encoding="utf-8")


def apply_additions(kb: dict[str, Any], additions: list[dict[str, Any]], output: Path) -> None:
    archive = kb.setdefault("archive_additions", {})
    if not isinstance(archive, dict):
        raise ValueError("La clé archive_additions existe mais n'est pas un objet.")
    existing = archive.setdefault("knowledge", [])
    if not isinstance(existing, list):
        raise ValueError("archive_additions.knowledge n'est pas une liste.")
    existing_ids = {item.get("id") for item in existing if isinstance(item, dict)}
    existing.extend(item for item in additions if item.get("id") not in existing_ids)
    archive["schema_version"] = SCHEMA_VERSION
    archive["generated_by"] = f"{APP_NAME} {APP_VERSION}"
    archive["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    write_json(output, kb)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrait les connaissances techniques d'exports ChatGPT et les compare à la KB DTL4u."
    )
    parser.add_argument("inputs", nargs="*", type=Path, help="fichiers conversations-*.json ou dossiers")
    parser.add_argument("--kb", type=Path, required=True, help="dtl4u_kb.json")
    parser.add_argument("--output", type=Path, default=Path("DTLarchive-output"))
    parser.add_argument("--pattern", default="conversations-*.json")
    parser.add_argument("--min-score", type=int, default=8)
    parser.add_argument("--include-unverified", action="store_true")
    parser.add_argument("--apply", action="store_true", help="produire une KB enrichie sans modifier l'original")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    return parser.parse_args(argv)


def resolve_inputs(inputs: Sequence[Path], pattern: str) -> list[Path]:
    roots = list(inputs) or [Path(".")]
    files: list[Path] = []
    for root in roots:
        if root.is_dir():
            files.extend(root.glob(pattern))
        elif root.is_file():
            files.append(root)
    return sorted({path.resolve() for path in files})


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    files = resolve_inputs(args.inputs, args.pattern)
    if not files:
        print(f"[ERREUR] Aucun fichier {args.pattern} trouvé.", file=sys.stderr)
        return 2
    if not args.kb.is_file():
        print(f"[ERREUR] KB introuvable : {args.kb}", file=sys.stderr)
        return 2

    try:
        kb, kb_strings = load_kb(args.kb)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[ERREUR] Lecture KB : {exc}", file=sys.stderr)
        return 2

    candidates: list[KnowledgeCandidate] = []
    conversation_count = 0
    for source in files:
        for conv in iter_conversations(source):
            conversation_count += 1
            for index, window in enumerate(make_windows(conv.messages), start=1):
                candidate = extract_candidate(conv, window, index)
                if candidate and candidate.score >= args.min_score:
                    candidate.kb_match = compare_with_kb(candidate, kb_strings)
                    if args.include_unverified or candidate.status != "UNVERIFIED":
                        candidates.append(candidate)

    # Déduplication approximative par problème + résultat.
    deduped: dict[str, KnowledgeCandidate] = {}
    for c in candidates:
        key = hashlib.sha256(
            (normalize(c.problem)[:300] + "|" + normalize(c.outcome)[:200]).encode("utf-8")
        ).hexdigest()
        old = deduped.get(key)
        if old is None or c.score > old.score:
            deduped[key] = c
    candidates = sorted(
        deduped.values(),
        key=lambda c: (c.kb_match.get("classification", ""), -c.score, c.conversation_title),
    )

    args.output.mkdir(parents=True, exist_ok=True)
    extracted = {
        "metadata": {
            "application": APP_NAME,
            "version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source_files": [str(p) for p in files],
            "kb": str(args.kb.resolve()),
        },
        "knowledge": [asdict(c) for c in candidates],
    }
    write_json(args.output / "extracted_knowledge.json", extracted)

    groups: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        groups.setdefault(c.kb_match["classification"], []).append(asdict(c))
    write_json(args.output / "kb_comparison.json", {
        "metadata": extracted["metadata"],
        "groups": groups,
    })

    additions = [
        candidate_addition(c) for c in candidates
        if c.kb_match["classification"] in {"NEW", "ENRICH"} and c.user_confirmed
    ]
    conflicts = [
        asdict(c) for c in candidates
        if c.kb_match["classification"] == "CONFLICT"
    ]
    unverified = [
        asdict(c) for c in candidates if c.status == "UNVERIFIED"
    ]
    write_json(args.output / "kb_additions.json", {
        "metadata": extracted["metadata"], "knowledge": additions
    })
    write_json(args.output / "kb_conflicts.json", {
        "metadata": extracted["metadata"], "knowledge": conflicts
    })
    write_json(args.output / "unverified.json", {
        "metadata": extracted["metadata"], "knowledge": unverified
    })

    classes = Counter(c.kb_match["classification"] for c in candidates)
    stats = {
        "Fichiers": len(files),
        "Conversations": conversation_count,
        "Candidats": len(candidates),
        "Confirmés": sum(c.user_confirmed for c in candidates),
        "Nouveaux": classes["NEW"],
        "À enrichir": classes["ENRICH"],
        "Existants": classes["EXISTING"],
        "Non vérifiés": classes["UNVERIFIED"],
    }
    write_html_report(args.output / "DTLarchive-report.html", candidates, stats)

    if args.apply:
        apply_additions(kb, additions, args.output / "dtl4u_kb.enriched.json")

    if not args.quiet:
        print(f"{APP_NAME} {APP_VERSION}")
        print(f"Fichiers analysés : {len(files)}")
        print(f"Conversations lues : {conversation_count}")
        print(f"Connaissances retenues : {len(candidates)}")
        print(f"Ajouts proposés : {len(additions)}")
        print(f"Rapport : {args.output / 'DTLarchive-report.html'}")
        if args.apply:
            print(f"KB enrichie : {args.output / 'dtl4u_kb.enriched.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
