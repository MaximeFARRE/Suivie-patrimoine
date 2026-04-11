# AUDIT_GLOBAL

Date d'audit: 2026-04-11
Portee: code present dans le workspace local (application desktop PyQt6).

## Methode
- Lecture ciblee des couches `qt_ui/*`, `services/*`, `core/*`, `db/*`, `tests/*`.
- Verification runtime/tests:
  - `python -m pytest -q` (interrompu par erreurs de collection sur dossiers `pytest-cache-files-*`).
  - `python -m pytest -q tests` (85 tests executes: 83 OK, 2 FAIL).
- Analyse de patterns de risque: SQL direct en UI, modules volumineux, gestion d'erreurs, duplications, points de perf.

## Legende priorite
- `P0`: a traiter immediatement (risque de resultat faux / regression forte).
- `P1`: prochain sprint (qualite/robustesse fortement amelioree).
- `P2`: court terme (maintenabilite/perf).
- `P3`: backlog (amelioration structurelle). 

---

## 1) Architecture

| ID | Gravite | Description | Impact | Fichier(s) concernes | Recommandation concrete | Priorite d'action |
|---|---|---|---|---|---|---|
| A-01 | elevee | Bypass UI -> data/metier via SQL direct dans plusieurs ecrans. | Regles metier dupliquees, maintenance difficile, regressions silencieuses. | `qt_ui/main_window.py`, `qt_ui/pages/import_page.py`, `qt_ui/panels/compte_bourse_panel.py`, `qt_ui/panels/credits_overview_panel.py`, `qt_ui/panels/saisie_panel.py` | Extraire les requetes dans des services dedies (`search_service`, `import_lookup_service`, `bourse_read_service`, etc.). | P1 |
| A-02 | elevee | Modules monolithiques (1000+ lignes) avec responsabilites mixtes. | Difficile a relire, tester, refactorer sans casse. | `qt_ui/pages/goals_projection_page.py`, `qt_ui/pages/import_page.py`, `qt_ui/panels/bourse_global_panel.py`, `services/snapshots.py`, `qt_ui/panels/prevision_avancee_panel.py` | Decoupage par sous-domaines (input mapping, calcul, rendu, orchestration). | P1 |
| A-03 | moyenne | Responsabilites floues dans `vue_ensemble_metrics` (calcul metier + preparation affichage). | Frontiere architecture floue, duplication potentielle avec panel. | `services/vue_ensemble_metrics.py`, `qt_ui/panels/vue_ensemble_panel.py` | Scinder en 2 modules: `*_service.py` (metier) et `*_presenter.py` (DTO/charts). | P2 |
| A-04 | elevee | Deux stacks de projection en production (legacy + prevision avancee). | Cohabitation de comportements differents, confusion technique et produit. | `services/projections.py`, `services/prevision.py`, `qt_ui/pages/goals_projection_page.py`, `qt_ui/panels/prevision_avancee_panel.py` | Introduire une facade unique de projection et migrer progressivement les appels UI. | P0 |
| A-05 | moyenne | Couplage bidirectionnel latent snapshots/bourse (import croise via import local). | Risque de dependance circulaire et d'evolution fragile. | `services/snapshots.py` (import local `bourse_analytics`), `services/bourse_analytics.py` (appel snapshots) | Extraire la fonction partagee de cash bourse dans un module neutre (`services/bourse_cash.py`). | P2 |
| A-06 | faible | Fichiers redondants/obsoletes dans le repo (docs et legacy). | Ambiguite pour les contributeurs, dilution de la source officielle. | `pages/3_Import.py`, `SOURCES_DE_VERITE.md`, `SOURCE_DE_VERITE.md`, `README.md`/`readme.md`, `Patrimoine Desktop.spec`/`patrimoine.spec` | Declarer clairement le canonique, archiver/supprimer les doublons inutiles. | P2 |

---

## 2) Source de verite / coherence metier

