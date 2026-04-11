# Source de Verite

Mise a jour: 2026-04-11

## Objectif
Ce document definit ou vit chaque verite metier dans l'application, sur la base du code reel actuel.
Il sert de reference pour eviter les calculs divergents entre modules.

## 1) Quelle couche possede la verite metier ?
Regle cible et majoritairement respectee:

```text
UI -> services -> repository/DB
```

Autorite par couche:
- `services/*`: verite metier (calculs, agregations, conventions de fallback, normalisation).
- `repositories.py` et SQL sous `services/*`: verite de persistance (lecture/ecriture brute).
- `qt_ui/*`: orchestration d'ecrans, declenchement d'actions, mise en forme d'affichage uniquement.

Constat reel: il reste des bypass UI -> SQL (sections "violations" plus bas).

## 2) Ou doivent vivre les calculs financiers ?
Calculs financiers (rendements, perf, CAGR, valorisation, conversion devises, risques) doivent vivre dans `services/*`:
- Bourse live/perf: `services/bourse_analytics.py`
- Valorisation/FX spot: `services/fx.py`, `services/portfolio.py`
- Valorisation hebdo historique: `services/market_history.py`, `services/snapshots.py`
- Projections/previsions: `services/projections.py` (V1 legacy), `services/prevision.py` + `services/prevision_engines/*` (nouveau)

Interdit cote UI: recalculer ces formules avec ses propres conventions.

## 3) Ou doivent vivre les calculs d'agregation (portefeuille/patrimoine/cashflow/projections) ?
- Portefeuille/patrimoine historique: `services/snapshots.py`, `services/family_snapshots.py`
- Vue consolidee personne: `services/vue_ensemble_metrics.py`
- Cashflow/epargne: `services/cashflow.py`
- Agregation famille de dashboard: `services/family_dashboard.py` (derive de snapshots famille)
- Projections patrimoniales:
  - Legacy: `services/projections.py`
  - Nouveau domaine: `services/prevision.py`, `services/prevision_base.py`, `services/prevision_engines/*`

## 4) Ce que l'UI a le droit de faire / n'a pas le droit de faire
UI autorisee:
- Lire des payloads deja calcules par services.
- Declencher des actions services (import, recalcul, projection, refresh prix).
- Transformer legerement la presentation (labels, tri visuel, couleurs, colonnes).

UI interdite:
- Refaire des calculs metier (perf, allocation, epargne, projection).
- Convertir des devises avec logique propre.
- Interroger directement la DB pour de la logique metier durable.

Etat reel actuel: interdits non totalement respectes (SQL direct et refresh metier en UI).

