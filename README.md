# DTLarchive

Version actuelle : **v1.0.0**

DTLarchive analyse les exports JSON de conversations ChatGPT, isole les échanges
techniques utiles à DTL4u, puis les compare à la base de connaissances
`dtl4u_kb.json`.

## Principes de sécurité intellectuelle

- Une proposition de l'assistant n'est jamais considérée comme un fait confirmé.
- Les séquences confirmées par l'utilisateur sont favorisées.
- La KB d'origine n'est jamais modifiée.
- `--apply` crée une copie `dtl4u_kb.enriched.json`.
- Les éléments non confirmés sont classés `UNVERIFIED`.

## Utilisation

Placez dans un même dossier :

```text
DTLarchive.py
dtl4u_kb.json
conversations-000.json
...
conversations-013.json
```

Puis lancez :

```powershell
python .\DTLarchive.py . --kb .\dtl4u_kb.json
```

Pour conserver aussi les pistes non confirmées :

```powershell
python .\DTLarchive.py . --kb .\dtl4u_kb.json --include-unverified
```

Pour produire une copie enrichie de la KB :

```powershell
python .\DTLarchive.py . --kb .\dtl4u_kb.json --apply
```

## Sorties

```text
DTLarchive-output\
├── extracted_knowledge.json
├── kb_comparison.json
├── kb_additions.json
├── kb_conflicts.json
├── unverified.json
├── DTLarchive-report.html
└── dtl4u_kb.enriched.json   # seulement avec --apply
```

## Classement

- `EXISTING` : connaissance déjà bien couverte par la KB.
- `ENRICH` : connaissance proche, mais apportant des observations nouvelles.
- `NEW` : connaissance absente ou très peu représentée.
- `UNVERIFIED` : piste provenant principalement de l'assistant, sans validation utilisateur.

La détection de contradiction explicite sera renforcée dans une version suivante ;
la structure de sortie `kb_conflicts.json` est déjà prévue.

## Limites de la v1

La v1 utilise une extraction déterministe et locale : mots-clés, commandes,
codes d'erreur, confirmations utilisateur et similarité lexicale. Elle ne fait
aucun appel à une IA distante et n'envoie aucune conversation sur Internet.
