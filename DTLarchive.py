#!/usr/bin/env python3
"""DTLarchive - moteur de recherche local dans les archives ChatGPT."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
import tempfile
import traceback
import unicodedata
import webbrowser
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


APP_NAME = "DTLarchive"
APP_VERSION = "v2.1-1"
SCHEMA_VERSION = "2.0"
GREEN_COLOR = "\033[38;2;0;255;0m"
RESET_COLOR = "\033[0m"


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
class QueryTerm:
    text: str
    excluded: bool = False
    group: int = 0


@dataclass
class MiningResult:
    source_file: str
    conversation_id: str
    conversation_title: str
    conversation_date: str
    matched_keywords: list[str]
    occurrence_count: int
    message_count: int
    relevance_score: int
    relevance_label: str
    matched_roles: list[str] = field(default_factory=list)
    contexts: list[dict[str, Any]] = field(default_factory=list)
    conversation_url: str = ""


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", value.lower().replace("’", "'")).strip()


def compact(text: str, limit: int = 500) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = normalize(item)
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def green(value: Any) -> str:
    return f"{GREEN_COLOR}{value}{RESET_COLOR}"


def pluralized(count: int, singular: str, plural: str | None = None) -> str:
    return singular if count == 1 else (plural or singular + "s")


def resolve_tool_dir() -> Path:
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        return executable_dir.parent if executable_dir.name.lower() == "dist" else executable_dir
    return Path(__file__).resolve().parent


def resolve_log_dir() -> Path:
    candidates = [resolve_tool_dir() / "logs", Path(tempfile.gettempdir()) / APP_NAME / "logs"]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            continue
    return Path(tempfile.gettempdir())


def current_log_path() -> Path:
    return resolve_log_dir() / f"{APP_NAME}_{dt.datetime.now().strftime('%Y%m%d')}.html"


def html_log_header() -> str:
    generated = html.escape(dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Journal {APP_NAME}</title><style>
:root{{--bg:#0b1020;--panel:#121a2f;--text:#eef4ff;--muted:#9fb0d0;--info:#38bdf8;--error:#fb7185;--action:#facc15}}
body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.25 Consolas,"Courier New",monospace}}
header{{position:sticky;top:0;padding:10px 16px;background:linear-gradient(90deg,#172554,#0f172a);border-bottom:1px solid #24324f}}
h1{{margin:0;font-size:18px}}.meta{{margin-top:2px;color:var(--muted);font-size:12px}}main{{padding:8px 10px 18px}}
.entry{{display:grid;grid-template-columns:160px 72px 1fr;gap:8px;margin:2px 0;padding:4px 7px;border-radius:4px;background:var(--panel)}}
.time{{color:var(--muted)}}.level{{font-weight:700;color:var(--info)}}.entry.action .level{{color:var(--action)}}
.entry.error .level{{color:var(--error)}}.entry.error{{background:#2a1320}}.message{{white-space:pre-wrap;overflow-wrap:anywhere}}
</style></head><body><header><h1>Journal {APP_NAME} {APP_VERSION}</h1>
<div class="meta">Créé le {generated}</div></header><main>
"""


def write_action_log(action: str, status: str = "INFO", *, detail: str = "", exc: BaseException | None = None) -> None:
    normalized_status = status.upper()
    is_error = normalized_status in {"ERREUR", "ECHEC"}
    level = "ERREUR" if is_error else "ACTION" if normalized_status in {"DEBUT", "OK"} else "INFO"
    parts = [action]
    if detail:
        parts.append(detail)
    if exc is not None:
        parts.append(f"exception={type(exc).__name__}: {exc}")
        trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()
        if trace:
            parts.append(trace)
    entry_class = "error" if is_error else level.lower()
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f'<div class="entry {entry_class}"><span class="time">{html.escape(stamp)}</span>'
        f'<span class="level">{html.escape(level)}</span>'
        f'<span class="message">{html.escape(" | ".join(parts))}</span></div>\n'
    )
    try:
        path = current_log_path()
        if not path.exists() or path.stat().st_size == 0:
            path.write_text(html_log_header(), encoding="utf-8")
        with path.open("a", encoding="utf-8") as stream:
            stream.write(entry)
    except OSError:
        pass


