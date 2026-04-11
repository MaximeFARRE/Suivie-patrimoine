# Architecture - Patrimoine Desktop

Dernière mise à jour: 2026-04-11
Périmètre: architecture réellement observée dans le code actuel.

## 1. Vue d'ensemble de l'application
L'application est une desktop app PyQt6 de suivi patrimonial familial.

Chemin principal d'exécution:

```text
main.py
  -> core/db_connection.py (init DB + connexion singleton)
  -> qt_ui/main_window.py (navigation + pages)
  -> qt_ui/pages/* + qt_ui/panels/*
  -> services/* (métier, calculs, imports, projections)
  -> services/repositories.py + SQL direct + db/schema.sql
```

Architecture dominante observée:
- structure majoritaire orientée `UI -> services -> DB`.
- mais avec des écarts importants: SQL et agrégations métier encore présents dans certains composants UI.

## 2. Arborescence logique du projet
Arborescence logique (couches actives):

```text
main.py                          # bootstrap app, logging, backup DB
core/
  db_connection.py               # singleton connexion, init et seed

qt_ui/
  main_window.py                 # shell app + navigation + recherche globale
  pages/                         # pages racines (famille, personnes, import, objectifs, settings)
  panels/                        # vues métier détaillées
  widgets/                       # composants UI réutilisables
  components/                    # animation, skeleton, stack

services/
  db.py                          # connexion sqlite/libsql, migrations, helpers DB
  repositories.py                # accès CRUD génériques
  snapshots.py / family_snapshots.py
  cashflow.py / credits.py / liquidites.py
  bourse_analytics.py / bourse_advanced_analytics.py
  projections.py / prevision*.py
  imports.py / tr_import.py / import_history.py
  market_history.py / fx.py / pricing.py / isin_resolver.py
  pdf_export.py

db/
  schema.sql
  migrations/*.sql

tests/
  test_*.py                      # tests surtout orientés services

pages/
  3_Import.py                    # ancien Streamlit (legacy)
```

## 3. Description des couches

### 3.1 UI / pages / panels / widgets
Couche concernée:
- `qt_ui/main_window.py`
- `qt_ui/pages/*`
- `qt_ui/panels/*`
- `qt_ui/widgets/*`

Responsabilités réellement présentes:
- navigation et orchestration d'écrans,
- rendu des tableaux/graphes,
- interactions utilisateur,
- déclenchement de rebuild snapshots en thread,
- recherche globale multi-objets.

Écarts observés:
- du SQL direct est fait dans l'UI (exemples concrets):
  - `qt_ui/main_window.py`: `_query_global_search` exécute plusieurs requêtes SQL.
  - `qt_ui/pages/import_page.py`: lookup `people/accounts` en SQL direct.
  - `qt_ui/panels/compte_bourse_panel.py`, `credits_overview_panel.py`, `saisie_panel.py`: requêtes SQL ponctuelles.

Conclusion: couche UI = mélange orchestration + une partie accès données (non idéal).

### 3.2 Services métier
Couche concernée: `services/*`.

Responsabilités réellement présentes:
- calculs patrimoniaux hebdo (`snapshots.py`, `family_snapshots.py`),
- KPI cashflow/épargne (`cashflow.py`),
- crédits (fiche, amortissement, coût réel) (`credits.py`),
- bourse live/perf/diagnostics (`bourse_analytics.py`),
- analytics avancées risques (`bourse_advanced_analytics.py`),
- projections et scénarios (`projections.py`, `prevision*.py`),
- imports CSV et historique/rollback (`imports.py`, `tr_import.py`, `import_history.py`).

Observation:
- c'est la couche la plus riche et la plus proche d'une vraie source de vérité métier.
- certaines responsabilités sont dupliquées entre services (ex: variantes rebuild snapshots/famille).

### 3.3 Accès base de données
Couches impliquées:
- `services/db.py`
- `core/db_connection.py`
- `services/repositories.py`
- SQL direct ponctuel dans UI et certains services.

Responsabilités réellement présentes:
- init DB + migrations SQL + migrations code versionnées,
- connexion locale SQLite (WAL) ou libsql/Turso avec wrapper de compat Row,
- CRUD générique via `repositories.py`.

Particularités:
- coexistence de 2 styles d'accès:
  - style repository,
  - style SQL inline dans différents modules.

### 3.4 Analytics / calculs
Modules principaux:
- `services/calculations.py`
- `services/bourse_analytics.py`
- `services/bourse_advanced_analytics.py`
- `services/vue_ensemble_metrics.py`
- `services/projections.py`
- `services/prevision*`

Responsabilités réelles:
- calculs de soldes, cashflow, perf, CAGR,
- métriques de risque (Sharpe, VaR/ES, corrélations, contributions),
- projections déterministes + stress + Monte Carlo (prévision).

État constaté:
- couche analytique puissante mais dispersée sur plusieurs modules longs.

### 3.5 Import / export / sync / API externes
Modules:
- import: `services/imports.py`, `services/tr_import.py`, `services/import_history.py`
- export: `services/pdf_export.py`
- sync marché/FX: `services/market_history.py`
- pricing live/FX: `services/pricing.py`, `services/fx.py`
- résolution ISIN: `services/isin_resolver.py`

APIs externes réellement utilisées:
- `yfinance`
- OpenFIGI
- Frankfurter API
- Trade Republic via CLI `pytr`

