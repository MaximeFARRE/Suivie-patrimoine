# Backlog Global

Mise à jour: 2026-04-11

## P0 (immédiat)

### P0-1 Corriger les 2 tests en échec ou ajuster le contrat
- Scope: `services/cashflow.py`, `services/vue_ensemble_metrics.py`, `tests/test_vue_ensemble_metrics.py`.
- Critère d'acceptation:
  - `python -m pytest -q` => 100% vert.
  - contrat métier épargne documenté dans `SOURCE_DE_VERITE.md`.
- Effort estimé: S.

### P0-2 Unifier la documentation racine et supprimer les ambiguïtés de nommage
- Scope: docs racine.
- Critère d'acceptation:
  - un seul document source de vérité nommé et référencé partout.
  - plus de liens docs cassés.
- Effort: S.

### P0-3 Fiabiliser le pipeline local de tests
- Scope: outillage dev.
- Actions:
  - ajouter `pytest` dans dépendances dev (ou procédure explicite d'installation).
  - documenter commande canonique d'exécution tests.
- Effort: S.

## P1 (prochaine itération)

### P1-1 Extraire un service `global_search_service`
- Scope: retirer SQL métier de `qt_ui/main_window.py`.
- Critère d'acceptation:
  - aucun SQL de recherche dans la fenêtre principale,
  - tests unitaires du service de recherche.
- Effort: M.

### P1-2 Réduire SQL direct dans `import_page.py`
- Scope: créer services de lookup (`people/accounts`) et les consommer.
- Critère d'acceptation:
  - réduction nette des `.execute()` UI,
  - comportement inchangé.
- Effort: M.

### P1-3 Brancher réellement les préférences runtime
- Scope: `rebuild_delay_ms`, `backup_max_count`.
- Critère d'acceptation:
  - valeurs lues et appliquées dans `MainWindow`/`main.py`.
- Effort: S.

### P1-4 Isoler le legacy Streamlit
- Scope: `pages/3_Import.py`.
- Critère d'acceptation:
  - soit suppression,
  - soit déplacement dans dossier `legacy/` non ambigu + note claire.
- Effort: S.

## P2 (assainissement structurel)

### P2-1 Découper `services/snapshots.py`
- Scope: extraction en modules (`snapshot_compute`, `snapshot_rebuild`, `snapshot_watermark`).
- Critère d'acceptation:
  - API publique inchangée,
  - complexité par fichier réduite,
  - tests existants conservés + nouveaux tests ciblés.
- Effort: L.

### P2-2 Découper `qt_ui/pages/goals_projection_page.py` et `import_page.py`
- Scope: séparer orchestration UI / dialogs / renderers.
- Critère d'acceptation:
  - fichiers < 800 lignes,
  - code plus localisé par sous-fonctionnalité.
- Effort: L.

### P2-3 Standardiser les helpers techniques partagés
- Scope: `_safe_float`, `_row_get`, conversions date/montant.
- Critère d'acceptation:
  - module utilitaire central,
  - suppression des duplications évidentes.
- Effort: M.

### P2-4 Renforcer tests d'intégration UI-service
- Scope: scénarios clés (import, recherche globale, navigation personne/compte).
- Critère d'acceptation:
  - tests d'intégration minimaux automatisés,
  - couverture des flux à risque.
- Effort: M/L.

## Ordre recommandé
1. P0-1
2. P0-3
3. P1-1
4. P1-2
5. P1-3
6. P2-* (par tranche)
