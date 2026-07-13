# DTLarchive

Current version: **v2.2-0**

[Version française](README_Fr.md)

Repository: [DidierMorandi/DTLarchive](https://github.com/DidierMorandi/DTLarchive)

DTLarchive is a local data-mining and search tool for ChatGPT conversation
archives. It can find every conversation that contains a word, phrase, or
combination of keywords, regardless of topic.

By default, DTLarchive searches conversation titles and user questions only.
You can also search titles and ChatGPT answers, or titles and both roles. The
tool runs entirely on the local computer: no archive or search term is sent to
an online service.

Version 2.2 introduces a persistent SQLite index. JSON exports are parsed only
when they are new or modified; later searches reuse the local full-text index
instead of reading every archive again.

## Using the Windows executable

1. Open `DTLarchive.exe`.
2. Press a key when prompted, then select one or more
   `conversations*.json` files from a ChatGPT export.
3. Let DTLarchive update its local index. Unchanged archives are reused without
   being parsed again.
4. Review the date range actually covered by the selected conversations.
5. Optionally enter an inclusive start date and end date in `dd/mm/yyyy`
   format. Leave either field empty to remove that limit.
6. Enter the keyword query and choose where to search.
7. Wait while the index is searched, then press a key to open the HTML
   report in the default browser.

DTLarchive validates the requested period before asking for keywords. A period
that does not overlap the selected archives is rejected and must be entered
again. A partially overlapping period remains valid and is searched only where
archive data exists. Leaving both dates empty searches the entire archive.

## Query syntax

- `retirement` searches for one word;
- `white card` searches for the complete phrase;
- `insurance, pension` finds conversations containing either term;
- `asylum ET lucky` requires both terms in the same conversation;
- `asylum ET lucky, pension` means `(asylum ET lucky) OU pension`;
- `asylum OU pension` explicitly uses alternative terms;
- `"asylum" ET "lucky"` also accepts quoted terms;
- `print*` finds words beginning with `print`;
- `backup, -network` finds `backup` while excluding conversations containing
  `network`.

`ET` is the AND operator. `OU`, a comma, or a semicolon is the OR operator.
A leading minus sign excludes a term. Searches are case-insensitive and
accent-insensitive. Simple singular forms also match their common plural form.

## Search scope

Interactive mode offers three scopes:

1. titles and user questions — default;
2. titles and ChatGPT answers;
3. titles, user questions, and ChatGPT answers.

Conversation titles are included in every scope.

## Local SQLite index

The default index is stored next to the application:

```text
DTLarchive-index.sqlite
```

The database separates archive import, indexed search, and result analysis. It
contains source-file fingerprints, unique conversations, ordered messages,
source provenance, and an SQLite FTS5 full-text index. A conversation appearing
in several selected exports is stored only once, while its source links are
preserved. When a source changes, DTLarchive keeps the newest available version
of each conversation.

File size and modification time provide the fast unchanged-file check. A
SHA-256 fingerprint prevents unnecessary reimport when only file metadata has
changed. Use `--reindex` when a complete rebuild is required.

## Command line

DTLarchive accepts individual archive files or directories. Directories are
searched for `conversations*.json` by default.

```powershell
python .\DTLarchive.py D:\Archives\ChatGPT `
  --mots-cles "asylum ET lucky, OFPRA" `
  --date-debut 01/01/2024 `
  --date-fin 31/12/2025 `
  --role user
```

The same options can be passed to `DTLarchive.exe`. Available search scopes are
`--role user`, `--role assistant`, and `--role both`.

Useful options:

- `--output PATH` selects the output directory;
- `--pattern PATTERN` changes the archive filename pattern;
- `--index PATH` selects another SQLite index file;
- `--reindex` clears and rebuilds the selected index;
- `--quiet` suppresses the result summary in the console;
- `--version` displays the program version.

An invalid date, a reversed period, or a period outside the archive range stops
command-line execution with exit code `2`.

## Generated results

Interactive runs create the following files next to the application:

```text
DTLarchive-index.sqlite
DTLarchive-output\
├── conversations\
│   └── conversation-<identifier>.html
├── DTLarchive-report.html
└── mining_results.json
```

The main report contains:

- the query, selected scope, requested period, and processing statistics;
- one row per matching conversation, with its date, title, and source file;
- matched keywords, roles, and occurrence count;
- a relevance score and label;
- up to two messages before and after a match for immediate context;
- a button that opens a local HTML copy of the full conversation at the first
  matching message;
- an automatic overview of term distribution and the main conversation titles.

The relevance score prioritizes title matches, followed by user-question
matches and then ChatGPT-answer matches. It also increases with the number of
occurrences and distinct matched terms. Results are sorted from highest to
lowest score.

`mining_results.json` contains the same findings and run metadata in a format
suitable for further processing.

## Diagnostic log

Each run appends diagnostic events to a color HTML log:

```text
logs\DTLarchive_YYYYMMDD.html
```

The log records startup, selected parameters, completed searches, and fatal or
input-related errors. It also indicates how many archive files were imported or
reused from the index, without sending any information outside the computer.

## License

DTLarchive is released under the [MIT License](LICENSE).

Copyright © 2026 Didier DTL Morandi — [www.netdtl.com](https://www.netdtl.com/)
