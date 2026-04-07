# plan_prevision.md
# Plan de développement — Module de prévision patrimoniale

> Ce document est volontairement séparé du fichier `prevision.md`.
> Il sert de **plan d’exécution concret**.
> Le fichier `prevision.md` reste la vision complète.
> Ce fichier-ci sert à piloter le développement réel, étape par étape.
>
> Principe important :
> - on **ne remplace pas** le fichier/projet de projection existant
> - on construit un **deuxième chantier distinct**, propre et modulaire
> - on garde une architecture compatible avec la refonte récente de l’application

---

# 1. Objectif du chantier

Créer un **nouveau moteur de prévision patrimoniale avancée** qui coexiste avec l’existant, sans casser le module de projection actuel.

Ce nouveau chantier doit permettre à terme :

- des projections plus réalistes
- des simulations probabilistes
- une vraie mesure du risque patrimonial
- des comparaisons de scénarios
- une meilleure vitrine technique pour les entretiens finance

---

# 2. Contrainte principale

Le système actuel de projection existe déjà et doit rester intact.

Donc :

- on **ne modifie pas brutalement** le flux existant
- on crée un **nouveau sous-domaine**
- on isole clairement ce qui est :
  - projection actuelle
  - prévision avancée nouvelle génération

---

# 3. Nommage recommandé

Pour éviter toute confusion avec l’existant :

## Option recommandée
Créer un nouveau bloc autour du mot **prevision**.

Exemples de fichiers possibles :

- `services/prevision.py`
- `services/prevision_base.py`
- `services/prevision_models.py`
- `services/prevision_risk.py`
- `services/prevision_explain.py`
- `services/prevision_presets_repository.py`

Et éventuellement un dossier :

- `services/prevision_engines/`

avec :
- `deterministic_engine.py`
- `monte_carlo_engine.py`
- `stress_engine.py`
- `regime_engine.py`

Cette option est la plus propre car elle évite de mélanger :
- le système historique `projections`
- le nouveau système `prevision`

---

# 4. Positionnement dans l’architecture

Architecture à respecter strictement :

```text
UI -> Services -> Repository / DB
```

Donc :

## UI
Responsabilités :
- affichage
- interactions utilisateur
- chargement des presets
- lancement d’un calcul
- rendu des résultats

Interdits :
- recalcul métier
- Monte Carlo côté UI
- groupby métier lourd
- calcul de KPI de risque

## Services
Responsabilités :
- construire la base de prévision
- simuler les trajectoires
- calculer les métriques
- produire les payloads finaux

## Repository / DB
Responsabilités :
- persistance des presets
- persistance éventuelle des scénarios sauvegardés
- éventuellement cache de résultats si un jour nécessaire

---

# 5. Stratégie de coexistence avec l’existant

## Phase 1
Le module actuel continue d’alimenter la page de projection existante.

## Phase 2
Le nouveau système “prévision” est développé à part, sans brancher l’UI principale immédiatement.

## Phase 3
On ajoute soit :
- un nouvel onglet dans `GoalsProjectionPage`
ou
- une nouvelle sous-section “Prévision avancée”

## Phase 4
Une fois le moteur validé, on décide :
- soit de garder les deux systèmes
- soit de faire migrer progressivement l’existant vers le nouveau

Important :
- pas de gros remplacement d’un coup
- pas de régression sur la projection actuelle

---

# 6. Livrables fonctionnels visés

Le nouveau module doit produire à terme :

## Livrable A — Projection simple avancée
- base patrimoniale consolidée
- hypothèses lisibles
- trajectoire déterministe
- patrimoine final
- revenu passif projeté

## Livrable B — Simulation probabiliste
- Monte Carlo
- percentiles
- fan chart
- histogramme de patrimoine final
- probabilité d’atteinte d’objectif

## Livrable C — Analyse du risque
- volatilité
- max drawdown
- VaR
- CVaR
- Sharpe
- Sortino
- score de robustesse

## Livrable D — Comparaison de scénarios
- scénario A / B / C
- comparaison des distributions
- comparaison des risques
- comparaison des probabilités d’atteinte

## Livrable E — Stress tests
- krach marché
- inflation forte
- choc de revenus
- crise immobilière
- vacance / travaux / taux

---

# 7. Roadmap globale

# V1 — Base crédible, propre, montrable
Objectif :
- avoir rapidement quelque chose de sérieux
- architecture propre
- résultats visuels utiles

À implémenter :
- base de prévision consolidée
- modèle de données
- moteur déterministe
- Monte Carlo corrélé simple
- distribution finale
- premiers KPI de risque
- objectifs simples

# V2 — Version finance sérieuse
Objectif :
- ajouter profondeur analytique

À implémenter :
- moteur de risque enrichi
- stress tests
- comparaison de scénarios
- moteur immobilier plus fin
- meilleure gestion des flux

# V3 — Version premium
Objectif :
- aller vers une logique family office

À implémenter :
- régimes de marché
- corrélations dynamiques
- distributions non normales
- private equity réaliste
- fiscalité détaillée
- optimisation multi-objectifs