def show_dialog(kind: str, title: str, message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        getattr(messagebox, kind)(title, message, parent=root)
        root.destroy()
    except Exception:
        pass


def choose_conversation_files() -> list[Path]:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilenames(
            parent=root,
            title="Sélectionnez les archives de conversations ChatGPT",
            filetypes=(("Archives ChatGPT JSON", "conversations*.json"), ("Fichiers JSON", "*.json")),
        )
        root.destroy()
        return [Path(value) for value in selected]
    except Exception as exc:
        write_action_log("Sélection des archives", "ERREUR", exc=exc)
        return []


def wait_for_key(message: str) -> None:
    print()
    print(message)
    print("Appuyez sur une touche pour continuer...", flush=True)
    try:
        if sys.stdin.isatty() and sys.platform == "win32":
            import msvcrt

            msvcrt.getwch()
        else:
            input()
    except (EOFError, OSError):
        pass


def print_console_header() -> None:
    print(f"{APP_NAME} {APP_VERSION}")
    print()
    print("Data miner local pour archives ChatGPT")
    print("Recherche dans les titres et les questions de l'utilisateur")
    print()


def print_current_file(path: Path) -> None:
    print(f"\r\033[2K{green(path.name)}", end="", flush=True)


def clear_current_file() -> None:
    print("\r\033[2K", end="", flush=True)


def parse_french_date(value: str, *, end_of_day: bool = False) -> dt.datetime:
    parsed = dt.datetime.strptime(value.strip(), "%d/%m/%Y")
    return parsed.replace(hour=23, minute=59, second=59) if end_of_day else parsed


def ask_date(label: str, *, end_of_day: bool = False) -> dt.datetime | None:
    while True:
        print(f"{label} au format jj/mm/aaaa (vide = aucune limite) : ", end="", flush=True)
        try:
            value = input().strip()
        except (EOFError, OSError):
            return None
        if not value:
            return None
        try:
            return parse_french_date(value, end_of_day=end_of_day)
        except ValueError:
            print("Date invalide. Exemple attendu : 01/06/2026.")


def parse_query(value: str) -> list[QueryTerm]:
    terms: list[QueryTerm] = []
    for group, clause in enumerate(re.split(r"[,;]|\s+OU\s+", value)):
        for part in re.split(r"\s+ET\s+", clause.strip()):
            token = part.strip()
            if not token:
                continue
            excluded = token.startswith("-") and len(token) > 1
            text = token[1:].strip() if excluded else token
            if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
                text = text[1:-1].strip()
            duplicate = any(
                normalize(text) == normalize(term.text) and term.excluded == excluded and term.group == group
                for term in terms
            )
            if text and not duplicate:
                terms.append(QueryTerm(text=text, excluded=excluded, group=group))
    return terms


def format_query(terms: Sequence[QueryTerm]) -> list[str]:
    exclusions = [f"-{term.text}" for term in terms if term.excluded]
    groups: dict[int, list[str]] = {}
    for term in terms:
        if not term.excluded:
            groups.setdefault(term.group, []).append(term.text)
    clauses = [" ET ".join(values) for _, values in sorted(groups.items()) if values]
    return clauses + exclusions


def ask_query() -> list[QueryTerm]:
    print()
    print("Saisissez un mot, une expression ou plusieurs recherches séparées par des virgules.")
    print(f"Exemples : {green('retraite')}  {green('asile ET lucky')}  {green('asile OU retraite')}  {green('imprim*')}")
    print("ET exige tous les termes ; OU ou la virgule proposent des alternatives ; -mot exclut ; * complète un mot.")
    while True:
        print("Recherche : ", end="", flush=True)
        try:
            terms = parse_query(input().strip())
        except (EOFError, OSError):
            return []
        if any(not term.excluded for term in terms):
            return terms
        print("Saisissez au moins un mot-clé à rechercher.")


def ask_role_scope() -> str:
    print()
    print("Où faut-il chercher ?")
    print(f"  {green('1')}  Titres et questions de l'utilisateur")
    print(f"  {green('2')}  Titres et réponses de ChatGPT")
    print(f"  {green('3')}  Titres, questions et réponses")
    while True:
        print("Choix [1] : ", end="", flush=True)
        try:
            value = input().strip() or "1"
        except (EOFError, OSError):
            return "user"
        if value in {"1", "2", "3"}:
            return {"1": "user", "2": "assistant", "3": "both"}[value]
        print("Répondez 1, 2 ou 3.")


def role_label(role: str) -> str:
    return "👤 Utilisateur" if role == "user" else "🤖 ChatGPT"


def scope_label(scope: str) -> str:
    return {
        "user": "Titres et questions de l'utilisateur",
        "assistant": "Titres et réponses de ChatGPT",
        "both": "Titres, questions et réponses",
    }[scope]


def keyword_pattern(term: str) -> re.Pattern[str]:
    normalized = normalize(term)
    pieces = normalized.split("*")
    pattern = r"[a-z0-9_-]*".join(re.escape(piece) for piece in pieces)
    if "*" not in normalized and not normalized.endswith(("s", "x")):
        pattern += r"(?:s|x)?"
    return re.compile(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])")