| ID | Gravite | Description | Impact | Fichier(s) concernes | Recommandation concrete | Priorite d'action |
|---|---|---|---|---|---|---|
| S-01 | critique | Coherence epargne brisee: 2 tests metier en echec sur `vue_ensemble_metrics`. | KPI faux possibles (capacite epargne moyenne, serie mensuelle). | `services/cashflow.py`, `services/vue_ensemble_metrics.py`, `tests/test_vue_ensemble_metrics.py` | Corriger d'abord la convention (mois calendaires vs mois observes), puis figer via tests de non-regression. | P0 |
| S-02 | elevee | Serie epargne `get_person_monthly_savings_series` ne preserve pas les mois manquants. | Moyennes/indicateurs biaisés (ex: moyenne sur mois actifs uniquement). | `services/cashflow.py` | Reindexer explicitement sur calendrier mensuel entre bornes (fill zeros). | P0 |
| S-03 | elevee | Conversions FX divergentes selon modules (`convert_weekly`, `fx.convert`, `_fx_to_eur`). | Meme donnee potentiellement valorisee differemment selon ecran/service. | `services/market_history.py`, `services/fx.py`, `services/liquidites.py` | Definir une politique unique de conversion/fallback et l'appliquer partout. | P0 |
| S-04 | elevee | `liquidites._fx_to_eur` retourne le montant brut si taux absent. | Comportement silencieusement faux (montant non converti traite comme EUR). | `services/liquidites.py` | Retourner `None` si FX manquant + propager l'etat d'erreur jusqu'au UI. | P0 |
| S-05 | moyenne | Agregations famille partagees entre `family_snapshots` et `family_dashboard`. | Risque de divergence progressive des KPI famille. | `services/family_snapshots.py`, `services/family_dashboard.py`, `services/prevision_base.py` | Fixer un module autoritaire pour la serie de base et un module derive pour KPI. | P1 |
| S-06 | moyenne | Projections base legacy vs prevision base avancee calculent avec conventions differentes. | Resultats differents selon ecran pour un meme scope. | `services/projections.py`, `services/prevision_base.py` | Harmoniser les conventions via facade unique et contrat commun de base patrimoniale. | P1 |
| S-07 | moyenne | Duplication du calcul cash bourse entre modules. | Corrections a reproduire, risque d'ecarts subtils. | `services/bourse_analytics.py`, `services/liquidites.py`, `services/snapshots.py` | Factoriser le calcul cash bourse as-of dans une fonction partagee unique. | P2 |

---

## 3) Fiabilite fonctionnelle

| ID | Gravite | Description | Impact | Fichier(s) concernes | Recommandation concrete | Priorite d'action |
|---|---|---|---|---|---|---|
| F-01 | critique | Echecs tests metier confirms sur epargne/vue ensemble (83 pass, 2 fail). | Regressions fonctionnelles reelles deja detectees. | `tests/test_vue_ensemble_metrics.py`, `services/cashflow.py`, `services/vue_ensemble_metrics.py` | Bloquer les nouvelles evolutions sur ce domaine tant que les 2 tests ne sont pas resolves. | P0 |
| F-02 | elevee | Dans `compute_positions_valued_asof`, `convert_weekly` peut retourner `None` puis `round(None, 2)`. | Crash possible selon disponibilite FX historique. | `services/bourse_analytics.py` | Garde explicite: skip/flag position si conversion impossible. | P1 |
| F-03 | elevee | Usage massif de `except Exception` avec fallback permissif. | Erreurs masquees, donnees incorrectes sans alerte utilisateur claire. | `services/*` et `qt_ui/*` (nombreux points) | Restreindre aux exceptions attendues + tracer codes erreur metier. | P1 |
| F-04 | moyenne | Parsing date ambigu dans imports (`dayfirst=True`) avec warning pytest. | Mauvaise interpretation de dates selon source de CSV. | `services/imports.py` | Detecter format source et parser avec format explicite par type d'import. | P1 |
| F-05 | moyenne | Retours "vides" (DataFrame vide/None) parfois confondus avec "0 metier". | UX trompeuse et diagnostics complexes. | `services/cashflow.py`, `services/vue_ensemble_metrics.py`, `qt_ui/panels/*` | Introduire un statut qualite des donnees (ok/incomplet/indisponible) en sortie service. | P2 |
| F-06 | faible | Risque de comportements differents selon contexte reseau/API externe (yfinance/FX). | Instabilite intermitente difficile a reproduire. | `services/pricing.py`, `services/fx.py`, `services/market_history.py`, `services/isin_resolver.py` | Ajouter timeout/retry normalises + cache et etiquettes de fraicheur. | P2 |

---

