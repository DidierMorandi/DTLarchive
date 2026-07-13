"""Indexed lexical search layer for DTLarchive."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Sequence

from dtlarchive_index import ArchiveIndex, StoredConversation


@dataclass
class SearchSelection:
    conversations: list[StoredConversation]
    examined_count: int
    candidate_count: int


class SearchEngine:
    """Select candidate conversations without performing result analysis."""

    def __init__(self, index: ArchiveIndex, source_ids: Sequence[int]):
        self.index = index
        self.source_ids = list(source_ids)

    def search(
        self,
        terms: Sequence[Any],
        role_scope: str,
        start_date: dt.datetime | None,
        end_date: dt.datetime | None,
    ) -> SearchSelection:
        examined_count = self.index.conversation_count(
            self.source_ids, start_date, end_date
        )
        candidate_ids = self.index.candidate_ids(
            self.source_ids, terms, role_scope, start_date, end_date
        )
        conversations = self.index.load_conversations(
            sorted(candidate_ids), self.source_ids
        )
        return SearchSelection(
            conversations=conversations,
            examined_count=examined_count,
            candidate_count=len(candidate_ids),
        )
