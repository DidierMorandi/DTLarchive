from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from DTLarchive import (
    Conversation,
    Message,
    MiningResult,
    ask_query,
    current_language,
    GREEN_COLOR,
    parse_args,
    parse_query,
    print_console_header,
    wait_for_key,
    write_conversation_page,
    write_html_report,
)
from dtlarchive_i18n import LANGUAGE_ENV_VAR, set_language, t


class InternationalisationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_language = os.environ.get(LANGUAGE_ENV_VAR)

    def tearDown(self) -> None:
        if self.previous_language is None:
            os.environ.pop(LANGUAGE_ENV_VAR, None)
        else:
            os.environ[LANGUAGE_ENV_VAR] = self.previous_language

    def test_catalog_translates_interface_text(self) -> None:
        set_language("fr")
        self.assertEqual(t("scope.user"), "Titres et questions de l'utilisateur")
        set_language("en")
        self.assertEqual(t("scope.user"), "Titles and user questions")

    def test_english_and_or_operators_are_parsed(self) -> None:
        terms = parse_query("asylum AND lucky OR pension")
        self.assertEqual(
            [(term.text, term.group) for term in terms],
            [("asylum", 0), ("lucky", 0), ("pension", 1)],
        )

    def test_subtitle_ends_with_english_switch_phrase(self) -> None:
        set_language("fr")
        output = io.StringIO()
        with redirect_stdout(output):
            print_console_header()
        plain_output = output.getvalue().replace(GREEN_COLOR, "").replace("\033[0m", "")
        lines = [line for line in plain_output.splitlines() if line]
        self.assertEqual(plain_output.count("To talk to me in English, type 1"), 1)
        self.assertEqual(lines[-1], "To talk to me in English, type 1")
        self.assertIn(f"type {GREEN_COLOR}1\033[0m", output.getvalue())

    def test_initial_contextual_help_then_language_switch(self) -> None:
        set_language("fr")
        output = io.StringIO()
        with patch("builtins.input", side_effect=["?", "1", ""]), redirect_stdout(output):
            wait_for_key(
                t("file.selection_intro"),
                allow_language_switch=True,
                help_key="file.help",
                message_key="file.selection_intro",
            )
        self.assertIn("fichiers conversations*.json", output.getvalue())
        self.assertIn("DTLarchive will open File Explorer", output.getvalue())
        self.assertEqual(current_language(), "en")

    def test_contextual_help_returns_to_query(self) -> None:
        set_language("en")
        output = io.StringIO()
        with patch("builtins.input", side_effect=["?", "asylum AND lucky"]), redirect_stdout(output):
            terms = ask_query()
        self.assertEqual([term.text for term in terms], ["asylum", "lucky"])
        self.assertIn("Use AND", output.getvalue())

    def test_lang_argument_localizes_help_parser(self) -> None:
        set_language("en")
        args = parse_args(["--lang", "en", "--mots-cles", "test"])
        self.assertEqual(args.lang, "en")

    def test_conversation_page_uses_selected_language(self) -> None:
        set_language("en")
        conversation = Conversation(
            "archive.json", "id", "Test", None, None, [Message("1", "user", "Hello")]
        )
        result = MiningResult(
            "archive.json", "id", "Test", "Unknown date", ["hello"], 1, 1, 80, "Highly relevant"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "conversation.html"
            write_conversation_page(path, conversation, result)
            document = path.read_text(encoding="utf-8")
        self.assertIn('lang="en"', document)
        self.assertIn("Back to report", document)
        self.assertIn("Relevance", document)

    def test_main_report_uses_selected_language(self) -> None:
        set_language("en")
        result = MiningResult(
            "archive.json", "id", "Test", "01/01/2026 10:00", ["hello"], 1, 1, 80, "Highly relevant"
        )
        result.conversation_url = "conversations/test.html"
        metadata = {
            "recherche": ["hello"],
            "scope_label": "Titles and user questions",
            "periode": "from the beginning to the latest conversation",
            "fichiers": 1,
            "conversations_lues": 1,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.html"
            write_html_report(path, [result], metadata)
            document = path.read_text(encoding="utf-8")
        self.assertIn('lang="en"', document)
        self.assertIn("Automatic summary", document)
        self.assertIn("Open conversation", document)
        self.assertNotIn("Résumé automatique", document)


if __name__ == "__main__":
    unittest.main()
