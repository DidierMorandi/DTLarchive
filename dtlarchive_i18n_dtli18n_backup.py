
from __future__ import annotations

import os


DEFAULT_LANGUAGE = "fr"
SUPPORTED_LANGUAGES = {"fr", "en"}
LANGUAGE_ENV_VAR = "DTLARCHIVE_LANG"


TRANSLATIONS: dict[str, dict[str, str]] = {
    "startup.switch_to_english": {"fr": "To talk to me in English, type 1.", "en": "To talk to me in English, type 1."},
    "startup.switch_to_french": {"fr": "Pour me parler en français, tapez 2.", "en": "Pour me parler en français, tapez 2."},
    "app.subtitle": {"fr": "Explorateur local des archives .json de ChatGPT", "en": "Local ChatGPT .json archives explorer"},
    "app.scope_subtitle": {"fr": "Recherche dans les titres et les questions de l'utilisateur", "en": "Searches conversation titles and user questions"},
    "common.error": {"fr": "ERREUR", "en": "ERROR"},
    "common.fatal_error": {"fr": "ERREUR FATALE", "en": "FATAL ERROR"},
    "common.warning": {"fr": "AVERTISSEMENT", "en": "WARNING"},
    "common.action": {"fr": "ACTION", "en": "ACTION"},
    "common.info": {"fr": "INFO", "en": "INFO"},
    "common.unknown": {"fr": "inconnue", "en": "unknown"},
    "common.help_hint": {"fr": "Tapez ? pour obtenir de l'aide contextuelle.", "en": "Type ? for contextual help."},
    "common.invalid_choice": {"fr": "Choix non reconnu. {help_hint}", "en": "Choice not recognized. {help_hint}"},
    "file.dialog_title": {"fr": "Sélectionnez les archives de conversations ChatGPT", "en": "Select the ChatGPT conversation archives"},
    "file.dialog_archive": {"fr": "Archives ChatGPT JSON", "en": "ChatGPT JSON archives"},
    "file.dialog_json": {"fr": "Fichiers JSON", "en": "JSON files"},
    "file.selection_intro": {"fr": "DTLarchive va ouvrir l'explorateur de fichiers pour sélectionner les archives ChatGPT.", "en": "DTLarchive will open File Explorer so you can select the ChatGPT archives."},
    "file.none_selected": {"fr": "Aucune archive ChatGPT n'a été sélectionnée.", "en": "No ChatGPT archive was selected."},
    "file.press_key": {"fr": "Appuyez sur une touche pour continuer...", "en": "Press any key to continue..."},
    "file.press_key_language": {"fr": "Appuyez sur Entrée pour continuer, saisissez 1 pour passer en anglais, ou ? pour obtenir de l'aide...", "en": "Press Enter to continue, or enter 2 to switch to French, or ? for help..."},
    "file.help": {"fr": "Vous allez sélectionner un ou plusieurs fichiers conversations*.json exportés depuis ChatGPT. Vous pourrez en sélectionner plusieurs dans la même fenêtre.", "en": "Select one or more conversations*.json files exported from ChatGPT. You can select several files in the same window."},
    "date.prompt": {"fr": "{label} au format jj/mm/aaaa (vide = aucune limite, ? = aide) : ", "en": "{label} in dd/mm/yyyy format (blank = no limit, ? = help): "},
    "date.start": {"fr": "Date de début", "en": "Start date"},
    "date.end": {"fr": "Date de fin", "en": "End date"},
    "date.invalid": {"fr": "Date invalide. Exemple attendu : 01/06/2026.", "en": "Invalid date. Expected example: 01/06/2026."},
    "date.help": {"fr": "Saisissez une date au format jour/mois/année, par exemple 01/06/2026. Laissez vide pour ne pas fixer cette limite.", "en": "Enter a date in day/month/year format, for example 01/06/2026. Leave it blank to set no limit."},
    "date.search_period": {"fr": "Période de recherche (les deux dates sont facultatives).", "en": "Search period (both dates are optional)."},
    "date.available": {"fr": "Période disponible : {period}", "en": "Available period: {period}"},
    "date.none_usable": {"fr": "Aucune date de conversation exploitable n'a été trouvée dans les archives.", "en": "No usable conversation date was found in the archives."},
    "date.end_before_start": {"fr": "La date de fin doit être postérieure ou égale à la date de début.", "en": "The end date must be on or after the start date."},
    "date.no_conversation": {"fr": "Aucune conversation n'existe pour la période demandée ({period}).", "en": "No conversation exists for the requested period ({period})."},
    "date.archive_coverage": {"fr": "Les archives sélectionnées couvrent la période {period}.", "en": "The selected archives cover {period}."},
    "date.retry": {"fr": "Veuillez saisir une période qui recoupe les archives.", "en": "Enter a period that overlaps the archives."},
    "date.no_overlap": {"fr": "La période demandée ne recoupe pas celle des archives ({available}).", "en": "The requested period does not overlap the archive period ({available})."},
    "period.from_to": {"fr": "du {start} au {end}", "en": "from {start} to {end}"},
    "period.start": {"fr": "début", "en": "the beginning"},
    "period.present": {"fr": "présent", "en": "the present"},
    "period.archive_start": {"fr": "début des archives", "en": "the beginning of the archives"},
    "period.last_exchange": {"fr": "dernier échange", "en": "the latest conversation"},
    "query.instructions": {"fr": "Saisissez un mot, une expression ou plusieurs recherches séparées par des virgules.", "en": "Enter a word, a phrase, or several searches separated by commas."},
    "query.examples": {"fr": "Exemples : {one}  {two}  {three}  {four}", "en": "Examples: {one}  {two}  {three}  {four}"},
    "query.syntax": {"fr": "ET exige tous les termes ; OU ou la virgule proposent des alternatives ; -mot exclut ; * complète un mot.", "en": "AND requires every term; OR or a comma provides alternatives; -word excludes; * completes a word."},
    "query.prompt": {"fr": "Recherche (? = aide) : ", "en": "Search (? = help): "},
    "query.required": {"fr": "Saisissez au moins un mot-clé à rechercher.", "en": "Enter at least one keyword to search for."},
    "query.help": {"fr": "Saisissez des mots présents dans les conversations. Utilisez ET pour exiger plusieurs termes, OU pour accepter des alternatives, -mot pour exclure et * pour rechercher le début d'un mot.", "en": "Enter words found in conversations. Use AND to require several terms, OR for alternatives, -word to exclude, and * to search for the beginning of a word."},
    "query.label": {"fr": "Recherche", "en": "Search"},
    "scope.question": {"fr": "Où faut-il chercher ?", "en": "Where should DTLarchive search?"},
    "scope.user": {"fr": "Titres et questions de l'utilisateur", "en": "Titles and user questions"},
    "scope.assistant": {"fr": "Titres et réponses de ChatGPT", "en": "Titles and ChatGPT answers"},
    "scope.both": {"fr": "Titres, questions et réponses", "en": "Titles, questions, and answers"},
    "scope.prompt": {"fr": "Choix [1] (? = aide) : ", "en": "Choice [1] (? = help): "},
    "scope.invalid": {"fr": "Répondez 1, 2 ou 3.", "en": "Enter 1, 2, or 3."},
    "scope.help": {"fr": "Le titre est toujours recherché. Choisissez 1 pour vos questions, 2 pour les réponses de ChatGPT, ou 3 pour les deux.", "en": "Titles are always searched. Choose 1 for your questions, 2 for ChatGPT answers, or 3 for both."},
    "role.user": {"fr": "👤 Utilisateur", "en": "👤 User"},
    "role.assistant": {"fr": "🤖 ChatGPT", "en": "🤖 ChatGPT"},
    "role.title": {"fr": "Titre", "en": "Title"},
    "conversation.untitled": {"fr": "(sans titre)", "en": "(untitled)"},
    "conversation.unknown_date": {"fr": "Date inconnue", "en": "Unknown date"},
    "relevance.very": {"fr": "Très pertinent", "en": "Highly relevant"},
    "relevance.relevant": {"fr": "Pertinent", "en": "Relevant"},
    "relevance.secondary": {"fr": "Mention secondaire", "en": "Secondary mention"},
    "index.updating": {"fr": "Mise à jour de l'index local...", "en": "Updating the local index..."},
    "index.updated": {"fr": "Index mis à jour : {files} {file_label}, {conversations} conversations importées.", "en": "Index updated: {files} {file_label}, {conversations} conversations imported."},
    "index.file.one": {"fr": "archive indexée", "en": "archive indexed"},
    "index.file.many": {"fr": "archives indexées", "en": "archives indexed"},
    "index.current": {"fr": "Index déjà à jour : {files} archives réutilisées.", "en": "Index already up to date: {files} archives reused."},
    "index.failure": {"fr": "Impossible de mettre à jour l'index SQLite : {error}", "en": "Unable to update the SQLite index: {error}"},
    "index.incompatible": {"fr": "Version d'index incompatible : {current} (attendue : {expected}).", "en": "Incompatible index version: {current} (expected: {expected})."},
    "search.selected.one": {"fr": "fichier sélectionné", "en": "file selected"},
    "search.selected.many": {"fr": "fichiers sélectionnés", "en": "files selected"},
    "search.working": {"fr": "Recherche dans l'index local, merci de patienter...", "en": "Searching the local index, please wait..."},
    "result.examined.one": {"fr": "Conversation examinée", "en": "Conversation examined"},
    "result.examined.many": {"fr": "Conversations examinées", "en": "Conversations examined"},
    "result.found.one": {"fr": "Conversation trouvée", "en": "Conversation found"},
    "result.found.many": {"fr": "Conversations trouvées", "en": "Conversations found"},
    "result.occurrence.one": {"fr": "Occurrence", "en": "Occurrence"},
    "result.occurrence.many": {"fr": "Occurrences", "en": "Occurrences"},
    "result.report": {"fr": "Rapport", "en": "Report"},
    "result.finished": {"fr": "Rapport terminé : {path}\nIl va maintenant être affiché dans votre navigateur.", "en": "Report complete: {path}\nIt will now open in your browser."},
    "result.dialog": {"fr": "Recherche terminée.\n\n{examined_label} : {examined}\n{found_label} : {found}\n{occurrence_label} : {occurrences}\n\nLe rapport a été ouvert dans votre navigateur.\n{path}", "en": "Search complete.\n\n{examined_label}: {examined}\n{found_label}: {found}\n{occurrence_label}: {occurrences}\n\nThe report has been opened in your browser.\n{path}"},
    "html.back": {"fr": "← Retour au rapport", "en": "← Back to report"},
    "html.relevance": {"fr": "Pertinence", "en": "Relevance"},
    "html.results": {"fr": "Résultats", "en": "Results"},
    "html.generated": {"fr": "Rapport généré le {date}", "en": "Report generated on {date}"},
    "html.open_conversation": {"fr": "Ouvrir la conversation", "en": "Open conversation"},
    "html.context.one": {"fr": "contexte", "en": "context"},
    "html.context.many": {"fr": "contextes", "en": "contexts"},
    "html.conversation.one": {"fr": "conversation", "en": "conversation"},
    "html.conversation.many": {"fr": "conversations", "en": "conversations"},
    "html.files": {"fr": "Fichiers", "en": "Files"},
    "html.automatic_summary": {"fr": "Résumé automatique", "en": "Automatic summary"},
    "html.search_appears": {"fr": "La recherche apparaît dans {count} {label}.", "en": "The search appears in {count} {label}."},
    "html.term_distribution": {"fr": "Répartition des termes", "en": "Term distribution"},
    "html.main_subjects": {"fr": "Principaux sujets", "en": "Main subjects"},
    "html.no_result": {"fr": "Aucun résultat", "en": "No result"},
    "html.no_subject": {"fr": "Aucun sujet", "en": "No subject"},
    "html.date": {"fr": "Date", "en": "Date"},
    "html.conversation": {"fr": "Conversation", "en": "Conversation"},
    "html.keywords_roles": {"fr": "Mots-clés et rôles", "en": "Keywords and roles"},
    "html.occurrences": {"fr": "Occurrences", "en": "Occurrences"},
    "html.context": {"fr": "Contexte", "en": "Context"},
    "log.title": {"fr": "Journal", "en": "Log"},
    "log.created": {"fr": "Créé le {date}", "en": "Created on {date}"},
    "log.file_selection": {"fr": "Sélection des archives", "en": "Archive selection"},
    "log.archive_read": {"fr": "Lecture d'une archive", "en": "Reading an archive"},
    "log.start": {"fr": "Démarrage de l'explorateur", "en": "Starting the archive explorer"},
    "log.index_update": {"fr": "Mise à jour de l'index SQLite", "en": "Updating the SQLite index"},
    "log.index_ready": {"fr": "Index SQLite prêt", "en": "SQLite index ready"},
    "log.index_detail": {"fr": "base={path} | importées={imported} | réutilisées={reused}", "en": "database={path} | imported={imported} | reused={reused}"},
    "log.period_check": {"fr": "Contrôle de la période", "en": "Checking the period"},
    "log.search_configured": {"fr": "Recherche configurée", "en": "Search configured"},
    "log.search_detail": {"fr": "fichiers={files} | période={start} à {end} | recherche={query} | périmètre={scope}", "en": "files={files} | period={start} to {end} | search={query} | scope={scope}"},
    "log.finished": {"fr": "Fouille terminée", "en": "Archive search complete"},
    "log.finished_detail": {"fr": "conversations examinées={examined} | trouvées={found} | occurrences={occurrences}", "en": "conversations examined={examined} | found={found} | occurrences={occurrences}"},
    "log.argument_stop": {"fr": "Arrêt demandé par l'analyse des paramètres", "en": "Stop requested while parsing arguments"},
    "log.fatal": {"fr": "Exception fatale de DTLarchive", "en": "Fatal DTLarchive exception"},
    "log.stop": {"fr": "Arrêt de DTLarchive", "en": "DTLarchive stopped"},
    "arg.description": {"fr": "Recherche généraliste dans les archives ChatGPT.", "en": "General search through ChatGPT archives."},
    "arg.inputs": {"fr": "fichiers conversations*.json ou dossiers", "en": "conversations*.json files or folders"},
    "arg.output": {"fr": "dossier de sortie", "en": "output folder"},
    "arg.start": {"fr": "date de début inclusive au format jj/mm/aaaa", "en": "inclusive start date in dd/mm/yyyy format"},
    "arg.end": {"fr": "date de fin inclusive au format jj/mm/aaaa", "en": "inclusive end date in dd/mm/yyyy format"},
    "arg.keywords": {"fr": "mots ou expressions séparés par des virgules", "en": "words or phrases separated by commas"},
    "arg.index": {"fr": "chemin de la base d'index SQLite", "en": "SQLite index database path"},
    "arg.reindex": {"fr": "reconstruire entièrement l'index", "en": "fully rebuild the index"},
    "arg.role": {"fr": "chercher dans les questions, les réponses ou les deux", "en": "search questions, answers, or both"},
    "arg.lang": {"fr": "langue de l'interface", "en": "interface language"},
    "arg.pattern": {"fr": "motif des noms de fichiers d'archive", "en": "archive filename pattern"},
    "arg.quiet": {"fr": "masquer le résumé des résultats", "en": "hide the result summary"},
    "arg.help": {"fr": "afficher cette aide et quitter", "en": "show this help message and exit"},
    "arg.version": {"fr": "afficher la version du programme et quitter", "en": "show the program version and exit"},
    "arg.usage": {"fr": "utilisation :", "en": "usage:"},
    "arg.positionals": {"fr": "arguments positionnels :", "en": "positional arguments:"},
    "arg.options": {"fr": "options :", "en": "options:"},
}


def current_language() -> str:
    language = os.environ.get(LANGUAGE_ENV_VAR, DEFAULT_LANGUAGE).strip().lower()
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def set_language(language: str) -> None:
    if language in SUPPORTED_LANGUAGES:
        os.environ[LANGUAGE_ENV_VAR] = language


def t(key: str, **values: object) -> str:
    entry = TRANSLATIONS.get(key)
    template = key if entry is None else entry.get(current_language()) or entry[DEFAULT_LANGUAGE]
    return template.format(**values) if values else template


def plural_key(prefix: str, count: int) -> str:
    return t(f"{prefix}.one" if count == 1 else f"{prefix}.many")
