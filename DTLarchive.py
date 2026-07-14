#!/usr/bin/env python3
"""DTLarchive - moteur de recherche local dans les archives ChatGPT."""

from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
import html
import json
import re
import sqlite3
import sys
import tempfile
import traceback
import unicodedata
import webbrowser
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from dtlarchive_index import ArchiveIndex
from dtlarchive_i18n import current_language, plural_key, set_language, t
from dtlarchive_search import SearchEngine


APP_NAME = "DTLarchive"
APP_VERSION = "v2.2-4"
SCHEMA_VERSION = "2.1"
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


class LocalizedArgumentParser(argparse.ArgumentParser):
    def format_help(self) -> str:
        value = super().format_help()
        return (
            value.replace("usage:", t("arg.usage"), 1)
            .replace("positional arguments:", t("arg.positionals"), 1)
            .replace("options:", t("arg.options"), 1)
        )


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


def language_switch_message() -> str:
    if current_language() == "en":
        return t("startup.switch_to_french").replace("2", green("2"), 1)
    return t("startup.switch_to_english").replace("1", green("1"), 1)


def pluralized(count: int, singular: str, plural: str | None = None) -> str:
    return singular if count == 1 else (plural or singular + "s")


def is_help_request(value: str) -> bool:
    return value.strip().lower() in {"?", "aide", "help", "h"}


def configure_console_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(APP_NAME)
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except OSError:
            pass


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


def default_index_path() -> Path:
    return resolve_tool_dir() / "DTLarchive-index.sqlite"


def current_log_path() -> Path:
    return resolve_log_dir() / f"{APP_NAME}_{dt.datetime.now().strftime('%Y%m%d')}.html"


def html_log_header() -> str:
    generated = html.escape(dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    language = current_language()
    return f"""<!doctype html><html lang="{language}"><head><meta charset="utf-8">
<title>{t('log.title')} {APP_NAME}</title><style>
:root{{--bg:#0b1020;--panel:#121a2f;--text:#eef4ff;--muted:#9fb0d0;--info:#38bdf8;--error:#fb7185;--action:#facc15}}
body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.25 Consolas,"Courier New",monospace}}
header{{position:sticky;top:0;padding:10px 16px;background:linear-gradient(90deg,#172554,#0f172a);border-bottom:1px solid #24324f}}
h1{{margin:0;font-size:18px}}.meta{{margin-top:2px;color:var(--muted);font-size:12px}}main{{padding:8px 10px 18px}}
.entry{{display:grid;grid-template-columns:160px 72px 1fr;gap:8px;margin:2px 0;padding:4px 7px;border-radius:4px;background:var(--panel)}}
.time{{color:var(--muted)}}.level{{font-weight:700;color:var(--info)}}.entry.action .level{{color:var(--action)}}
.entry.error .level{{color:var(--error)}}.entry.error{{background:#2a1320}}.message{{white-space:pre-wrap;overflow-wrap:anywhere}}
</style></head><body><header><h1>{t('log.title')} {APP_NAME} {APP_VERSION}</h1>
<div class="meta">{t('log.created', date=generated)}</div></header><main>
"""


def write_action_log(action: str, status: str = "INFO", *, detail: str = "", exc: BaseException | None = None) -> None:
    normalized_status = status.upper()
    is_error = normalized_status in {"ERREUR", "ECHEC"}
    level = t("common.error") if is_error else t("common.action") if normalized_status in {"DEBUT", "OK"} else t("common.info")
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
            title=t("file.dialog_title"),
            filetypes=((t("file.dialog_archive"), "conversations*.json"), (t("file.dialog_json"), "*.json")),
        )
        root.destroy()
        return [Path(value) for value in selected]
    except Exception as exc:
        write_action_log(t("log.file_selection"), "ERREUR", exc=exc)
        return []


