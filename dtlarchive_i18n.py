
from __future__ import annotations

import os


DEFAULT_LANGUAGE = "fr"
SUPPORTED_LANGUAGES = {"fr", "en"}
LANGUAGE_ENV_VAR = "DTLARCHIVE_LANG"


TRANSLATIONS: dict[str, dict[str, str]] = {
                                              't0001_startup.switch_to_english': {
                                                  'fr': 'To talk to me in English, type 1.',
                                                  'en': 'To talk to me in English, type 1.',
                                              },
                                              't0002_startup.switch_to_french': {
                                                  'fr': 'Pour me parler en français, tapez 2.',
                                                  'en': 'Pour me parler en français, tapez 2.',
                                              },
                                              't0003_app.subtitle': {
                                                  'fr': 'Explorateur local des archives .json de ChatGPT.',
                                                  'en': 'Local ChatGPT .json archives explorer.',
                                              },
                                              't0004_app.scope_subtitle': {
                                                  'fr': "Recherche effectuée dans les titres et les questions de l'utilisateur.",
                                                  'en': 'Search performed in conversation titles and user questions.',
                                              },
                                              't0005_common.error': {
                                                  'fr': 'ERREUR',
                                                  'en': 'ERROR',
                                              },
                                              't0006_common.fatal_error': {
                                                  'fr': 'ERREUR FATALE',
                                                  'en': 'FATAL ERROR',
                                              },
                                              't0007_common.warning': {
                                                  'fr': 'AVERTISSEMENT',
                                                  'en': 'WARNING',
                                              },
                                              't0008_common.action': {
                                                  'fr': 'ACTION',
                                                  'en': 'ACTION',
                                              },
                                              't0009_common.info': {
                                                  'fr': 'INFO',
                                                  'en': 'INFO',
                                              },
                                              't0010_common.unknown': {
                                                  'fr': 'inconnue',
                                                  'en': 'unknown',
                                              },
                                              't0011_common.help_hint': {
                                                  'fr': "Tapez ? pour obtenir de l'aide contextuelle.",
                                                  'en': 'Type ? for contextual help.',
                                              },
                                              't0012_common.invalid_choice': {
                                                  'fr': 'Choix non reconnu. {help_hint}',
                                                  'en': 'Choice not recognized. {help_hint}',
                                              },
                                              't0013_file.dialog_title': {
                                                  'fr': 'Sélectionnez les archives de conversations ChatGPT',
                                                  'en': 'Select the ChatGPT conversation archives',
                                              },
                                              't0014_file.dialog_archive': {
                                                  'fr': 'Archives ChatGPT JSON',
                                                  'en': 'ChatGPT JSON archives',
                                              },
                                              't0015_file.dialog_json': {
                                                  'fr': 'Fichiers JSON',
                                                  'en': 'JSON files',
                                              },
                                              't0016_file.selection_intro': {
                                                  'fr': "DTLarchive va ouvrir l'explorateur de fichiers pour sélectionner les archives ChatGPT.",
                                                  'en': 'DTLarchive will open File Explorer so you can select the ChatGPT archives.',
                                              },
                                              't0017_file.none_selected': {
                                                  'fr': "Aucune archive ChatGPT n'a été sélectionnée.",
                                                  'en': 'No ChatGPT archive was selected.',
                                              },
                                              't0018_file.press_key': {
                                                  'fr': 'Appuyez sur une touche pour continuer...',
                                                  'en': 'Press any key to continue...',
                                              },
                                              't0019_file.press_key_language': {
                                                  'fr': "Appuyez sur Entrée pour continuer, saisissez 1 pour passer en anglais, ou ? pour obtenir de l'aide.",
                                                  'en': 'Press Enter to continue, or enter 2 to switch to French, or ? for help.',
                                              },
                                              't0020_file.help': {
                                                  'fr': 'Vous allez sélectionner un ou plusieurs fichiers conversations*.json exportés depuis ChatGPT. Vous pourrez en sélectionner plusieurs dans la même fenêtre.',
                                                  'en': 'Select one or more conversations*.json files exported from ChatGPT. You can select several files in the same window.',
                                              },
                                              't0021_date.prompt': {
                                                  'fr': '{label} au format jj/mm/aaaa (vide = aucune limite, ? = aide) : ',
                                                  'en': '{label} in dd/mm/yyyy format (blank = no limit, ? = help): ',
                                              },
                                              't0022_date.start': {
                                                  'fr': 'Date de début',
                                                  'en': 'Start date',
                                              },
                                              't0023_date.end': {
                                                  'fr': 'Date de fin',
                                                  'en': 'End date',
                                              },
                                              't0024_date.invalid': {
                                                  'fr': 'Date invalide. Exemple attendu : 01/06/2026.',
                                                  'en': 'Invalid date. Expected example: 01/06/2026.',
                                              },
                                              't0025_date.help': {
                                                  'fr': 'Saisissez une date au format jour/mois/année, par exemple 01/06/2026. Laissez vide pour ne pas fixer cette limite.',
                                                  'en': 'Enter a date in day/month/year format, for example 01/06/2026. Leave it blank to set no limit.',
                                              },
                                              't0026_date.search_period': {
                                                  'fr': 'Période de recherche (les deux dates sont facultatives).',
                                                  'en': 'Search period (both dates are optional).',
                                              },
                                              't0027_date.available': {
                                                  'fr': 'Période disponible : {period}',
                                                  'en': 'Available period: {period}',
                                              },
                                              't0028_date.none_usable': {
                                                  'fr': "Aucune date de conversation exploitable n'a été trouvée dans les archives.",
                                                  'en': 'No usable conversation date was found in the archives.',
                                              },
                                              't0029_date.end_before_start': {
                                                  'fr': 'La date de fin doit être postérieure ou égale à la date de début.',
                                                  'en': 'The end date must be on or after the start date.',
                                              },
                                              't0030_date.no_conversation': {
                                                  'fr': "Aucune conversation n'existe pour la période demandée ({period}).",
                                                  'en': 'No conversation exists for the requested period ({period}).',
                                              },
                                              't0031_date.archive_coverage': {
                                                  'fr': 'Les archives sélectionnées couvrent la période {period}.',
                                                  'en': 'The selected archives cover {period}.',
                                              },
                                              't0032_date.retry': {
                                                  'fr': 'Veuillez saisir une période qui recoupe les archives.',
                                                  'en': 'Enter a period that overlaps the archives.',
                                              },
                                              't0033_date.no_overlap': {
                                                  'fr': 'La période demandée ne recoupe pas celle des archives ({available}).',
                                                  'en': 'The requested period does not overlap the archive period ({available}).',
                                              },
                                              't0034_period.from_to': {
                                                  'fr': 'du {start} au {end}',
                                                  'en': 'from {start} to {end}',
                                              },
                                              't0035_period.start': {
                                                  'fr': 'début',
                                                  'en': 'the beginning',
                                              },
                                              't0036_period.present': {
                                                  'fr': 'présent',
                                                  'en': 'the present',
                                              },
                                              't0037_period.archive_start': {
                                                  'fr': 'début des archives',
                                                  'en': 'the beginning of the archives',
                                              },
                                              't0038_period.last_exchange': {
                                                  'fr': 'dernier échange',
                                                  'en': 'the latest conversation',
                                              },
                                              't0039_query.instructions': {
                                                  'fr': 'Saisissez un mot, une expression ou plusieurs recherches séparées par des virgules.',
                                                  'en': 'Enter a word, a phrase, or several searches separated by commas.',
                                              },
                                              't0040_query.examples': {
                                                  'fr': 'Exemples : {one}  {two}  {three}  {four}',
                                                  'en': 'Examples: {one}  {two}  {three}  {four}',
                                              },
                                              't0041_query.syntax': {
                                                  'fr': 'ET exige tous les termes ; OU ou la virgule proposent des alternatives ; -mot exclut ; * complète un mot.',
                                                  'en': 'AND requires every term; OR or a comma provides alternatives; -word excludes; * completes a word.',
                                              },
                                              't0042_query.prompt': {
                                                  'fr': 'Recherche (? = aide) : ',
                                                  'en': 'Search (? = help): ',
                                              },
                                              't0043_query.required': {
                                                  'fr': 'Saisissez au moins un mot-clé à rechercher.',
                                                  'en': 'Enter at least one keyword to search for.',
                                              },
                                              't0044_query.help': {
                                                  'fr': "Saisissez des mots présents dans les conversations. Utilisez ET pour exiger plusieurs termes, OU pour accepter des alternatives, -mot pour exclure et * pour rechercher le début d'un mot.",
                                                  'en': 'Enter words found in conversations. Use AND to require several terms, OR for alternatives, -word to exclude, and * to search for the beginning of a word.',
                                              },
                                              't0045_query.label': {
                                                  'fr': 'Recherche',
                                                  'en': 'Search',
                                              },
                                              't0046_scope.question': {
                                                  'fr': 'Où faut-il chercher ?',
                                                  'en': 'Where should DTLarchive search?',
                                              },
                                              't0047_scope.user': {
                                                  'fr': "Titres et questions de l'utilisateur",
                                                  'en': 'Titles and user questions',
                                              },
                                              't0048_scope.assistant': {
                                                  'fr': 'Titres et réponses de ChatGPT',
                                                  'en': 'Titles and ChatGPT answers',
                                              },
                                              't0049_scope.both': {
                                                  'fr': 'Titres, questions et réponses',
                                                  'en': 'Titles, questions, and answers',
                                              },
                                              't0050_scope.prompt': {
                                                  'fr': 'Choix [1] (? = aide) : ',
                                                  'en': 'Choice [1] (? = help): ',
                                              },
                                              't0051_scope.invalid': {
                                                  'fr': 'Répondez 1, 2 ou 3.',
                                                  'en': 'Enter 1, 2, or 3.',
                                              },
                                              't0052_scope.help': {
                                                  'fr': 'Le titre est toujours un champ de recherche. Choisissez 1 pour vos questions, 2 pour les réponses de ChatGPT, ou 3 pour les deux.',
                                                  'en': 'Titles are always searched. Choose 1 for your questions, 2 for ChatGPT answers, or 3 for both.',
                                              },
                                              't0053_role.user': {
                                                  'fr': '👤 Utilisateur',
                                                  'en': '👤 User',
                                              },
                                              't0054_role.assistant': {
                                                  'fr': '🤖 ChatGPT',
                                                  'en': '🤖 ChatGPT',
                                              },
                                              't0055_role.title': {
                                                  'fr': 'Titre',
                                                  'en': 'Title',
                                              },
                                              't0056_conversation.untitled': {
                                                  'fr': '(sans titre)',
                                                  'en': '(untitled)',
                                              },
                                              't0057_conversation.unknown_date': {
                                                  'fr': 'Date inconnue',
                                                  'en': 'Unknown date',
                                              },
                                              't0058_relevance.very': {
                                                  'fr': 'Très pertinent',
                                                  'en': 'Highly relevant',
                                              },
                                              't0059_relevance.relevant': {
                                                  'fr': 'Pertinent',
                                                  'en': 'Relevant',
                                              },
                                              't0060_relevance.secondary': {
                                                  'fr': 'Mention secondaire',
                                                  'en': 'Secondary mention',
                                              },
                                              't0061_index.updating': {
                                                  'fr': "Mise à jour de l'index local...",
                                                  'en': 'Updating the local index...',
                                              },
                                              't0062_index.updated': {
                                                  'fr': 'Index mis à jour : {files} {file_label}, {conversations} conversations importées.',
                                                  'en': 'Index updated: {files} {file_label}, {conversations} conversations imported.',
                                              },
                                              't0063_index.file.one': {
                                                  'fr': 'archive indexée',
                                                  'en': 'archive indexed',
                                              },
                                              't0064_index.file.many': {
                                                  'fr': 'archives indexées',
                                                  'en': 'archives indexed',
                                              },
                                              't0065_index.current': {
                                                  'fr': 'Index déjà à jour : {files} archives réutilisées.',
                                                  'en': 'Index already up to date: {files} archives reused.',
                                              },
                                              't0066_index.failure': {
                                                  'fr': "Impossible de mettre à jour l'index SQLite : {error}",
                                                  'en': 'Unable to update the SQLite index: {error}',
                                              },
                                              't0067_index.incompatible': {
                                                  'fr': "Version d'index incompatible : {current} (attendue : {expected}).",
                                                  'en': 'Incompatible index version: {current} (expected: {expected}).',
                                              },
                                              't0068_search.selected.one': {
                                                  'fr': 'fichier sélectionné',
                                                  'en': 'file selected',
                                              },
                                              't0069_search.selected.many': {
                                                  'fr': 'fichiers sélectionnés',
                                                  'en': 'files selected',
                                              },
                                              't0070_search.working': {
                                                  'fr': "Recherche dans l'index local, merci de patienter...",
                                                  'en': 'Searching the local index, please wait...',
                                              },
                                              't0071_result.examined.one': {
                                                  'fr': 'Conversation examinée',
                                                  'en': 'Conversation examined',
                                              },
                                              't0072_result.examined.many': {
                                                  'fr': 'Conversations examinées',
                                                  'en': 'Conversations examined',
                                              },
                                              't0073_result.found.one': {
                                                  'fr': 'Conversation trouvée',
                                                  'en': 'Conversation found',
                                              },
                                              't0074_result.found.many': {
                                                  'fr': 'Conversations trouvées',
                                                  'en': 'Conversations found',
                                              },
                                              't0075_result.occurrence.one': {
                                                  'fr': 'Occurrence',
                                                  'en': 'Occurrence',
                                              },
                                              't0076_result.occurrence.many': {
                                                  'fr': 'Occurrences',
                                                  'en': 'Occurrences',
                                              },
                                              't0077_result.report': {
                                                  'fr': 'Rapport',
                                                  'en': 'Report',
                                              },
                                              't0078_result.finished': {
                                                  'fr': 'Rapport terminé : {path}\nIl va maintenant être affiché dans votre navigateur.',
                                                  'en': 'Report complete: {path}\nIt will now open in your browser.',
                                              },
                                              't0079_result.dialog': {
                                                  'fr': 'Recherche terminée.\n\n{examined_label} : {examined}\n{found_label} : {found}\n{occurrence_label} : {occurrences}\n\nLe rapport a été ouvert dans votre navigateur.\n{path}',
                                                  'en': 'Search complete.\n\n{examined_label}: {examined}\n{found_label}: {found}\n{occurrence_label}: {occurrences}\n\nThe report has been opened in your browser.\n{path}',
                                              },
                                              't0080_html.back': {
                                                  'fr': '← Retour au rapport',
                                                  'en': '← Back to report',
                                              },
                                              't0081_html.relevance': {
                                                  'fr': 'Pertinence',
                                                  'en': 'Relevance',
                                              },
                                              't0082_html.results': {
                                                  'fr': 'Résultats',
                                                  'en': 'Results',
                                              },
                                              't0083_html.generated': {
                                                  'fr': 'Rapport généré le {date}',
                                                  'en': 'Report generated on {date}',
                                              },
                                              't0084_html.open_conversation': {
                                                  'fr': 'Ouvrir la conversation',
                                                  'en': 'Open conversation',
                                              },
                                              't0085_html.context.one': {
                                                  'fr': 'contexte',
                                                  'en': 'context',
                                              },
                                              't0086_html.context.many': {
                                                  'fr': 'contextes',
                                                  'en': 'contexts',
                                              },
                                              't0087_html.conversation.one': {
                                                  'fr': 'conversation',
                                                  'en': 'conversation',
                                              },
                                              't0088_html.conversation.many': {
                                                  'fr': 'conversations',
                                                  'en': 'conversations',
                                              },
                                              't0089_html.files': {
                                                  'fr': 'Fichiers',
                                                  'en': 'Files',
                                              },
                                              't0090_html.automatic_summary': {
                                                  'fr': 'Résumé automatique',
                                                  'en': 'Automatic summary',
                                              },
                                              't0091_html.search_appears': {
                                                  'fr': 'La recherche apparaît dans {count} {label}.',
                                                  'en': 'The search appears in {count} {label}.',
                                              },
                                              't0092_html.term_distribution': {
                                                  'fr': 'Répartition des termes',
                                                  'en': 'Term distribution',
                                              },
                                              't0093_html.main_subjects': {
                                                  'fr': 'Principaux sujets',
                                                  'en': 'Main subjects',
                                              },
                                              't0094_html.no_result': {
                                                  'fr': 'Aucun résultat',
                                                  'en': 'No result',
                                              },
                                              't0095_html.no_subject': {
                                                  'fr': 'Aucun sujet',
                                                  'en': 'No subject',
                                              },
                                              't0096_html.date': {
                                                  'fr': 'Date',
                                                  'en': 'Date',
                                              },
                                              't0097_html.conversation': {
                                                  'fr': 'Conversation',
                                                  'en': 'Conversation',
                                              },
                                              't0098_html.keywords_roles': {
                                                  'fr': 'Mots-clés et rôles',
                                                  'en': 'Keywords and roles',
                                              },
                                              't0099_html.occurrences': {
                                                  'fr': 'Occurrences',
                                                  'en': 'Occurrences',
                                              },
                                              't0100_html.context': {
                                                  'fr': 'Contexte',
                                                  'en': 'Context',
                                              },
                                              't0101_log.title': {
                                                  'fr': 'Journal',
                                                  'en': 'Log',
                                              },
                                              't0102_log.created': {
                                                  'fr': 'Créé le {date}',
                                                  'en': 'Created on {date}',
                                              },
                                              't0103_log.file_selection': {
                                                  'fr': 'Sélection des archives',
                                                  'en': 'Archive selection',
                                              },
                                              't0104_log.archive_read': {
                                                  'fr': "Lecture d'une archive",
                                                  'en': 'Reading an archive',
                                              },
                                              't0105_log.start': {
                                                  'fr': "Démarrage de l'explorateur",
                                                  'en': 'Starting the archive explorer',
                                              },
                                              't0106_log.index_update': {
                                                  'fr': "Mise à jour de l'index SQLite",
                                                  'en': 'Updating the SQLite index',
                                              },
                                              't0107_log.index_ready': {
                                                  'fr': 'Index SQLite prêt',
                                                  'en': 'SQLite index ready',
                                              },
                                              't0108_log.index_detail': {
                                                  'fr': 'base={path} | importées={imported} | réutilisées={reused}',
                                                  'en': 'database={path} | imported={imported} | reused={reused}',
                                              },
                                              't0109_log.period_check': {
                                                  'fr': 'Contrôle de la période',
                                                  'en': 'Checking the period',
                                              },
                                              't0110_log.search_configured': {
                                                  'fr': 'Recherche configurée',
                                                  'en': 'Search configured',
                                              },
                                              't0111_log.search_detail': {
                                                  'fr': 'fichiers={files} | période={start} à {end} | recherche={query} | périmètre={scope}',
                                                  'en': 'files={files} | period={start} to {end} | search={query} | scope={scope}',
                                              },
                                              't0112_log.finished': {
                                                  'fr': 'Fouille terminée',
                                                  'en': 'Archive search complete',
                                              },
                                              't0113_log.finished_detail': {
                                                  'fr': 'conversations examinées={examined} | trouvées={found} | occurrences={occurrences}',
                                                  'en': 'conversations examined={examined} | found={found} | occurrences={occurrences}',
                                              },
                                              't0114_log.argument_stop': {
                                                  'fr': "Arrêt demandé par l'analyse des paramètres",
                                                  'en': 'Stop requested while parsing arguments',
                                              },
                                              't0115_log.fatal': {
                                                  'fr': 'Exception fatale de DTLarchive',
                                                  'en': 'Fatal DTLarchive exception',
                                              },
                                              't0116_log.stop': {
                                                  'fr': 'Arrêt de DTLarchive',
                                                  'en': 'DTLarchive stopped',
                                              },
                                              't0117_arg.description': {
                                                  'fr': 'Recherche généraliste dans les archives ChatGPT.',
                                                  'en': 'General search through ChatGPT archives.',
                                              },
                                              't0118_arg.inputs': {
                                                  'fr': 'fichiers conversations*.json ou dossiers',
                                                  'en': 'conversations*.json files or folders',
                                              },
                                              't0119_arg.output': {
                                                  'fr': 'dossier de sortie',
                                                  'en': 'output folder',
                                              },
                                              't0120_arg.start': {
                                                  'fr': 'date de début inclusive au format jj/mm/aaaa',
                                                  'en': 'inclusive start date in dd/mm/yyyy format',
                                              },
                                              't0121_arg.end': {
                                                  'fr': 'date de fin inclusive au format jj/mm/aaaa',
                                                  'en': 'inclusive end date in dd/mm/yyyy format',
                                              },
                                              't0122_arg.keywords': {
                                                  'fr': 'mots ou expressions séparés par des virgules',
                                                  'en': 'words or phrases separated by commas',
                                              },
                                              't0123_arg.index': {
                                                  'fr': "chemin de la base d'index SQLite",
                                                  'en': 'SQLite index database path',
                                              },
                                              't0124_arg.reindex': {
                                                  'fr': "reconstruire entièrement l'index",
                                                  'en': 'fully rebuild the index',
                                              },
                                              't0125_arg.role': {
                                                  'fr': 'chercher dans les questions, les réponses ou les deux',
                                                  'en': 'search questions, answers, or both',
                                              },
                                              't0126_arg.lang': {
                                                  'fr': "langue de l'interface",
                                                  'en': 'interface language',
                                              },
                                              't0127_arg.pattern': {
                                                  'fr': "motif des noms de fichiers d'archive",
                                                  'en': 'archive filename pattern',
                                              },
                                              't0128_arg.quiet': {
                                                  'fr': 'masquer le résumé des résultats',
                                                  'en': 'hide the result summary',
                                              },
                                              't0129_arg.help': {
                                                  'fr': 'afficher cette aide et quitter',
                                                  'en': 'show this help message and exit',
                                              },
                                              't0130_arg.version': {
                                                  'fr': 'afficher la version du programme et quitter',
                                                  'en': 'show the program version and exit',
                                              },
                                              't0131_arg.usage': {
                                                  'fr': 'utilisation :',
                                                  'en': 'usage:',
                                              },
                                              't0132_arg.positionals': {
                                                  'fr': 'arguments positionnels :',
                                                  'en': 'positional arguments:',
                                              },
                                              't0133_arg.options': {
                                                  'fr': 'options :',
                                                  'en': 'options:',
                                              },
                                              't0134_brand.suite': {
                                                  'fr': 'Un outil de la suite NetDTL',
                                                  'en': 'A tool from the NetDTL suite',
                                              },
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