---

# 8. Plan technique détaillé

# Étape 1 — Cadrage et isolation du domaine
## But
Créer un domaine `prevision` séparé et propre.

## Tâches
- créer l’arborescence du nouveau module
- définir les responsabilités de chaque fichier
- documenter les points d’entrée publics
- documenter la séparation avec `services.projections`

## Résultat attendu
On sait exactement :
- où coder
- où ne pas coder
- quels fichiers appartiennent au nouveau moteur

---

# Étape 2 — Construire la base de prévision
## But
Créer une source unique de vérité pour l’état patrimonial de départ du moteur.

## Nouveau point d’entrée possible
- `services.prevision.get_prevision_base_for_scope(conn, scope_type, scope_id)`

## Cette base doit agréger
- patrimoine net actuel
- liquidités
- positions bourse
- immobilier
- private equity
- entreprises
- crédits
- revenus
- dépenses
- capacité d’épargne
- coussin de liquidité

## Questions à trancher
- fréquence mensuelle ou annuelle ?
- quels actifs inclure dès la V1 ?
- quel niveau de granularité pour l’immobilier ?
- quel niveau de détail pour le non coté ?

## Résultat attendu
Un payload stable, testable, lisible.

---

# Étape 3 — Définir les modèles métiers
## But
Créer des dataclasses propres et stables.

## Fichiers possibles
- `services/prevision_models.py`

## Objets à créer
- `PrevisionConfig`
- `PrevisionBase`
- `PrevisionScenario`
- `PrevisionResult`
- `RiskMetrics`
- `GoalMetrics`
- `ScenarioComparison`

## Résultat attendu
Tous les moteurs travaillent avec des objets clairs, pas avec des dictionnaires flous partout.

---

# Étape 4 — Implémenter le moteur déterministe
## But
Avoir une première brique simple, pédagogique, testable.

## Fichier possible
- `services/prevision_engines/deterministic_engine.py`

## Fonctions possibles
- `run_deterministic_projection(base, config)`

## Comportement attendu
- applique les hypothèses fixes
- projette la croissance des grandes classes d’actifs
- ajoute contributions / flux
- renvoie une série temporelle propre

## KPI minimum
- patrimoine final
- revenu passif final
- taux de croissance annualisé projeté
- trajectoire annuelle ou mensuelle

## Résultat attendu
Une base exploitable rapidement dans l’UI.

---

# Étape 5 — Implémenter le moteur Monte Carlo V1
## But
Passer d’une projection unique à une distribution de scénarios.

## Fichier possible
- `services/prevision_engines/monte_carlo_engine.py`

## Fonctions possibles
- `run_monte_carlo_projection(base, config)`

## Fonctionnalités minimales
- N simulations
- rendements aléatoires
- volatilités par bucket
- matrice de corrélation
- contributions régulières
- extraction des percentiles

## Sorties attendues
- série médiane
- série percentile 10
- série percentile 90
- distribution finale
- échantillon de trajectoires

## Résultat attendu
Le cœur différenciant du nouveau module.

---

# Étape 6 — Calculer les métriques de risque
## But
Ajouter la vraie lecture “finance / risk”.

## Fichier possible
- `services/prevision_risk.py`

## Métriques minimum V1/V2
- volatilité annualisée
- max drawdown
- downside volatility
- VaR 95 %
- CVaR 95 %
- Sharpe simplifié
- Sortino simplifié

## Résultat attendu
Un payload `risk_metrics` propre, consommable par l’UI.

---

# Étape 7 — Gérer les objectifs
## But
Pouvoir répondre à :
- probabilité d’atteindre 1 M€
- probabilité de couvrir les dépenses
- horizon d’autonomie financière

## Fichier possible
- `services/prevision_goals.py`

## Fonctions possibles
- `compute_goal_metrics(result, config)`
- `compute_goal_attainment_probability(...)`

## Résultat attendu
Le moteur devient utile pour décider, pas seulement pour “regarder une courbe”.

---

# Étape 8 — Générer diagnostics et explications
## But
Rendre les résultats intelligibles.

## Fichier possible
- `services/prevision_explain.py`

## Exemples de diagnostics
- patrimoine très concentré
- dépendance forte au revenu actif
- bonne réserve de liquidité
- drawdown potentiellement élevé
- forte probabilité d’atteindre l’objectif sous hypothèses centrales

## Résultat attendu
Une sortie lisible, forte en entretien, utile produit.

---

# Étape 9 — Créer l’intégration UI minimale
## But
Brancher le nouveau moteur sans casser l’existant.

## Option recommandée
Dans `qt_ui/pages/goals_projection_page.py`, ajouter une nouvelle zone ou un nouvel onglet :
- “Projection actuelle”
- “Prévision avancée”

## La nouvelle UI doit permettre
- de charger la base
- d’éditer les hypothèses
- de lancer le calcul
- d’afficher :
  - trajectoire
  - distribution
  - objectifs
  - risque
  - diagnostics

## Important
Aucune logique métier lourde dans la page.

---