def wait_for_key(
    message: str,
    *,
    allow_language_switch: bool = False,
    help_key: str | None = None,
    message_key: str | None = None,
) -> None:
    print()
    print(message)
    print(t("file.press_key_language" if allow_language_switch else "file.press_key"), flush=True)
    try:
        if allow_language_switch or help_key:
            answer = input().strip()
        elif sys.stdin.isatty() and sys.platform == "win32":
            import msvcrt

            answer = msvcrt.getwch()
        else:
            answer = input().strip()
        if allow_language_switch and answer == "1" and current_language() == "fr":
            set_language("en")
            wait_for_key(
                t(message_key) if message_key else message,
                allow_language_switch=allow_language_switch,
                help_key=help_key,
                message_key=message_key,
            )
        elif allow_language_switch and answer == "2" and current_language() == "en":
            set_language("fr")
            wait_for_key(
                t(message_key) if message_key else message,
                allow_language_switch=allow_language_switch,
                help_key=help_key,
                message_key=message_key,
            )
        elif help_key and is_help_request(answer):
            print(t(help_key))
            wait_for_key(
                t(message_key) if message_key else message,
                allow_language_switch=allow_language_switch,
                help_key=help_key,
                message_key=message_key,
            )
    except (EOFError, OSError):
        pass


def print_console_header() -> None:
    print(f"{APP_NAME} {APP_VERSION}")
    print()
    switch_message = language_switch_message()
    print(t("app.subtitle"))
    print(t("app.scope_subtitle"))
    print(switch_message)
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
        print(t("date.prompt", label=label), end="", flush=True)
        try:
            value = input().strip()
        except (EOFError, OSError):
            return None
        if not value:
            return None
        if is_help_request(value):
            print(t("date.help"))
            continue
        try:
            return parse_french_date(value, end_of_day=end_of_day)
        except ValueError:
            print(t("date.invalid"))


def parse_query(value: str) -> list[QueryTerm]:
    terms: list[QueryTerm] = []
    for group, clause in enumerate(re.split(r"[,;]|\s+(?:OU|OR)\s+", value, flags=re.IGNORECASE)):
        for part in re.split(r"\s+(?:ET|AND)\s+", clause.strip(), flags=re.IGNORECASE):
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
    conjunction = " AND " if current_language() == "en" else " ET "
    clauses = [conjunction.join(values) for _, values in sorted(groups.items()) if values]
    return clauses + exclusions


def ask_query() -> list[QueryTerm]:
    print()
    print(t("query.instructions"))
    examples = ("retirement", "asylum AND lucky", "asylum OR retirement", "print*") if current_language() == "en" else ("retraite", "asile ET lucky", "asile OU retraite", "imprim*")
    print(t("query.examples", one=green(examples[0]), two=green(examples[1]), three=green(examples[2]), four=green(examples[3])))
    print(t("query.syntax"))
    while True:
        print(t("query.prompt"), end="", flush=True)
        try:
            answer = input().strip()
        except (EOFError, OSError):
            return []
        if is_help_request(answer):
            print(t("query.help"))
            continue
        terms = parse_query(answer)
        if any(not term.excluded for term in terms):
            return terms
        print(t("query.required"))


def ask_role_scope() -> str:
    print()
    print(t("scope.question"))
    print(f"  {green('1')}  {t('scope.user')}")
    print(f"  {green('2')}  {t('scope.assistant')}")
    print(f"  {green('3')}  {t('scope.both')}")
    while True:
        print(t("scope.prompt"), end="", flush=True)
        try:
            value = input().strip() or "1"
        except (EOFError, OSError):
            return "user"
        if is_help_request(value):
            print(t("scope.help"))
            continue
        if value in {"1", "2", "3"}:
            return {"1": "user", "2": "assistant", "3": "both"}[value]
        print(t("scope.invalid"))


def role_label(role: str) -> str:
    return t("role.user" if role == "user" else "role.assistant")


def scope_label(scope: str) -> str:
    return t(f"scope.{scope}")


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


def iter_conversations(path: Path, *, strict: bool = False) -> Iterator[Conversation]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        write_action_log(t("log.archive_read"), "ERREUR", detail=str(path), exc=exc)
        print(f"[{t('common.warning')}] {path}: {exc}", file=sys.stderr)
        if strict:
            raise
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
                str(raw.get("title") or t("conversation.untitled")),
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
    return t("period.from_to", start=archive_start.strftime("%d/%m/%Y"), end=archive_end.strftime("%d/%m/%Y"))