## 4) Base de donnees / acces donnees

| ID | Gravite | Description | Impact | Fichier(s) concernes | Recommandation concrete | Priorite d'action |
|---|---|---|---|---|---|---|
| D-01 | elevee | Couche d'abstraction DB non uniforme (repository + SQL inline dans UI/services). | Contrats de donnees heterogenes, cout de maintenance accru. | `services/repositories.py`, `qt_ui/*`, `services/*` | Definir "read services" pour UI et interdire nouveau SQL direct cote presentation. | P1 |
| D-02 | moyenne | SQL dynamique par f-string present (meme si partiellement controle). | Fragilite future si validation amont oubliee. | `services/imports.py`, `services/db.py`, `services/snapshots.py`, `qt_ui/panels/compte_bourse_panel.py` | Encapsuler dans helpers parametrises, valider strictement les identifiants interpolés. | P2 |
| D-03 | elevee | Requetes volumineuses avec `limit=200000/300000` repetees. | Charge memoire/CPU importante, latence et freeze possibles. | `services/snapshots.py`, `services/liquidites.py` | Passer a des agregations SQL as-of et pagination/streaming quand possible. | P1 |
| D-04 | moyenne | Commit/sync frequents en mode libsql replica via wrapper. | Cout de sync potentiellement eleve lors d'operations batch. | `services/db.py` | Introduire mode transactionnel batch (commit groupé + sync explicite en fin). | P2 |
| D-05 | moyenne | Warnings techniques pytest dus a dossiers `pytest-cache-files-*` non geres. | CI locale fragile, bruit d'audit et d'execution tests. | racine projet (`pytest-cache-files-*`) | Ajouter `pytest.ini` (`norecursedirs`) + nettoyage/ignore de ces dossiers. | P1 |

---

## 5) Performance

| ID | Gravite | Description | Impact | Fichier(s) concernes | Recommandation concrete | Priorite d'action |
|---|---|---|---|---|---|---|
| P-01 | elevee | Rebuild snapshots auto au demarrage pour toutes les personnes. | Temps de demarrage long, charge CPU/IO initiale. | `qt_ui/main_window.py`, `services/snapshots.py` | Rendre configurable/opt-in et incremental par defaut. | P1 |
| P-02 | elevee | Refresh prix bourse fait des appels reseau et requetes unitaire par actif. | N+1 reseau/DB, latence forte sur gros portefeuilles. | `qt_ui/panels/bourse_global_panel.py`, `qt_ui/panels/compte_bourse_panel.py`, `services/pricing.py` | Batcher les fetchs, cache TTL, et limiter les updates aux actifs stale. | P1 |
| P-03 | moyenne | Recherche globale avec sous-requetes correlees lourdes a chaque debounce. | Reponse degradee sur base volumineuse. | `qt_ui/main_window.py` | Materialiser une vue/index de recherche ou service de recherche dedie avec requetes optimisees. | P2 |
| P-04 | elevee | Snapshots recalculent avec nombreuses boucles + requetes repetitives. | Cout de recalcul eleve, risque d'effet tunnel. | `services/snapshots.py` | Prefetch massif (transactions/accounts/assets), vectoriser et memoizer conversions. | P1 |
| P-05 | moyenne | Filtrage texte des tables UI via `df.apply(axis=1)` sur chaque frappe. | Cout O(n*m), ralentissements sensibles sur gros tableaux. | `qt_ui/widgets/data_table.py` | Precalculer colonnes concatenees lowercase ou index de recherche en memoire. | P2 |
| P-06 | faible | Multiples `iterrows()` et transformations DataFrame cote UI. | Surcout modere mais diffuse, impact cumulatif. | `qt_ui/pages/*`, `qt_ui/panels/*` | Deplacer les aggregations lourdes dans services et envoyer DTO preformes. | P3 |

---

## 6) Lisibilite / maintenabilite

