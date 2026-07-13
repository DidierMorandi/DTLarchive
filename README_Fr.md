# DTLarchive

Version actuelle : **v2.1-1**

[English version](README.md)

DTLarchive est un outil local de fouille et de recherche dans les archives de
conversations ChatGPT. Il permet de retrouver toutes les conversations qui
contiennent un mot, une expression ou une combinaison de mots-clés, quel que
soit leur sujet.

Par défaut, DTLarchive recherche uniquement dans les titres des conversations
et les questions de l'utilisateur. Il peut également chercher dans les titres
et les réponses de ChatGPT, ou dans les titres et les messages des deux rôles.
Tout le traitement reste sur l'ordinateur : aucune archive ni recherche n'est
envoyée à un service en ligne.

## Utilisation de l'exécutable Windows

1. Ouvrez `DTLarchive.exe`.
2. Appuyez sur une touche à l'invite, puis sélectionnez un ou plusieurs fichiers
   `conversations*.json` provenant d'un export ChatGPT.
3. Consultez la période réellement couverte par les conversations choisies.
4. Saisissez éventuellement une date de début et une date de fin inclusives au
   format `jj/mm/aaaa`. Laissez un champ vide pour supprimer cette limite.
5. Saisissez les mots-clés et choisissez où effectuer la recherche.
6. Patientez pendant le traitement, puis appuyez sur une touche pour ouvrir le
   rapport HTML dans le navigateur par défaut.

DTLarchive contrôle la période demandée avant de demander les mots-clés. Une
période qui ne recoupe pas les archives sélectionnées est refusée et doit être
saisie à nouveau. Une période partiellement couverte reste valable et la
recherche porte sur la partie réellement disponible. Si les deux dates sont
laissées vides, l'ensemble de l'archive est pris en compte.

## Syntaxe de recherche

- `retraite` recherche un mot ;
- `carte blanche` recherche l'expression complète ;
- `mutuelle, assurance` trouve les conversations contenant l'un ou l'autre ;
- `asile ET lucky` exige la présence des deux termes dans la même conversation ;
- `asile ET lucky, retraite` signifie `(asile ET lucky) OU retraite` ;
- `asile OU retraite` utilise explicitement des termes alternatifs ;
- `"asile" ET "lucky"` accepte également les termes entre guillemets ;
- `imprim*` trouve les mots commençant par `imprim` ;
- `sauvegarde, -réseau` trouve `sauvegarde` mais exclut les conversations qui
  contiennent `réseau`.

`ET` est l'opérateur logique ET. `OU`, la virgule et le point-virgule sont des
opérateurs logiques OU. Un signe moins placé devant un terme l'exclut. La
recherche ignore les majuscules et les accents. Un singulier simple trouve aussi
sa forme plurielle courante.

## Périmètre de recherche

Le mode interactif propose trois périmètres :

1. titres et questions de l'utilisateur — choix par défaut ;
2. titres et réponses de ChatGPT ;
3. titres, questions de l'utilisateur et réponses de ChatGPT.

Les titres des conversations sont inclus dans tous les périmètres.

## Ligne de commande

DTLarchive accepte des fichiers d'archive individuels ou des dossiers. Dans un
dossier, il sélectionne par défaut les fichiers `conversations*.json`.

```powershell
python .\DTLarchive.py D:\Archives\ChatGPT `
  --mots-cles "asile ET lucky, OFPRA" `
  --date-debut 01/01/2024 `
  --date-fin 31/12/2025 `
  --role user
```

Les mêmes options peuvent être transmises à `DTLarchive.exe`. Les périmètres
disponibles sont `--role user`, `--role assistant` et `--role both`.

Options utiles :

- `--output CHEMIN` choisit le dossier de sortie ;
- `--pattern MOTIF` modifie le motif des noms de fichiers d'archive ;
- `--quiet` masque le résumé des résultats dans la console ;
- `--version` affiche la version du programme.

En ligne de commande, une date invalide, une période inversée ou une période
extérieure aux archives provoque un arrêt avec le code de sortie `2`.

## Résultats générés

En mode interactif, les fichiers suivants sont créés à côté de l'application :

```text
DTLarchive-output\
├── conversations\
│   └── conversation-<identifiant>.html
├── DTLarchive-report.html
└── mining_results.json
```

Le rapport principal contient :

- la recherche, le périmètre, la période demandée et les statistiques du
  traitement ;
- une ligne par conversation trouvée, avec sa date, son titre et son fichier
  source ;
- les mots-clés, les rôles concernés et le nombre d'occurrences ;
- un score et un libellé de pertinence ;
- jusqu'à deux messages avant et après une correspondance pour restituer le
  contexte immédiat ;
- un bouton ouvrant une copie HTML locale de la conversation complète au niveau
  du premier message correspondant ;
- un aperçu automatique de la répartition des termes et des principaux titres
  de conversations.

Le score de pertinence privilégie les correspondances dans le titre, puis dans
les questions de l'utilisateur et enfin dans les réponses de ChatGPT. Il
augmente aussi avec le nombre d'occurrences et de termes distincts trouvés. Les
résultats sont classés du score le plus élevé au plus faible.

Le fichier `mining_results.json` contient les mêmes résultats et les informations
du traitement dans un format réutilisable par d'autres outils.

## Journal de diagnostic

Chaque lancement ajoute les événements de diagnostic dans un journal HTML en
couleurs :

```text
logs\DTLarchive_AAAAMMJJ.html
```

Le journal enregistre le démarrage, les paramètres choisis, les recherches
terminées et les erreurs fatales ou liées aux saisies, sans envoyer
d'information hors de l'ordinateur.