def relevance_label(score: int) -> str:
    if score >= 80:
        return t("relevance.very")
    if score >= 45:
        return t("relevance.relevant")
    return t("relevance.secondary")


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
    matched_roles: list[str] = [t("role.title")] if title_count else []
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
        conversation_date=date_value.strftime("%d/%m/%Y %H:%M") if date_value else t("conversation.unknown_date"),
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
    language = current_language()
    document = f"""<!doctype html><html lang="{language}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(conversation.title)}</title><style>
:root{{--bg:#0b0d0f;--panel:#15191e;--border:#30363d;--text:#e8eaed;--green:#39ff14;--blue:#58a6ff}}
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:var(--bg);color:var(--text)}}header,main{{max-width:1000px;margin:auto;padding:22px}}
header{{position:sticky;top:0;background:#0b0d0fee;border-bottom:1px solid var(--border);z-index:2}}a{{color:var(--blue)}}
.message{{margin:12px 0;padding:14px;border:1px solid var(--border);border-radius:8px;background:var(--panel);scroll-margin-top:130px}}
.message.user{{border-left:4px solid var(--blue)}}.message.assistant{{border-left:4px solid #a78bfa}}.message.matched{{outline:2px solid var(--green);background:#102417}}
.role{{font-weight:700;margin-bottom:8px}}.text{{white-space:pre-wrap;overflow-wrap:anywhere}}
</style></head><body><header><a href="../DTLarchive-report.html">{t('html.back')}</a>
<h1>{html.escape(conversation.title)}</h1><div>{html.escape(conversation.source_file)} — {t('html.relevance')} : {result.relevance_score} %</div></header>
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
        f"<li><strong>{html.escape(term)}</strong> : {count} {plural_key('html.conversation', count)}</li>"
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
        context_label = plural_key("html.context", len(result.contexts))
        roles = " · ".join(result.matched_roles)
        rows.append(
            "<tr>"
            f"<td>{html.escape(result.conversation_date)}</td>"
            f"<td><strong>{html.escape(result.conversation_title)}</strong><br><small>{html.escape(result.source_file)}</small><br>"
            f'<a class="open-button" href="{html.escape(result.conversation_url)}">{t("html.open_conversation")}</a></td>'
            f"<td><span class='score'>{result.relevance_score} %</span><br>{html.escape(result.relevance_label)}</td>"
            f"<td>{keywords}<br><small>{roles}</small></td><td class='number'>{result.occurrence_count}</td>"
            f"<td><details><summary>{len(result.contexts)} {context_label}</summary>{''.join(contexts)}</details></td>"
            "</tr>"
        )
    generated = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    language = current_language()
    document = f"""<!doctype html><html lang="{language}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{t('html.results')} {APP_NAME}</title><style>
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
</style></head><body><header><h1>{APP_NAME} {APP_VERSION}</h1><div class="muted">{t('html.generated', date=generated)}</div>
<div class="query"><strong>{t('query.label')} :</strong> {chips}<br><span class="muted">{html.escape(metadata['scope_label'])} — {html.escape(metadata['periode'])}</span></div>
<div class="stats"><div class="stat"><strong>{metadata['fichiers']}</strong>{t('html.files')}</div>
<div class="stat"><strong>{metadata['conversations_lues']}</strong>{plural_key('result.examined', metadata['conversations_lues'])}</div>
<div class="stat"><strong>{len(results)}</strong>{plural_key('result.found', len(results))}</div>
<div class="stat"><strong>{sum(result.occurrence_count for result in results)}</strong>{plural_key('result.occurrence', sum(result.occurrence_count for result in results))}</div></div>
<div class="summary-box"><h2>{t('html.automatic_summary')}</h2><p>{t('html.search_appears', count=len(results), label=plural_key('html.conversation', len(results)))}</p>
<div class="summary-grid"><div><h3>{t('html.term_distribution')}</h3><ul>{term_summary or f'<li>{t("html.no_result")}</li>'}</ul></div>
<div><h3>{t('html.main_subjects')}</h3><ul>{subject_summary or f'<li>{t("html.no_subject")}</li>'}</ul></div></div></div></header>
<main><table><thead><tr><th>{t('html.date')}</th><th>{t('html.conversation')}</th><th>{t('html.relevance')}</th><th>{t('html.keywords_roles')}</th><th>{t('html.occurrences')}</th><th>{t('html.context')}</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></main></body></html>"""
    path.write_text(document, encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = LocalizedArgumentParser(description=t("arg.description"), add_help=False)
    parser.add_argument("-h", "--help", action="help", help=t("arg.help"))
    parser.add_argument("inputs", nargs="*", type=Path, help=t("arg.inputs"))
    parser.add_argument("--output", type=Path, help=t("arg.output"))
    parser.add_argument("--pattern", default="conversations*.json", help=t("arg.pattern"))
    parser.add_argument("--date-debut", help=t("arg.start"))
    parser.add_argument("--date-fin", help=t("arg.end"))
    parser.add_argument("--mots-cles", help=t("arg.keywords"))
    parser.add_argument("--index", type=Path, help=t("arg.index"))
    parser.add_argument("--reindex", action="store_true", help=t("arg.reindex"))
    parser.add_argument(
        "--role",
        choices=("user", "assistant", "both"),
        default="user",
        help=t("arg.role"),
    )
    parser.add_argument("--lang", choices=("fr", "en"), default=current_language(), help=t("arg.lang"))
    parser.add_argument("--quiet", action="store_true", help=t("arg.quiet"))
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}", help=t("arg.version"))
    return parser.parse_args(argv)


def resolve_inputs(inputs: Sequence[Path], pattern: str) -> list[Path]:
    files: list[Path] = []
    for root in inputs:
        if root.is_dir():
            files.extend(root.glob(pattern))
        elif root.is_file():
            files.append(root)
    return sorted({path.resolve() for path in files})


def apply_language_argument(argv: Sequence[str]) -> None:
    for index, argument in enumerate(argv):
        if argument.startswith("--lang="):
            set_language(argument.partition("=")[2])
            return
        if argument == "--lang" and index + 1 < len(argv):
            set_language(argv[index + 1])
            return


def main(argv: Sequence[str] | None = None) -> int:
    configure_console_encoding()
    effective_argv = list(argv) if argv is not None else sys.argv[1:]
    apply_language_argument(effective_argv)
    interactive = not effective_argv
    write_action_log(t("log.start"), "DEBUT", detail=f"arguments={effective_argv!r}")
    if interactive:
        print_console_header()
    args = parse_args(argv)
    set_language(args.lang)
    args.output = args.output or (resolve_tool_dir() / "DTLarchive-output" if interactive else Path("DTLarchive-output"))

    files = resolve_inputs(args.inputs, args.pattern) if args.inputs else []
    if not files and interactive:
        wait_for_key(
            t("file.selection_intro"),
            allow_language_switch=True,
            help_key="file.help",
            message_key="file.selection_intro",
        )
        files = sorted({path.resolve() for path in choose_conversation_files() if path.is_file()})
    if not files:
        message = t("file.none_selected")
        write_action_log(t("log.file_selection"), "ERREUR", detail=message)
        if interactive:
            show_dialog("showwarning", APP_NAME, message)
        else:
            print(f"[{t('common.error')}] {message}", file=sys.stderr)
        return 2

    index_path = (args.index or default_index_path()).resolve()
    try:
        archive_index = ArchiveIndex(index_path)
        if args.reindex:
            archive_index.clear()
        if interactive:
            print(f"\n{t('index.updating')}", flush=True)
        index_update = archive_index.update(
            files,
            lambda path: iter_conversations(path, strict=True),
            force=args.reindex,
            progress=print_current_file if interactive else None,
        )
        if interactive:
            clear_current_file()
            if index_update.imported_files:
                file_label = plural_key("index.file", index_update.imported_files)
                print(t("index.updated", files=green(index_update.imported_files), file_label=file_label, conversations=green(index_update.imported_conversations)))
            else:
                print(t("index.current", files=green(index_update.unchanged_files)))
        source_ids = archive_index.source_ids(files)
        archive_bounds = archive_index.archive_bounds(source_ids)
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        message = t("index.failure", error=exc)
        write_action_log(t("log.index_update"), "ERREUR", detail=str(index_path), exc=exc)
        print(f"[{t('common.error')}] {message}", file=sys.stderr)
        if interactive:
            show_dialog("showerror", APP_NAME, message)
        return 2

    write_action_log(
        t("log.index_ready"),
        "OK",
        detail=(
            t("log.index_detail", path=index_path, imported=index_update.imported_files, reused=index_update.unchanged_files)
        ),
    )
    if interactive:
        if archive_bounds:
            print(t("date.available", period=green(archive_period_label(archive_bounds))))
        else:
            print(t("date.none_usable"))

    try:
        start_date = parse_french_date(args.date_debut) if args.date_debut else None
        end_date = parse_french_date(args.date_fin, end_of_day=True) if args.date_fin else None
    except ValueError:
        print(f"[{t('common.error')}] {t('date.invalid')}", file=sys.stderr)
        archive_index.close()
        return 2

    terms = parse_query(args.mots_cles or "")
    role_scope = args.role
    if interactive:
        while True:
            print(f"\n{t('date.search_period')}")
            start_date = ask_date(t("date.start"))
            end_date = ask_date(t("date.end"), end_of_day=True)
            if start_date and end_date and start_date > end_date:
                print(t("date.end_before_start"))
                continue
            if not period_overlaps_archive(start_date, end_date, archive_bounds):
                requested_period = t("period.from_to", start=start_date.strftime("%d/%m/%Y") if start_date else t("period.start"), end=end_date.strftime("%d/%m/%Y") if end_date else t("period.present"))
                print(t("date.no_conversation", period=requested_period))
                if archive_bounds:
                    print(t("date.archive_coverage", period=green(archive_period_label(archive_bounds))))
                print(t("date.retry"))
                continue
            break
        terms = ask_query()
        role_scope = ask_role_scope()
    elif start_date and end_date and start_date > end_date:
        print(f"[{t('common.error')}] {t('date.end_before_start')}", file=sys.stderr)
        archive_index.close()
        return 2

    if not period_overlaps_archive(start_date, end_date, archive_bounds):
        available = archive_period_label(archive_bounds) if archive_bounds else t("common.unknown")
        message = t("date.no_overlap", available=available)
        write_action_log(t("log.period_check"), "ERREUR", detail=message)
        print(f"[{t('common.error')}] {message}", file=sys.stderr)
        archive_index.close()
        return 2
    if not any(not term.excluded for term in terms):
        print(f"[{t('common.error')}] {t('query.required')}", file=sys.stderr)
        archive_index.close()
        return 2

    all_labels = format_query(terms)
    write_action_log(
        t("log.search_configured"),
        "OK",
        detail=(
            t("log.search_detail", files=len(files), start=start_date, end=end_date, query=all_labels, scope=role_scope)
        ),
    )
    if interactive:
        label = plural_key("search.selected", len(files))
        print(f"\n{green(len(files))} {label}.")
        print(t("search.working"), flush=True)

    results: list[MiningResult] = []
    matched_conversations: list[tuple[MiningResult, Conversation]] = []
    search_selection = SearchEngine(archive_index, source_ids).search(
        terms, role_scope, start_date, end_date
    )
    conversation_count = search_selection.examined_count
    for conversation in search_selection.conversations:
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
    archive_index.close()
    if interactive:
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
    period = t("period.from_to", start=start_date.strftime("%d/%m/%Y") if start_date else t("period.archive_start"), end=end_date.strftime("%d/%m/%Y") if end_date else t("period.last_exchange"))
    metadata = {
        "application": APP_NAME,
        "version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_files": [str(path) for path in files],
        "index_path": str(index_path),
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
        t("log.finished"),
        "OK",
        detail=t("log.finished_detail", examined=conversation_count, found=len(results), occurrences=occurrences),
    )

    if not args.quiet:
        if not interactive:
            print(f"{APP_NAME} {APP_VERSION}")
        print(f"{plural_key('result.examined', conversation_count)} : {green(conversation_count)}")
        print(f"{plural_key('result.found', len(results))} : {green(len(results))}")
        print(f"{plural_key('result.occurrence', occurrences)} : {green(occurrences)}")
        if not interactive:
            print(f"{t('result.report')} : {green(report_path)}")

    if interactive:
        wait_for_key(t("result.finished", path=green(report_path)))
        webbrowser.open(report_path.as_uri())
        show_dialog(
            "showinfo",
            APP_NAME,
            t("result.dialog", examined_label=plural_key("result.examined", conversation_count), examined=conversation_count, found_label=plural_key("result.found", len(results)), found=len(results), occurrence_label=plural_key("result.occurrence", occurrences), occurrences=occurrences, path=report_path),
        )
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except SystemExit as exc:
        if exc.code not in (None, 0):
            write_action_log(t("log.argument_stop"), "ECHEC", detail=f"code={exc.code}")
        raise
    except BaseException as exc:
        write_action_log(t("log.fatal"), "ERREUR", exc=exc)
        print(f"[{t('common.fatal_error')}] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    else:
        if exit_code != 0:
            write_action_log(t("log.stop"), "ECHEC", detail=f"code={exit_code}")
        raise SystemExit(exit_code)