## 5) Ce que les panels peuvent preparer
Panels/UI peuvent preparer:
- Ordre d'affichage.
- Selections utilisateurs (filtres, periode, compte, scenario).
- Formattage final (arrondis d'affichage, libelles, tooltips).

Doit rester dans services:
- Toute formule financiere.
- Toute regle d'agregation multi-comptes/multi-personnes.
- Toute convention metier de fallback (prix manquant, FX manquant, historique incomplet).

## 6) Source de verite par domaine

| Domaine | Source canonique actuelle | Observations et conflits |
|---|---|---|
| Positions bourse live | `services/bourse_analytics.py` (`get_live_bourse_positions`, `get_live_bourse_positions_for_account`) | Correctement consomme par panels bourse. |
| Historique portefeuille | `services/snapshots.py` (`get_person_weekly_series`) et `services/family_snapshots.py` (`get_family_weekly_series`) | Verite snapshots claire; derivees supplementaires dans `family_dashboard.py`. |
| Cashflow | `services/cashflow.py` (`get_cashflow_for_scope`) | Source stable et reutilisee dans projections/prevision. |
| Metriques epargne | `services/cashflow.py` (`compute_savings_metrics`, `get_person_monthly_savings_series`) | Ancien wrapper encore present dans `services/revenus_repository.py` (deprecated). |
| Projections (legacy) | `services/projections.py` (`get_projection_base_for_scope`, `run_projection`) | Coexiste avec nouveau domaine prevision: conflit de verite. |
| Stress tests | `services/prevision.py` + `services/prevision_engines/stress_engine.py` | Plus coherent que legacy, mais base amont encore hybride person/family. |
| Monte Carlo | `services/prevision.py` + `services/prevision_engines/monte_carlo_engine.py` | Source claire cote prevision avancee. |
| Valorisation des actifs | Historique hebdo: `services/market_history.py::convert_weekly`; live/spot: `services/fx.py::convert` | Regles FX non totalement unifiees (`liquidites.py` a sa propre conversion). |
| Aggregations personne/foyer/compte | Personne: `services/vue_ensemble_metrics.py`; Famille: `services/family_snapshots.py` + `services/family_dashboard.py`; Compte bourse: `services/bourse_analytics.py` | Frontieres pas totalement nettes entre `family_snapshots` et `family_dashboard`; duplication partielle de roles. |

## 7) Modules qui enfreignent aujourd'hui la regle
Violations observees dans le code:
- Projection dual-stack (verite partagee):
  - `services/projections.py` (V1)
  - `services/prevision.py` + `services/prevision_*` (nouveau)
  - UI consommatrice mixte: `qt_ui/pages/goals_projection_page.py` (V1) vs `qt_ui/panels/prevision_avancee_panel.py` (nouveau)
- FX/valorisation non unifiee:
  - `services/market_history.py::convert_weekly`
  - `services/fx.py::convert` / `ensure_fx_rate`
  - `services/liquidites.py::_fx_to_eur` (implementation locale)
- SQL metier en UI (bypass partiel couche services):
  - `qt_ui/main_window.py`
  - `qt_ui/pages/import_page.py`
  - `qt_ui/panels/compte_bourse_panel.py`
  - `qt_ui/panels/credits_overview_panel.py`
  - `qt_ui/panels/saisie_panel.py`
- Service avec responsabilites mixtes (metier + preparation affichage):
  - `services/vue_ensemble_metrics.py` contient `prepare_*` en plus des calculs metier.

## 8) Plan simple pour recentraliser progressivement la logique
Phase 1 (faible risque, immediate):
- Geler les nouvelles entrees metier: toute nouvelle logique passe par `services/*`.
- Marquer officiellement `services/projections.py` en legacy dans la doc + commentaires d'entree UI.
- Interdire toute nouvelle conversion FX hors `market_history`/`fx`.

Phase 2 (reduction des conflits):
- Introduire une facade unique de projection (ex: `services/projection_service.py`) qui route vers legacy ou prevision, sans expose direct UI aux 2 mondes.
- Extraire `_fx_to_eur` de `services/liquidites.py` vers une API FX commune.
- Extraire les requetes SQL de `qt_ui/*` vers services dedies (lecture seule d'abord).

Phase 3 (convergence):
- Migrer `goals_projection_page.py` vers la facade unique (puis vers prevision).
- Isoler la preparation d'affichage de `vue_ensemble_metrics.py` dans un module presenter/dto.
- Clarifier famille: data SSOT dans `family_snapshots.py`, KPIs derives uniquement en couche analytique dediee.

## Zones floues (incertitudes assumees)
- Frontiere exacte cible entre `family_snapshots.py` et `family_dashboard.py` (des roles se recouvrent aujourd'hui).
- Perimetre fonctionnel final entre projections V1 et prevision avancee (les 2 sont encore actives cote UI).
- Politique unique souhaitee pour FX manquante (fallback strict `None` vs substitution vs rejet).

## Regles strictes
- Une donnee metier critique = une API canonique documentee ici.
- Aucun calcul financier durable dans `qt_ui/*`.
- Aucun acces SQL metier nouveau dans `qt_ui/*`.
- Toute conversion FX doit passer par un service FX/market_history commun (pas de helper local).
- Toute nouvelle projection doit passer par la facade de projection unique.
- Toute exception doit etre tracee dans ce document avec date et plan de retrait.

## Cas toleres temporairement
- Coexistence `services/projections.py` et `services/prevision.py` tant que la migration UI n'est pas complete.
- SQL UI historique dans les ecrans listes ci-dessus tant que les services de remplacement ne sont pas disponibles.
- Fonctions `prepare_*` dans `services/vue_ensemble_metrics.py` en attendant extraction progressive.
- Wrapper deprecated `services/revenus_repository.py::compute_taux_epargne_mensuel` tant que les appels legacy existent.

## Backlog de realignement de la source de verite
1. Creer une facade unique projection et basculer les appels UI vers celle-ci.
2. Migrer `qt_ui/pages/goals_projection_page.py` du moteur V1 vers prevision (ou facade).
3. Centraliser FX: supprimer `_fx_to_eur` local de `services/liquidites.py` au profit d'une API commune.
4. Extraire SQL metier de `qt_ui/main_window.py` vers un service de recherche globale.
5. Extraire SQL metier de `qt_ui/pages/import_page.py` vers des services de selection/import.
6. Extraire SQL metier de `qt_ui/panels/compte_bourse_panel.py` vers `services/bourse_analytics.py`/service dedie.
7. Extraire SQL metier de `qt_ui/panels/credits_overview_panel.py` vers `services/credits.py`.
8. Extraire SQL metier de `qt_ui/panels/saisie_panel.py` vers services assets/transactions.
9. Scinder `services/vue_ensemble_metrics.py` en "calcul metier" et "preparation affichage".
10. Documenter et figer la frontiere `family_snapshots` (SSOT data) vs `family_dashboard` (derive).