Zone floue / sensible:
- les comportements de fallback réseau sont répartis dans plusieurs services, pas centralisés.

## 4. Flux de données principaux

### Flux A - Démarrage
1. `main.py` configure logs/thème/exception handler.
2. `core/db_connection.get_connection()` lance `init_db()`, `seed_minimal()`, migrations.
3. `MainWindow` charge les pages.
4. un thread lance `rebuild_snapshots_person_from_last` au démarrage.

### Flux B - Navigation et affichage personne
1. UI sélectionne personne/compte.
2. Panels appellent services (ex: `vue_ensemble_metrics`, `bourse_analytics`, `credits`).
3. Services lisent DB via repository/SQL.
4. UI render tables/charts.

### Flux C - Import données
1. UI import choisit type (dépenses/revenus/Bankin/TR/crédit).
2. service d'import parse/normalise.
3. écriture DB + enregistrement batch import.
4. rollback possible via `import_history`.

### Flux D - Données marché et FX
1. services snapshots/bourse déclenchent sync weekly/live.
2. récupération prix/fx via yfinance (+ fallback/pivot FX).
3. stockage tables `asset_prices_weekly` / `fx_rates_weekly`.
4. valorisation patrimoine/positions.

### Flux E - Projections
1. UI objectifs/scénarios lit base patrimoniale.
2. `projections.py` et `prevision*.py` calculent trajectoires.
3. UI affiche courbes/scénarios/milestones.

## 5. Règles de dépendances entre couches (état actuel)
Règle souhaitée dans le code:
- UI dépend des services.
- services dépendent de DB/repositories.
- DB ne dépend pas de UI.

Réalité observée:
- majoritairement respectée,
- mais violations régulières côté UI (requêtes SQL directes).

Règles pratiques actuellement suivies partiellement:
- pas d'import UI depuis services internes privés (globalement vrai),
- services centraux utilisés pour KPI principaux (souvent vrai),
- exceptions fréquentes sur lookup SQL dans UI (faux positif d'architecture propre).

## 6. Anti-patterns déjà présents dans le projet

1. SQL dans l'UI
- Exemples: `qt_ui/main_window.py`, `qt_ui/pages/import_page.py`, `qt_ui/panels/*` ciblés.

2. Fichiers monolithiques
- `qt_ui/pages/goals_projection_page.py` (~1500 lignes)
- `qt_ui/pages/import_page.py` (~1300+)
- `qt_ui/panels/bourse_global_panel.py` (~1100)
- `services/snapshots.py` (~1000+)

3. Duplication de logique
- Variantes rebuild snapshots et rebuild famille avec code très proche.
- Multiples helpers techniques quasi équivalents (`_safe_float`, `_row_get`, etc.).

4. Paramètres UI partiellement non branchés
- `settings_page.py` expose des réglages dont l'impact runtime est incomplet.

5. Legacy ambigu conservé dans le repo actif
- `pages/3_Import.py` (Streamlit) cohabite avec la version Qt.

## 7. Règles de refactor à respecter pour l'avenir

1. Déplacer progressivement toute requête SQL UI vers des services dédiés.
2. Maintenir un point d'entrée service unique par KPI métier.
3. Découper les gros modules sans changer le comportement (refactor incrémental).
4. Centraliser les helpers transverses (conversion float/date/row).
5. Ajouter un test de non-régression à chaque correction de bug métier.
6. Mettre à jour la documentation d'architecture dans la même PR que le code.

## 8. Fichiers ou modules sensibles
Sensibles = impact fort + risque de régression:
- `main.py` (bootstrap, backup, fermeture)
- `core/db_connection.py` (lifecycle connexion)
- `services/db.py` (migrations, compat sqlite/libsql)
- `services/snapshots.py` (valeur patrimoniale hebdo)
- `services/family_snapshots.py` (agrégats famille)
- `services/bourse_analytics.py` (positions/perf)
- `services/cashflow.py` (épargne/KPI)
- `services/credits.py` (CRD/amortissements)
- `qt_ui/main_window.py` (navigation globale + recherche + rebuild thread)
- `qt_ui/pages/import_page.py` (pipeline import critique)

## 9. Endroits où la dette technique est la plus forte

1. Frontière UI / data-access
- dette élevée à cause du SQL direct dans la couche présentation.

2. Taille et couplage des modules clés
- objectifs/projections/import/snapshots concentrent beaucoup de responsabilités.

3. Cohérence documentaire et nomenclature
- historique de docs avec noms proches (`SOURCES_DE_VERITE` vs `SOURCE_DE_VERITE`).

4. Paramétrage applicatif
- différences entre options affichées en settings et application effective au runtime.

5. Couverture de tests d'intégration UI
- bonne couverture services, couverture UI-end-to-end limitée.

## Règles d'évolution de l'architecture
Principes simples pour éviter la dégradation:

1. Une fonctionnalité métier = un service référent explicite.
2. UI sans SQL métier (tolérer seulement wiring temporaire, documenté et daté).
3. Toute nouvelle logique de fallback vit côté service, pas côté panel.
4. Toute règle métier modifiée doit être couverte par un test dédié.
5. Les gros fichiers doivent être découpés avant ajout massif de nouvelles features.
6. Toute exception d'architecture doit être listée ici avec plan de sortie.
7. Documentation et code évoluent ensemble (pas de doc différée).