| ID | Gravite | Description | Impact | Fichier(s) concernes | Recommandation concrete | Priorite d'action |
|---|---|---|---|---|---|---|
| M-01 | elevee | Fichiers tres longs et peu modulaires. | Changement local = risque global plus eleve. | `qt_ui/pages/goals_projection_page.py`, `qt_ui/pages/import_page.py`, `services/snapshots.py`, `qt_ui/panels/bourse_global_panel.py`, `qt_ui/panels/prevision_avancee_panel.py` | Decoupage progressif par use-cases + tests avant/apres. | P1 |
| M-02 | moyenne | Nommage/doublons documentaires (`SOURCE(S)_DE_VERITE`, README case). | Confusion de reference, onboarding plus lent. | racine projet | Garder une seule convention de nommage et supprimer les doublons. | P2 |
| M-03 | moyenne | Helpers similaires repetes (`_row_get`, safe float, formatters). | Dette de duplication et comportement non homogène. | `services/projections.py`, `services/db.py`, `services/bourse_analytics.py`, `qt_ui/main_window.py`, etc. | Introduire utilitaires partages (module `services/common_*`). | P2 |
| M-04 | moyenne | Catch-all exceptions nombreuses et heterogenes de logging. | Debugging long, traçabilite metier faible. | large partie `services/*`, `qt_ui/*` | Standardiser gestion erreurs (types, logs, messages utilisateur). | P1 |
| M-05 | faible | Presence de legacy non desktop dans repo actif (`pages/3_Import.py`). | Brouille la comprehension de l'architecture active. | `pages/3_Import.py` | Deplacer en archive/legacy avec README explicite ou supprimer. | P3 |

---

## 7) Tests / validation

| ID | Gravite | Description | Impact | Fichier(s) concernes | Recommandation concrete | Priorite d'action |
|---|---|---|---|---|---|---|
| T-01 | critique | Domaine epargne/vue ensemble en regression (2 tests rouges). | KPI business potentiellement faux en production. | `tests/test_vue_ensemble_metrics.py`, `services/cashflow.py`, `services/vue_ensemble_metrics.py` | Corriger puis verrouiller par tests parametrés sur trous calendaires. | P0 |
| T-02 | elevee | Pas de tests dedies pour `bourse_analytics`/`liquidites`/`fx` (zones critiques). | Bugs de valorisation/FX peuvent passer sans detection. | `services/bourse_analytics.py`, `services/liquidites.py`, `services/fx.py`, `services/market_history.py` | Ajouter tests unitaires sur conversions manquantes, perf, cash bourse. | P1 |
| T-03 | elevee | Peu/pas de tests integration UI-flux critiques (import, recherche, projection ecran). | Regressions UX fonctionnelles detectees tardivement. | `qt_ui/main_window.py`, `qt_ui/pages/import_page.py`, `qt_ui/pages/goals_projection_page.py` | Ajouter tests integration headless (PyQt + DB temporaire). | P1 |
| T-04 | moyenne | Pas de tests de coherence inter-moteurs projection (legacy vs prevision). | Incoherence de resultats selon chemin UI. | `services/projections.py`, `services/prevision.py` | Tests de comparaison sur datasets de reference. | P1 |
| T-05 | moyenne | Parametres settings non verifies par tests (delay rebuild, backup count). | Options utilisateur possiblement non appliquees sans alerte. | `qt_ui/pages/settings_page.py`, `qt_ui/main_window.py`, `main.py` | Tests d'integration des preferences runtime. | P2 |
| T-06 | moyenne | Collecte pytest racine casse sans config d'exclusion de dossiers parasites. | Pipeline locale fragile et signal qualite degrade. | racine projet | Ajouter `pytest.ini` + hygiene des dossiers temporaires. | P1 |

---

## 8) UX / produit