# Étape 10 — Ajouter les presets utilisateur
## But
Sauvegarder plusieurs scénarios.

## Exemples
- prudent
- central
- agressif
- achat RP
- retraite anticipée
- entrepreneur

## Fichier possible
- `services/prevision_presets_repository.py`

## Résultat attendu
Comparaison rapide et UX plus riche.

---

# 9. Proposition d’arborescence concrète

```text
services/
├── projections.py                  # existant, conservé
├── prevision.py                   # nouvelle façade publique
├── prevision_base.py
├── prevision_models.py
├── prevision_risk.py
├── prevision_goals.py
├── prevision_explain.py
├── prevision_presets_repository.py
└── prevision_engines/
    ├── __init__.py
    ├── deterministic_engine.py
    ├── monte_carlo_engine.py
    ├── stress_engine.py
    └── regime_engine.py
```

Option UI possible :

```text
qt_ui/
├── pages/
│   └── goals_projection_page.py
└── panels/
    ├── prevision_assumptions_panel.py
    ├── prevision_summary_panel.py
    ├── prevision_distribution_panel.py
    ├── prevision_risk_panel.py
    ├── prevision_goals_panel.py
    └── prevision_stress_panel.py
```

---

# 10. Plan V1 ultra concret

## Backend
- créer `prevision_models.py`
- créer `prevision_base.py`
- créer `prevision.py`
- créer `deterministic_engine.py`
- créer `monte_carlo_engine.py`
- créer `prevision_risk.py`
- créer `prevision_goals.py`

## UI
- ajouter un espace “Prévision avancée”
- formulaire simple :
  - horizon
  - contribution mensuelle
  - rendement moyen par bucket
  - volatilité par bucket
  - nombre de simulations
- graphiques :
  - trajectoire médiane + percentiles
  - histogramme final
- cartes KPI :
  - médiane finale
  - percentile 10
  - percentile 90
  - probabilité d’atteinte objectif
  - drawdown simulé moyen / max

## Tests
- tests modèles
- tests moteur déterministe
- tests Monte Carlo seedée
- tests KPI de risque
- tests intégration façade publique

---

# 11. Plan V2 ultra concret

## Backend
- enrichir moteur immobilier
- enrichir logique revenus / dépenses
- ajouter `stress_engine.py`
- ajouter `run_prevision_comparison(...)`
- ajouter scores maison :
  - robustesse
  - concentration
  - résilience cashflow

## UI
- comparateur de scénarios
- stress tests
- vue risque plus riche
- vue diagnostics / explications

## Tests
- stress tests reproductibles
- scénarios comparatifs
- cohérence comparaisons

---

# 12. Plan V3 ultra concret

## Backend
- `regime_engine.py`
- régimes de marché
- matrices de transition
- corrélations dynamiques
- distributions non normales
- fiscalité détaillée
- logique PE / non coté avancée
- optimisation multi-objectifs

## UI
- choix du moteur
- scénarios premium
- vue sensibilité
- recommandations

---

# 13. Ce qu’il faut décider avant de coder

## Décision 1
Granularité V1 :
- par grands buckets
ou
- par actif réel ?

Recommandation :
- V1 par buckets
- V2/V3 raffinement progressif

## Décision 2
Fréquence :
- annuelle
ou
- mensuelle ?

Recommandation :
- moteur mensuel si faisable
- sinon annuel V1 puis mensuel V2

## Décision 3
Intégration UI :
- nouvel onglet
ou
- nouvelle page interne dans `GoalsProjectionPage` ?

Recommandation :
- onglet / sous-section dans la page existante

## Décision 4
Persistance des presets :
- DB dédiée maintenant
ou
- plus tard ?

Recommandation :
- V1 possible sans persistance
- V2 avec repository dédié

---

# 14. Critères de réussite

Le chantier est réussi si :

- le module existant de projection n’est pas cassé
- le nouveau domaine est clairement séparé
- les calculs restent dans `services`
- l’UI ne recalcule pas de logique métier
- la base de prévision a une vraie SSOT
- les résultats sont lisibles
- la V1 est déjà montrable en entretien
- la V2 apporte une vraie lecture du risque
- la V3 ouvre vers un niveau family office

---

# 15. Résumé final

Ce chantier ne doit pas être pensé comme :
- une simple amélioration cosmétique de la projection existante

Il doit être pensé comme :
- un **nouveau sous-système patrimonial**
- proprement isolé
- compatible avec le refactor récent
- capable d’évoluer sans casser l’existant

La bonne stratégie est donc :

1. garder `projections` tel quel
2. créer un nouveau domaine `prevision`
3. sortir une V1 crédible rapidement
4. enrichir progressivement jusqu’à un moteur premium

---

# 16. Première action concrète recommandée

La première vraie action de code à lancer est :

> créer le squelette du domaine `services/prevision*` avec les dataclasses, la façade publique et un moteur déterministe minimal

Pourquoi :
- c’est propre
- c’est compatible avec ton refactor
- ça ne casse rien
- ça pose la fondation correcte pour toute la suite