def count_term(normalized_text: str, term: str) -> int:
    return len(keyword_pattern(term).findall(normalized_text))


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
                value = part.get("text") or part.get("content")
                if isinstance(value, str):
                    values.append(value)
        return "\n".join(values).strip()
    value = content.get("text")
    return value.strip() if isinstance(value, str) else ""


def current_branch_messages(mapping: dict[str, Any], current_node: str | None) -> list[Message]:
    messages: list[Message] = []
    visited: set[str] = set()
    node_id = current_node
    while node_id and node_id in mapping and node_id not in visited:
        visited.add(node_id)
        node = mapping[node_id]
        raw = node.get("message")
        if isinstance(raw, dict):
            role = ((raw.get("author") or {}).get("role") or "")
            text = text_from_content(raw.get("content"))
            if role in {"user", "assistant"} and text:
                messages.append(Message(str(raw.get("id") or node_id), role, text, raw.get("create_time")))
        node_id = node.get("parent")
    messages.reverse()
    if messages:
        return messages
    fallback: list[Message] = []
    for fallback_id, node in mapping.items():
        raw = node.get("message")
        if not isinstance(raw, dict):
            continue
        role = ((raw.get("author") or {}).get("role") or "")
        text = text_from_content(raw.get("content"))
        if role in {"user", "assistant"} and text:
            fallback.append(Message(str(raw.get("id") or fallback_id), role, text, raw.get("create_time")))
    return sorted(fallback, key=lambda message: (message.create_time is None, message.create_time or 0))


def iter_conversations(path: Path) -> Iterator[Conversation]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        write_action_log("Lecture d'une archive", "ERREUR", detail=str(path), exc=exc)
        print(f"[AVERTISSEMENT] {path}: {exc}", file=sys.stderr)
        return
    records = payload if isinstance(payload, list) else [payload]
    for raw in records:
        if not isinstance(raw, dict) or not isinstance(raw.get("mapping"), dict):
            continue
        messages = current_branch_messages(raw["mapping"], raw.get("current_node"))
        if messages:
            yield Conversation(
                path.name,
                str(raw.get("conversation_id") or raw.get("id") or ""),
                str(raw.get("title") or "(sans titre)"),
                raw.get("create_time"),
                raw.get("update_time"),
                messages,
            )


def conversation_datetime(conversation: Conversation) -> dt.datetime | None:
    timestamp = conversation.create_time if conversation.create_time is not None else conversation.update_time
    try:
        return dt.datetime.fromtimestamp(float(timestamp)) if timestamp is not None else None
    except (TypeError, ValueError, OSError):
        return None


def conversation_in_period(
    conversation: Conversation, start_date: dt.datetime | None, end_date: dt.datetime | None
) -> bool:
    if start_date is None and end_date is None:
        return True
    value = conversation_datetime(conversation)
    if value is None:
        return False
    return not (start_date and value < start_date) and not (end_date and value > end_date)


def load_conversation_archives(
    files: Sequence[Path], *, show_progress: bool = False
) -> dict[Path, list[Conversation]]:
    archives: dict[Path, list[Conversation]] = {}
    for source in files:
        if show_progress:
            print_current_file(source)
        archives[source] = list(iter_conversations(source))
    if show_progress:
        clear_current_file()
    return archives


def archive_datetime_bounds(
    archives: dict[Path, list[Conversation]],
) -> tuple[dt.datetime, dt.datetime] | None:
    dates = [
        value
        for conversations in archives.values()
        for conversation in conversations
        if (value := conversation_datetime(conversation)) is not None
    ]
    return (min(dates), max(dates)) if dates else None