| ID | Gravite | Description | Impact | Fichier(s) concernes | Recommandation concrete | Priorite d'action |
|---|---|---|---|---|---|---|
| U-01 | elevee | Deux experiences projections (Objectifs/Projection vs Prevision avancee) non unifiees. | Utilisateur peut comparer des chiffres issus de modeles differents sans le savoir. | `qt_ui/pages/goals_projection_page.py`, `qt_ui/panels/prevision_avancee_panel.py` | Afficher clairement le moteur utilise + converger vers une experience unique. | P1 |
| U-02 | elevee | Capacite epargne/moyennes peuvent etre mal interpretees si mois manquants non explicites. | Mauvaise lecture de la situation financiere reelle. | `services/cashflow.py`, `services/vue_ensemble_metrics.py`, `qt_ui/panels/vue_ensemble_panel.py`, `qt_ui/panels/taux_epargne_panel.py` | Afficher couverture de donnees (nb mois reels / nb mois attendus). | P0 |
| U-03 | moyenne | Comportement FX heterogene (0, None, montant brut) peu explicite pour l'utilisateur. | Confiance degradee dans les valorisations. | `services/liquidites.py`, `services/market_history.py`, `qt_ui/panels/vue_ensemble_panel.py` | Ajouter badge "donnee incomplete" + details FX manquants par ecran. | P1 |
| U-04 | moyenne | Rebuild auto au lancement peut surprendre (charge, attente). | Impression de lenteur/inertie au demarrage. | `qt_ui/main_window.py` | Option utilisateur explicite + mode manuel/planifie. | P2 |
| U-05 | moyenne | Gestion d'erreurs non uniforme dans les pages/panels (warnings logs vs labels). | Diagnostique utilisateur inconsistent. | `qt_ui/pages/*`, `qt_ui/panels/*` | Normaliser une couche "UI error state" (warning/error/info). | P2 |
| U-06 | faible | Recherche globale enrichie par dernier contexte transactionnel peut paraitre instable. | Navigation potentiellement deroutante sur actifs multiscope. | `qt_ui/main_window.py` | Afficher provenance/horodatage du contexte et fallback neutre si ambigu. | P3 |

---

## Top 10 des problemes a traiter en priorite
1. [P0] Regression epargne/vue ensemble (2 tests rouges).
2. [P0] Convention de serie mensuelle epargne (mois manquants non geres).
3. [P0] Conflit de source de verite projection (dual stack actif).
4. [P0] Politique FX incoherente (`_fx_to_eur` montant brut si taux absent).
5. [P1] SQL direct en UI sur ecrans critiques.
6. [P1] Risque crash `round(None)` dans valorisation bourse hebdo.
7. [P1] Snapshots trop couteux (requetes massives et loops).
8. [P1] Absence de tests sur modules critiques valorisation/FX/bourse.
9. [P1] Fichiers monolithiques ralentissant toute evolution.
10. [P1] Pipeline pytest fragile a cause de dossiers parasites et warnings cache.

## Top 10 des ameliorations a fort impact
1. Ajouter une facade unique de projection et migrer progressivement les ecrans.
2. Reindexer la serie epargne sur calendrier mensuel et recalibrer KPI associes.
3. Unifier les conversions FX (meme contrat de retour et meme fallback).
4. Extraire les acces SQL UI vers services de lecture dedies.
5. Introduire un statut de qualite des donnees (OK/incomplet/manquant) dans les payloads metier.
6. Optimiser snapshots via prefetch SQL + reduction des `limit` massifs.
7. Optimiser recherche globale (vue/index + requetes simplifiees).
8. Remplacer les filtres DataFrame `apply(axis=1)` par une strategie de recherche preindexee.
9. Ajouter tests unitaires pour bourse/liquidites/fx + tests integration UI headless.
10. Standardiser la gestion d'erreurs (exceptions attendues, codes, message utilisateur).

## Top 10 des simplifications architecturales possibles
1. Introduire `services/projection_service.py` comme point d'entree unique.
2. Extraire un module commun de conversion FX (historique + live sous contrat unique).
3. Creer `services/search_service.py` pour la recherche globale.
4. Creer `services/import_lookup_service.py` pour retirer le SQL de `import_page`.
5. Decomposer `services/snapshots.py` en sous-modules (cash banque, cash bourse, holdings, orchestration rebuild).
6. Decomposer `qt_ui/pages/goals_projection_page.py` en sections UI + presenter + actions.
7. Isoler la preparation d'affichage de `vue_ensemble_metrics` dans un presenter dedie.
8. Centraliser les helpers communs (`row_get`, safe float, date parsing, normalisation).
9. Aligner le naming documentaire (un seul `README`, une seule "source de verite").
10. Archiver explicitement les artefacts legacy (Streamlit/specs obsoletes) hors chemin principal.

---

## Points d'incertitude (explicitement assumes)
- Aucune analyse statique complete des dependances circulaires Python n'a ete executee; l'audit releve surtout les couplages visibles dans le code lu.
- L'audit UX repose sur la lecture code + flux, pas sur une campagne de tests utilisateurs.
- Les mesures de performance sont qualitatives (analyse de complexite/structure), pas un profilage chronometre complet.