def period_overlaps_archive(
    start_date: dt.datetime | None,
    end_date: dt.datetime | None,
    archive_bounds: tuple[dt.datetime, dt.datetime] | None,
) -> bool:
    if archive_bounds is None or (start_date is None and end_date is None):
        return True
    archive_start, archive_end = archive_bounds
    return not (start_date and start_date > archive_end) and not (end_date and end_date < archive_start)


def archive_period_label(archive_bounds: tuple[dt.datetime, dt.datetime]) -> str:
    archive_start, archive_end = archive_bounds
    return f"du {archive_start.strftime('%d/%m/%Y')} au {archive_end.strftime('%d/%m/%Y')}"


def relevance_label(score: int) -> str:
    if score >= 80:
        return "Très pertinent"
    if score >= 45:
        return "Pertinent"
    return "Mention secondaire"


def build_contexts(conversation: Conversation, matched_indexes: Sequence[int]) -> list[dict[str, Any]]:
    if not conversation.messages:
        return []
    indexes = sorted(set(matched_indexes))
    if not indexes:
        indexes = [0]
    ranges: list[list[int]] = []
    for index in indexes:
        start = max(0, index - 2)
        end = min(len(conversation.messages) - 1, index + 2)
        if ranges and start <= ranges[-1][1] + 1:
            ranges[-1][1] = max(ranges[-1][1], end)
        else:
            ranges.append([start, end])
    contexts: list[dict[str, Any]] = []
    matched_set = set(matched_indexes)
    for start, end in ranges[:6]:
        contexts.append({
            "messages": [
                {
                    "index": index,
                    "id": conversation.messages[index].id,
                    "role": conversation.messages[index].role,
                    "role_label": role_label(conversation.messages[index].role),
                    "text": compact(conversation.messages[index].text, 1200),
                    "matched": index in matched_set,
                }
                for index in range(start, end + 1)
            ]
        })
    return contexts


def mine_conversation(
    conversation: Conversation, terms: Sequence[QueryTerm], role_scope: str = "user"
) -> MiningResult | None:
    allowed_roles = {"user", "assistant"} if role_scope == "both" else {role_scope}
    searchable_messages = [message for message in conversation.messages if message.role in allowed_roles]
    searchable_text = "\n".join([conversation.title, *(message.text for message in searchable_messages)])
    normalized_searchable_text = normalize(searchable_text)
    excluded_terms = [term for term in terms if term.excluded]
    if any(count_term(normalized_searchable_text, term.text) for term in excluded_terms):
        return None

    positive_groups: dict[int, list[QueryTerm]] = {}
    for term in terms:
        if not term.excluded:
            positive_groups.setdefault(term.group, []).append(term)
    matched_groups = [
        group_terms
        for group_terms in positive_groups.values()
        if group_terms and all(count_term(normalized_searchable_text, term.text) > 0 for term in group_terms)
    ]
    if not matched_groups:
        return None
    matched = unique(term.text for group_terms in matched_groups for term in group_terms)
    counts = {term: count_term(normalized_searchable_text, term) for term in matched}

    title_count = sum(count_term(normalize(conversation.title), term) for term in matched)
    matched_indexes: list[int] = []
    matched_roles: list[str] = ["Titre"] if title_count else []
    for index, message in enumerate(conversation.messages):
        if message.role not in allowed_roles:
            continue
        normalized_message = normalize(message.text)
        if any(count_term(normalized_message, term) for term in matched):
            matched_indexes.append(index)
            matched_roles.append(role_label(message.role))

    user_matches = sum(conversation.messages[index].role == "user" for index in matched_indexes)
    assistant_matches = sum(conversation.messages[index].role == "assistant" for index in matched_indexes)
    occurrence_count = sum(counts.values())
    score = min(
        100,
        15
        + (35 if title_count else 0)
        + min(user_matches * 25, 35)
        + min(assistant_matches * 15, 25)
        + min(occurrence_count * 5, 20)
        + min(max(0, len(matched) - 1) * 10, 20),
    )

    date_value = conversation_datetime(conversation)
    return MiningResult(
        source_file=conversation.source_file,
        conversation_id=conversation.id,
        conversation_title=conversation.title,
        conversation_date=date_value.strftime("%d/%m/%Y %H:%M") if date_value else "Date inconnue",
        matched_keywords=matched,
        occurrence_count=occurrence_count,
        message_count=len(conversation.messages),
        relevance_score=score,
        relevance_label=relevance_label(score),
        matched_roles=unique(matched_roles),
        contexts=build_contexts(conversation, matched_indexes),
    )


def conversation_page_name(conversation: Conversation) -> str:
    identity = conversation.id or f"{conversation.source_file}|{conversation.title}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"conversation-{digest}.html"


def write_conversation_page(path: Path, conversation: Conversation, result: MiningResult) -> None:
    matched_indexes = {
        item["index"]
        for context in result.contexts
        for item in context["messages"]
        if item["matched"]
    }
    messages: list[str] = []
    for index, message in enumerate(conversation.messages):
        matched_class = " matched" if index in matched_indexes else ""
        messages.append(
            f'<article id="msg-{index}" class="message {message.role}{matched_class}">'
            f'<div class="role">{role_label(message.role)}</div>'
            f'<div class="text">{html.escape(message.text)}</div></article>'
        )
    document = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(conversation.title)}</title><style>
:root{{--bg:#0b0d0f;--panel:#15191e;--border:#30363d;--text:#e8eaed;--green:#39ff14;--blue:#58a6ff}}
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:var(--bg);color:var(--text)}}header,main{{max-width:1000px;margin:auto;padding:22px}}
header{{position:sticky;top:0;background:#0b0d0fee;border-bottom:1px solid var(--border);z-index:2}}a{{color:var(--blue)}}
.message{{margin:12px 0;padding:14px;border:1px solid var(--border);border-radius:8px;background:var(--panel);scroll-margin-top:130px}}
.message.user{{border-left:4px solid var(--blue)}}.message.assistant{{border-left:4px solid #a78bfa}}.message.matched{{outline:2px solid var(--green);background:#102417}}
.role{{font-weight:700;margin-bottom:8px}}.text{{white-space:pre-wrap;overflow-wrap:anywhere}}
</style></head><body><header><a href="../DTLarchive-report.html">← Retour au rapport</a>
<h1>{html.escape(conversation.title)}</h1><div>{html.escape(conversation.source_file)} — Pertinence : {result.relevance_score} %</div></header>
<main>{''.join(messages)}</main></body></html>"""
    path.write_text(document, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_html_report(path: Path, results: Sequence[MiningResult], metadata: dict[str, Any]) -> None:
    chips = " ".join(f"<span class='chip'>{html.escape(term)}</span>" for term in metadata["recherche"])
    term_counts = {
        term: sum(term in result.matched_keywords for result in results)
        for term in unique(keyword for result in results for keyword in result.matched_keywords)
    }
    term_summary = "".join(
        f"<li><strong>{html.escape(term)}</strong> : {count} {pluralized(count, 'conversation', 'conversations')}</li>"
        for term, count in sorted(term_counts.items(), key=lambda item: (-item[1], normalize(item[0])))
    )
    subjects = unique(result.conversation_title for result in sorted(results, key=lambda item: -item.relevance_score))[:5]
    subject_summary = "".join(f"<li>{html.escape(subject)}</li>" for subject in subjects)
    rows: list[str] = []
    for result in results:
        keywords = " ".join(f"<span class='chip'>{html.escape(term)}</span>" for term in result.matched_keywords)
        contexts: list[str] = []
        for context in result.contexts:
            context_messages = "".join(
                f'<div class="context-message {item["role"]}{" matched" if item["matched"] else ""}">'
                f'<strong>{item["role_label"]}</strong><p>{html.escape(item["text"])}</p></div>'
                for item in context["messages"]
            )
            contexts.append(f'<div class="context-window">{context_messages}</div>')
        context_label = pluralized(len(result.contexts), "contexte", "contextes")
        roles = " · ".join(result.matched_roles)
        rows.append(
            "<tr>"
            f"<td>{html.escape(result.conversation_date)}</td>"
            f"<td><strong>{html.escape(result.conversation_title)}</strong><br><small>{html.escape(result.source_file)}</small><br>"
            f'<a class="open-button" href="{html.escape(result.conversation_url)}">Ouvrir la conversation</a></td>'
            f"<td><span class='score'>{result.relevance_score} %</span><br>{html.escape(result.relevance_label)}</td>"
            f"<td>{keywords}<br><small>{roles}</small></td><td class='number'>{result.occurrence_count}</td>"
            f"<td><details><summary>{len(result.contexts)} {context_label}</summary>{''.join(contexts)}</details></td>"
            "</tr>"
        )
    generated = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    document = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Résultats {APP_NAME}</title><style>
:root{{--bg:#0b0d0f;--panel:#131619;--border:#30363d;--text:#e8eaed;--muted:#9aa0a6;--green:#39ff14;--blue:#58a6ff}}
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:var(--bg);color:var(--text)}}
header,main{{max-width:1500px;margin:auto;padding:24px}}h1{{margin:0 0 5px}}.muted,small{{color:var(--muted)}}
.query,.summary-box{{margin-top:18px;padding:14px;background:var(--panel);border:1px solid var(--border);border-radius:8px}}
.summary-grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}.summary-box h2{{margin-top:0}}.summary-box ul{{margin-bottom:0}}
.stats{{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}}.stat{{min-width:145px;padding:14px;background:var(--panel);border:1px solid var(--border);border-radius:8px}}
.stat strong{{display:block;color:var(--green);font-size:24px}}table{{width:100%;border-collapse:collapse;background:var(--panel)}}
th,td{{padding:10px;border:1px solid var(--border);vertical-align:top;text-align:left}}th{{position:sticky;top:0;background:#20242a}}
.chip{{display:inline-block;margin:2px;padding:2px 7px;border-radius:10px;background:#073b1c;color:var(--green)}}.number{{color:var(--green);font-weight:bold;text-align:center}}
.score{{color:var(--green);font-size:20px;font-weight:700}}.open-button{{display:inline-block;margin-top:9px;padding:5px 9px;border-radius:5px;background:#0d3b66;color:#fff;text-decoration:none}}
.context-window{{margin:8px 0;border:1px solid var(--border);border-radius:6px;overflow:hidden}}.context-message{{padding:8px;background:#0d1117;border-left:3px solid #a78bfa}}
.context-message.user{{border-left-color:var(--blue)}}.context-message.matched{{background:#102417;outline:1px solid #1f7a36}}.context-message p{{margin:5px 0;white-space:pre-wrap}}
summary{{cursor:pointer;color:var(--blue)}}@media(max-width:800px){{.summary-grid{{grid-template-columns:1fr}}}}
</style></head><body><header><h1>{APP_NAME} {APP_VERSION}</h1><div class="muted">Rapport généré le {generated}</div>
<div class="query"><strong>Recherche :</strong> {chips}<br><span class="muted">{html.escape(metadata['scope_label'])} — Période : {html.escape(metadata['periode'])}</span></div>
<div class="stats"><div class="stat"><strong>{metadata['fichiers']}</strong>Fichiers</div>
<div class="stat"><strong>{metadata['conversations_lues']}</strong>Conversations examinées</div>
<div class="stat"><strong>{len(results)}</strong>Conversations trouvées</div>
<div class="stat"><strong>{sum(result.occurrence_count for result in results)}</strong>Occurrences</div></div>
<div class="summary-box"><h2>Résumé automatique</h2><p>La recherche apparaît dans <strong>{len(results)} {pluralized(len(results), 'conversation', 'conversations')}</strong>.</p>
<div class="summary-grid"><div><h3>Répartition des termes</h3><ul>{term_summary or '<li>Aucun résultat</li>'}</ul></div>
<div><h3>Principaux sujets</h3><ul>{subject_summary or '<li>Aucun sujet</li>'}</ul></div></div></div></header>
<main><table><thead><tr><th>Date</th><th>Conversation</th><th>Pertinence</th><th>Mots-clés et rôles</th><th>Occurrences</th><th>Contexte</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></main></body></html>"""
    path.write_text(document, encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recherche généraliste dans les archives ChatGPT.")
    parser.add_argument("inputs", nargs="*", type=Path, help="fichiers conversations*.json ou dossiers")
    parser.add_argument("--output", type=Path, help="dossier de sortie")
    parser.add_argument("--pattern", default="conversations*.json")
    parser.add_argument("--date-debut", help="date de début inclusive au format jj/mm/aaaa")
    parser.add_argument("--date-fin", help="date de fin inclusive au format jj/mm/aaaa")
    parser.add_argument("--mots-cles", help="mots ou expressions séparés par des virgules")
    parser.add_argument(
        "--role",
        choices=("user", "assistant", "both"),
        default="user",
        help="chercher dans les questions, les réponses ou les deux",
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    return parser.parse_args(argv)


def resolve_inputs(inputs: Sequence[Path], pattern: str) -> list[Path]:
    files: list[Path] = []
    for root in inputs:
        if root.is_dir():
            files.extend(root.glob(pattern))
        elif root.is_file():
            files.append(root)
    return sorted({path.resolve() for path in files})


def main(argv: Sequence[str] | None = None) -> int:
    effective_argv = list(argv) if argv is not None else sys.argv[1:]
    interactive = not effective_argv
    write_action_log("Démarrage du data miner", "DEBUT", detail=f"arguments={effective_argv!r}")
    if interactive:
        print_console_header()
    args = parse_args(argv)
    args.output = args.output or (resolve_tool_dir() / "DTLarchive-output" if interactive else Path("DTLarchive-output"))

    files = resolve_inputs(args.inputs, args.pattern) if args.inputs else []
    if not files and interactive:
        wait_for_key("DTLarchive va ouvrir l'explorateur de fichiers pour sélectionner les archives ChatGPT.")
        files = sorted({path.resolve() for path in choose_conversation_files() if path.is_file()})
    if not files:
        message = "Aucune archive ChatGPT n'a été sélectionnée."
        write_action_log("Sélection des archives", "ERREUR", detail=message)
        if interactive:
            show_dialog("showwarning", APP_NAME, message)
        else:
            print(f"[ERREUR] {message}", file=sys.stderr)
        return 2

    if interactive:
        print("\nAnalyse de la période couverte par les archives...", flush=True)
    archives = load_conversation_archives(files, show_progress=interactive)
    archive_bounds = archive_datetime_bounds(archives)
    if interactive:
        if archive_bounds:
            print(f"Période disponible : {green(archive_period_label(archive_bounds))}")
        else:
            print("Aucune date de conversation exploitable n'a été trouvée dans les archives.")

    try:
        start_date = parse_french_date(args.date_debut) if args.date_debut else None
        end_date = parse_french_date(args.date_fin, end_of_day=True) if args.date_fin else None
    except ValueError:
        print("[ERREUR] Date invalide : utilisez le format jj/mm/aaaa.", file=sys.stderr)
        return 2

    terms = parse_query(args.mots_cles or "")
    role_scope = args.role
    if interactive:
        while True:
            print("\nPériode de recherche (les deux dates sont facultatives).")
            start_date = ask_date("Date de début")
            end_date = ask_date("Date de fin", end_of_day=True)
            if start_date and end_date and start_date > end_date:
                print("La date de fin doit être postérieure ou égale à la date de début.")
                continue
            if not period_overlaps_archive(start_date, end_date, archive_bounds):
                requested_period = (
                    f"du {start_date.strftime('%d/%m/%Y') if start_date else 'début'} "
                    f"au {end_date.strftime('%d/%m/%Y') if end_date else 'présent'}"
                )
                print(f"Aucune conversation n'existe pour la période demandée ({requested_period}).")
                if archive_bounds:
                    print(f"Les archives sélectionnées couvrent la période {green(archive_period_label(archive_bounds))}.")
                print("Veuillez saisir une période qui recoupe les archives.")
                continue
            break
        terms = ask_query()
        role_scope = ask_role_scope()
    elif start_date and end_date and start_date > end_date:
        print("[ERREUR] La date de fin doit être postérieure ou égale à la date de début.", file=sys.stderr)
        return 2

    if not period_overlaps_archive(start_date, end_date, archive_bounds):
        available = archive_period_label(archive_bounds) if archive_bounds else "inconnue"
        message = f"La période demandée ne recoupe pas celle des archives ({available})."
        write_action_log("Contrôle de la période", "ERREUR", detail=message)
        print(f"[ERREUR] {message}", file=sys.stderr)
        return 2
    if not any(not term.excluded for term in terms):
        print("[ERREUR] Saisissez au moins un mot-clé à rechercher.", file=sys.stderr)
        return 2

    all_labels = format_query(terms)
    write_action_log(
        "Recherche configurée",
        "OK",
        detail=(
            f"fichiers={len(files)} | période={start_date} à {end_date} | "
            f"recherche={all_labels} | périmètre={role_scope}"
        ),
    )
    if interactive:
        label = pluralized(len(files), "fichier sélectionné", "fichiers sélectionnés")
        print(f"\n{green(len(files))} {label}.")
        print("Traitement en cours, merci de patienter...", flush=True)

    results: list[MiningResult] = []
    matched_conversations: list[tuple[MiningResult, Conversation]] = []
    conversation_count = 0
    for source, conversations in archives.items():
        if interactive:
            print_current_file(source)
        for conversation in conversations:
            if not conversation_in_period(conversation, start_date, end_date):
                continue
            conversation_count += 1
            result = mine_conversation(conversation, terms, role_scope)
            if result is not None:
                page_name = conversation_page_name(conversation)
                first_match_index = next(
                    (
                        item["index"]
                        for context in result.contexts
                        for item in context["messages"]
                        if item["matched"]
                    ),
                    0,
                )
                result.conversation_url = f"conversations/{page_name}#msg-{first_match_index}"
                results.append(result)
                matched_conversations.append((result, conversation))
    if interactive:
        clear_current_file()
        print()

    def result_date_key(result: MiningResult) -> dt.datetime:
        try:
            return dt.datetime.strptime(result.conversation_date, "%d/%m/%Y %H:%M")
        except ValueError:
            return dt.datetime.min

    results.sort(key=lambda result: (result.relevance_score, result_date_key(result)), reverse=True)
    args.output.mkdir(parents=True, exist_ok=True)
    conversation_dir = args.output / "conversations"
    conversation_dir.mkdir(parents=True, exist_ok=True)
    for result, conversation in matched_conversations:
        write_conversation_page(conversation_dir / conversation_page_name(conversation), conversation, result)
    period = (
        f"du {start_date.strftime('%d/%m/%Y') if start_date else 'début des archives'} "
        f"au {end_date.strftime('%d/%m/%Y') if end_date else 'dernier échange'}"
    )
    metadata = {
        "application": APP_NAME,
        "version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_files": [str(path) for path in files],
        "fichiers": len(files),
        "conversations_lues": conversation_count,
        "date_debut": start_date.strftime("%d/%m/%Y") if start_date else None,
        "date_fin": end_date.strftime("%d/%m/%Y") if end_date else None,
        "periode": period,
        "recherche": all_labels,
        "role_scope": role_scope,
        "scope_label": scope_label(role_scope),
    }
    write_json(args.output / "mining_results.json", {"metadata": metadata, "results": [asdict(result) for result in results]})
    report_path = (args.output / "DTLarchive-report.html").resolve()
    write_html_report(report_path, results, metadata)
    occurrences = sum(result.occurrence_count for result in results)
    write_action_log(
        "Fouille terminée",
        "OK",
        detail=f"conversations examinées={conversation_count} | trouvées={len(results)} | occurrences={occurrences}",
    )

    if not args.quiet:
        if not interactive:
            print(f"{APP_NAME} {APP_VERSION}")
        print(f"{pluralized(conversation_count, 'Conversation examinée', 'Conversations examinées')} : {green(conversation_count)}")
        print(f"{pluralized(len(results), 'Conversation trouvée', 'Conversations trouvées')} : {green(len(results))}")
        print(f"{pluralized(occurrences, 'Occurrence', 'Occurrences')} : {green(occurrences)}")
        if not interactive:
            print(f"Rapport : {green(report_path)}")

    if interactive:
        wait_for_key(f"Rapport terminé : {green(report_path)}\nIl va maintenant être affiché dans votre navigateur.")
        webbrowser.open(report_path.as_uri())
        show_dialog(
            "showinfo",
            APP_NAME,
            f"Recherche terminée.\n\n{pluralized(conversation_count, 'Conversation examinée', 'Conversations examinées')} : {conversation_count}\n"
            f"{pluralized(len(results), 'Conversation trouvée', 'Conversations trouvées')} : {len(results)}\n"
            f"{pluralized(occurrences, 'Occurrence', 'Occurrences')} : {occurrences}\n\n"
            f"Le rapport a été ouvert dans votre navigateur.\n{report_path}",
        )
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except SystemExit as exc:
        if exc.code not in (None, 0):
            write_action_log("Arrêt demandé par l'analyse des paramètres", "ECHEC", detail=f"code={exc.code}")
        raise
    except BaseException as exc:
        write_action_log("Exception fatale de DTLarchive", "ERREUR", exc=exc)
        print(f"[ERREUR FATALE] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    else:
        if exit_code != 0:
            write_action_log("Arrêt de DTLarchive", "ECHEC", detail=f"code={exit_code}")
        raise SystemExit(exit_code)
