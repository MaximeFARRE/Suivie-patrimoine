# prevision.md
# Vision complète — Moteur de prévision patrimoniale

> Version de travail longue, volontairement ambitieuse.
> Objectif : servir de référence produit + technique pendant le développement de l’onglet **Objectifs & Projections**.
> Philosophie : ne pas “prédire le futur” avec un taux fixe, mais construire un **moteur de projection probabiliste patrimoniale** capable d’explorer des trajectoires plausibles, leurs risques, leurs contraintes de liquidité et l’impact des décisions de vie / d’investissement.

---

# 1. Idée directrice

Le mauvais modèle :

- “Le portefeuille fait 8 % par an”
- “On applique 8 % pendant 30 ans”
- “On obtient un patrimoine final”

Le bon modèle :

- un patrimoine est un **système vivant**
- il contient des actifs hétérogènes
- des passifs
- des flux entrants et sortants
- de la fiscalité
- des contraintes de liquidité
- des événements de vie
- des décisions d’allocation
- des risques de marché et des risques non-marché

Le but du moteur n’est donc pas de répondre :

> “Combien vaudra exactement mon patrimoine dans 20 ans ?”

mais plutôt :

- quelles trajectoires sont plausibles ?
- quelle est la probabilité d’atteindre mes objectifs ?
- quels sont mes vrais risques ?
- quelles décisions améliorent le couple rendement / risque / robustesse ?
- où se trouvent mes fragilités structurelles ?

Autrement dit :

> Le bon mot n’est pas **prédiction exacte**.  
> Le bon mot est **projection probabiliste sous contraintes**.

---

# 2. Ce que doit devenir l’onglet Projection

L’onglet Projection ne doit pas être une simple courbe “patrimoine futur”.

Il doit devenir un **laboratoire patrimonial** capable de faire :

- projection simple et pédagogique
- simulation Monte Carlo
- analyse des risques
- stress tests
- comparaison de scénarios
- aide à la décision patrimoniale

C’est cette profondeur qui peut faire de cette partie une **vraie vitrine technique et financière** pour des entretiens en finance, gestion, allocation d’actifs, family office, wealth management, risk office ou stratégie patrimoniale.

---

# 3. Vision “family office” maximale

Si l’on raisonne comme un gérant de family office avec budget illimité, on ne construit pas un simulateur de rendement moyen.

On construit un **moteur de pilotage patrimonial** avec 8 briques.

## 3.1. Modèle patrimonial complet

Le moteur doit représenter :

### Actifs financiers
- actions cotées
- ETF
- obligations
- monétaire
- private equity
- dette privée
- hedge funds
- produits structurés
- crypto
- assurance-vie
- PEA
- CTO
- PER
- PEE
- comptes titres de holding

### Actifs réels
- résidence principale
- immobilier locatif
- SCPI / OPCI
- foncier
- participations non cotées
- entreprise opérationnelle
- stock-options / BSPCE / management package
- objets de valeur si besoin

### Passifs
- crédits immobiliers amortissables
- crédits in fine
- dette lombard / marge
- dettes liées à la société
- engagements hors bilan simplifiés si un jour nécessaire

### Flux
- salaires
- bonus
- dividendes
- coupons
- loyers nets
- distributions de fonds
- pensions
- dépenses courantes
- dépenses exceptionnelles
- donations
- successions
- vente d’actifs
- achats futurs

---

## 3.2. Modélisation par objets économiques

Le patrimoine ne doit pas être traité comme une masse unique.

Chaque grande brique doit être simulée comme un **objet économique** avec ses propres règles.

Exemples :

### Une ligne d’ETF
- valeur actuelle
- devise
- rendement espéré
- volatilité
- dividende
- corrélation
- enveloppe fiscale
- fréquence de rééquilibrage

### Un bien immobilier
- valeur du bien
- loyer
- charges
- taxe
- vacance locative
- travaux
- crédit associé
- fiscalité
- revalorisation lente

### Une participation non cotée
- valorisation incertaine
- illiquidité
- scénario de sortie
- dilution possible
- croissance de CA / EBITDA si un jour on va jusque-là

### Un prêt
- échéancier
- taux
- mensualité
- CRD
- date de fin
- coût des intérêts

Pourquoi cette approche est indispensable :

- un ETF peut faire -30 % rapidement
- un appartement n’est pas mark-to-market tous les jours
- le private equity a une volatilité “cachée”
- une entreprise peut faire +0 % pendant des années puis être vendue
- un crédit agit comme un levier asymétrique

---

## 3.3. Moteur de scénarios multi-couches

Le moteur complet doit pouvoir supporter plusieurs couches de projection.

### Couche A — déterministe
Hypothèses fixes :
- rendement fixe
- inflation fixe
- croissance de salaire fixe
- hausse de loyer fixe

Utilité :
- très pédagogique
- très lisible
- parfaite pour une V1 simple

### Couche B — Monte Carlo corrélé
- rendements aléatoires
- volatilités par classe d’actifs
- matrice de corrélation
- contributions régulières
- rééquilibrage éventuel

Utilité :
- première vraie brique “finance”
- cœur de la V2 sérieuse

### Couche C — régimes de marché
États du monde :
- expansion
- marché normal
- inflation forte
- récession
- crise de liquidité
- krach actions
- crise immobilière
- remontée prolongée des taux

Chaque régime modifie :
- rendement moyen
- volatilité
- corrélations
- spreads
- pression sur l’immobilier
- coût du crédit
- croissance des revenus

Utilité :
- beaucoup plus réaliste
- très fort intellectuellement
- excellente vitrine en entretien

### Couche D — stress tests
Scénarios historiques ou hypothétiques :
- crise type 2008
- année type 2022 (actions + obligations pénalisées)
- stagnation boursière longue
- baisse immobilière française
- perte d’emploi 24 mois
- chute du non coté
- choc de taux
- choc inflationniste
- gros travaux imprévus
- baisse des loyers

Utilité :
- passage du “simulateur” à l’outil de pilotage

---

## 3.4. Moteur de cycle de vie

Le patrimoine dépend énormément de la vie du client.

Le moteur doit pouvoir simuler :

### Revenus professionnels
- salaire fixe
- bonus
- promotions
- progression de carrière
- chômage
- création d’entreprise
- vente d’entreprise
- retraite

### Dépenses
- dépenses courantes
- inflation du style de vie
- achat de résidence principale
- enfants
- études
- santé
- gros achats
- soutien familial

### Décisions patrimoniales
- achat immobilier
- vente d’actifs
- investissement mensuel plus élevé
- changement d’allocation
- remboursement anticipé de crédit
- arbitrage entre bourse et immobilier
- donation
- transmission
- expatriation

---

## 3.5. Moteur fiscal et juridique

Un outil haut niveau doit calculer le **net**, pas seulement le brut.

À terme, le moteur doit pouvoir gérer :
- fiscalité des dividendes
- fiscalité des plus-values
- fiscalité immobilière
- traitement des intérêts
- enveloppes fiscales françaises
- assurance-vie
- PEA / CTO / PER / PEE
- détention en direct ou via holding
- IFI si pertinent un jour
- scénarios de résidence fiscale
- donation / démembrement / transmission si un jour nécessaire

Important :
- ne pas mettre un “taux d’impôt moyen” global
- calculer l’impôt **par flux** et **par enveloppe**

---

## 3.6. Moteur de risque patrimonial

Le risque ne doit pas se limiter à la volatilité.

Le moteur doit analyser :

### Risques de marché
- volatilité annualisée
- max drawdown
- downside deviation
- VaR
- CVaR
- ratio de Sharpe
- ratio de Sortino
- durée moyenne de recovery
- probabilité d’année négative
- perte potentielle à horizon 1 an / 3 ans / 5 ans

### Risques de structure
- concentration par actif
- concentration par classe d’actifs
- concentration géographique
- concentration sectorielle
- concentration devise
- dépendance à l’entreprise familiale
- dépendance à une seule source de revenus

### Risques de liquidité
- part du patrimoine vendable rapidement
- part vendable en 30 jours
- part vendable en 6 mois
- part illiquide
- probabilité de tension de trésorerie

### Risques de cash-flow
- couverture des dépenses par les revenus passifs
- risque de devoir vendre dans un mauvais marché
- months of runway
- capacité à absorber un choc de revenu

### Risques personnels
- dépendance à la carrière
- dépendance au salaire principal
- poids du crédit
- fragilité en cas de changement de vie

---

## 3.7. Moteur d’optimisation / recommandation

Une fois qu’on sait simuler, la question naturelle devient :

> “Quelle décision est meilleure ?”

Le moteur idéal doit pouvoir comparer :
- rembourser le crédit ou investir
- acheter la RP ou rester locataire
- augmenter l’épargne mensuelle
- augmenter la part actions
- réduire l’illiquidité
- garder un coussin de sécurité plus élevé
- arbitrer immobilier / bourse / non coté
- modifier la répartition par enveloppe

Optimisations possibles :
- maximiser la richesse terminale médiane
- maximiser la probabilité d’atteindre un objectif
- minimiser le drawdown
- minimiser le risque de ruine
- maximiser le revenu passif
- minimiser la dépendance au salaire
- respecter une contrainte de liquidité

---

## 3.8. Couche d’explicabilité

Le moteur doit aussi expliquer :

### Ce qui tire le résultat
- capacité d’épargne
- effet du temps
- allocation actions
- levier immobilier
- croissance des revenus
- fiscalité

### Ce qui crée le risque
- concentration
- levier
- illiquidité
- faible réserve de cash
- dépendance au salaire
- part excessive d’un actif unique

### Sensibilités
- si rendement actions baisse de 1 %
- si inflation monte de 1 %
- si salaire stagne
- si loyers stagnent
- si vacance double
- si les taux restent élevés
- si une crise arrive au début du parcours

Le logiciel doit dire non seulement :
- ce qui peut arriver
mais aussi :
- pourquoi
- et sous l’effet de quels paramètres

---

# 4. Ce que le moteur doit produire concrètement

## 4.1. Sorties de richesse
- trajectoire médiane
- trajectoire moyenne
- percentiles 5 / 10 / 25 / 50 / 75 / 90 / 95
- histogramme du patrimoine final
- probabilité d’atteindre un objectif
- valeur minimale / maximale simulée
- probabilité d’être en perte à horizon donné

## 4.2. Sorties de revenu
- revenu passif annuel projeté
- revenu passif médian à horizon N
- couverture des dépenses par revenus passifs
- date estimée d’autonomie financière probabiliste
- probabilité de couvrir X % des dépenses

## 4.3. Sorties de risque
- volatilité du patrimoine
- max drawdown
- drawdown percentile
- VaR / CVaR
- Sharpe / Sortino
- probabilité de perte à 1 an / 3 ans / 5 ans
- temps moyen de recovery
- nombre moyen d’années négatives

## 4.4. Sorties de robustesse
- score de diversification
- score de liquidité
- score de robustesse patrimoniale
- risque de concentration
- risque de cash squeeze
- risque de dépendance au revenu actif

---

# 5. Les grands modules visibles à imaginer dans l’app

## 5.1. Module 1 — Projection simple
Objectif :
- rester ultra lisible
- être pédagogique
- servir de base

Affichage :
- courbe simple
- hypothèses affichées clairement
- contributions mensuelles / annuelles
- patrimoine final projeté

Utilité :
- premier niveau de lecture pour tout utilisateur

---

## 5.2. Module 2 — Simulation probabiliste
Objectif :
- montrer la distribution des trajectoires

Affichage :
- fan chart
- trajectoire médiane
- bandes percentiles
- histogramme du patrimoine final
- probabilité d’atteinte des objectifs

Utilité :
- cœur du moteur différenciant

---

## 5.3. Module 3 — Risque patrimonial
Objectif :
- montrer le vrai risque du patrimoine

Affichage :
- drawdown attendu
- volatilité
- Sharpe / Sortino
- VaR / CVaR
- radar de risque
- répartition liquidité / illiquidité
- concentration

Utilité :
- très fort pour un angle “finance / risk”

---

## 5.4. Module 4 — Stress tests
Objectif :
- montrer la réaction du patrimoine à des chocs

Affichage :
- liste de scénarios
- comparaison avant / après
- perte maximale
- tension de trésorerie
- temps de retour

Utilité :
- excellent outil d’aide à la décision

---

## 5.5. Module 5 — Comparateur de scénarios
Objectif :
- comparer plusieurs décisions

Exemples :
- scénario A : rester à 70 % actions
- scénario B : acheter un bien immobilier
- scénario C : rembourser le crédit
- scénario D : augmenter l’épargne à 1 500 €/mois

Affichage :
- comparaison médiane
- comparaison du percentile 10
- comparaison du drawdown
- comparaison de la probabilité d’atteindre l’objectif

---

# 6. Les objets métiers à modéliser

Cette partie est essentielle pour garder une architecture propre.

## 6.1. ProjectionProfile
Représente le profil de projection :
- horizon
- fréquence (mensuelle / annuelle)
- devise de base
- mode de simulation
- inflation
- hypothèses par défaut
- paramètres du moteur

---

## 6.2. Household / ScopeState
Représente l’état patrimonial de départ d’un scope :
- personne ou famille
- patrimoine actuel
- comptes
- actifs
- passifs
- flux récurrents
- enveloppes
- expositions

---

## 6.3. AssetBucket
Vue agrégée par grande classe d’actifs :
- cash
- equity
- bonds
- real_estate
- private_equity
- business
- crypto
- alternatives

Peut servir en V1 / V2 avant la modélisation ultra fine.

---

## 6.4. EconomicObject
Interface conceptuelle commune :
- current_value()
- project_one_step()
- cashflows_for_period()
- liquidity_profile()
- risk_exposure()

Puis sous-classes potentielles :
- ListedEquityPosition
- BondBucket
- RealEstateAsset
- PrivateEquityPosition
- BusinessAsset
- CreditLiability
- CashReserve

---

## 6.5. ProjectionScenario
Contient :
- nom du scénario
- hypothèses utilisateur
- stratégie d’épargne
- événements futurs
- règles de simulation
- éventuels stress appliqués

---

## 6.6. ProjectionResult
Payload final du moteur :
- séries temporelles
- percentiles
- histogramme
- KPI finaux
- métriques de risque
- diagnostics
- explications
- alertes

---

# 7. Représentation des classes d’actifs

Pour rester réaliste et propre, chaque grande classe d’actifs doit avoir des paramètres dédiés.

## 7.1. Actions cotées
- rendement moyen attendu
- volatilité
- dividende
- corrélations
- éventuel biais régional / sectoriel
- devise
- fiscalité de détention / cession

## 7.2. Obligations / monétaire
- rendement nominal
- sensibilité aux taux si un jour on va loin
- volatilité plus faible
- corrélation avec actions variable selon régime
- cash-like bucket pour V1

## 7.3. Immobilier
- valeur actuelle
- rendement locatif
- charges
- fiscalité
- vacance
- travaux
- dynamique de prix
- crédit associé
- friction à la vente
- faible liquidité

## 7.4. Private equity
- rendement cible plus élevé
- dispersion forte
- faible liquidité
- cashflows non linéaires
- appels de capitaux / distributions si modélisation avancée
- valorisation lissée à manipuler avec prudence

## 7.5. Entreprise / non coté opérationnel
- croissance
- marge / cash distribuable
- probabilité de sortie
- risque de rupture
- illiquidité
- forte concentration

## 7.6. Cash / fonds euro
- rendement faible
- volatilité faible
- forte liquidité
- réserve de sécurité

## 7.7. Crypto
- rendement espéré très incertain
- très forte volatilité
- drawdowns extrêmes
- poids à surveiller dans le score de concentration

---

# 8. Réalisme statistique maximal

Si l’on pousse vraiment loin, voici les raffinements importants.

## 8.1. Ne pas se limiter à la loi normale
Les marchés présentent :
- queues épaisses
- asymétries
- krachs plus fréquents que prévu

Donc à terme, envisager :
- Student-t
- distributions empiriques bootstrappées
- mélanges de lois
- chocs explicites

## 8.2. Corrélations dynamiques
En crise, les corrélations montent souvent.

Donc une diversification “théorique” peut moins protéger qu’attendu.

À terme :
- matrice de corrélation par régime
- corrélations stressées

## 8.3. Volatilité par régime
Une année “normale” n’a pas la même volatilité qu’une année de crise.

Donc :
- sigma normal
- sigma crise
- sigma inflation
- sigma reprise

## 8.4. Séquence de rendements
L’ordre des rendements compte énormément, surtout avec :
- retraits
- crédits
- objectif d’indépendance financière
- fort levier

Il faut donc garder une vraie logique de trajectoire et pas seulement un rendement annualisé final.

---

# 9. Les risques spécifiques à ne pas oublier

## 9.1. Risque de concentration
Exemples :
- une seule action
- un seul bien immobilier
- un seul employeur
- une seule entreprise non cotée

## 9.2. Risque d’illiquidité
Exemples :
- private equity
- immobilier
- société familiale
- objets peu cessibles

## 9.3. Risque de cashflow
Exemples :
- mensualités élevées
- loyers qui ne couvrent plus
- revenus professionnels instables
- dépenses trop rigides

## 9.4. Risque de séquence
Très important quand :
- on retire du cash
- on approche d’un objectif
- on dépend d’un portefeuille pour vivre

## 9.5. Risque fiscal
Exemples :
- mauvaise enveloppe
- fiscalité de sortie
- vente au mauvais moment
- frottements oubliés

---

# 10. Ce qu’il ne faut surtout pas faire

- promettre une valeur finale “exacte”
- faire croire qu’un patrimoine suit une trajectoire lisse
- appliquer un taux unique à toutes les classes d’actifs
- mélanger actifs liquides et illiquides sans distinction
- ignorer les crédits
- ignorer les flux
- ignorer la fiscalité
- ignorer l’ordre des rendements
- recalculer les KPI de projection dans l’UI

---

# 11. Implémentation dans TON application — philosophie d’architecture

L’application a déjà une architecture cible claire :

```text
UI -> Services -> Repository / DB
```

Il faut conserver strictement cette discipline.

L’onglet Projection doit donc être traité comme un **domaine métier autonome**, avec :

- pages/panels Qt uniquement orchestrateurs
- services de projection comme source unique de vérité
- repositories uniquement pour persistance des scénarios, presets et résultats éventuellement mis en cache
- aucune logique financière lourde dans l’UI

---

# 12. Alignement avec l’architecture actuelle

Le document SSOT indique déjà que :
- `services.projections.run_projection` est la source officielle des projections
- `services.projections.get_projection_base_for_scope` est la base officielle de projection
- la page concernée est `qt_ui/pages/goals_projection_page.py`

Donc l’idée n’est pas de multiplier les points d’entrée.

Au contraire :
- on enrichit **le domaine `services.projections`**
- on crée des sous-modules propres
- mais on conserve un **façade public unique** pour l’UI

---

# 13. Proposition d’architecture propre pour le domaine projection

## 13.1. Façade publique
Fichier principal :
- `services/projections.py`

Fonctions publiques possibles :
- `get_projection_base_for_scope(conn, scope_type, scope_id)`
- `run_projection(conn, scope_type, scope_id, config)`
- `run_projection_comparison(conn, scope_type, scope_id, scenario_configs)`
- `list_projection_presets(conn, scope_type, scope_id)`
- `save_projection_preset(conn, payload)`
- `delete_projection_preset(conn, preset_id)`

Idée :
- la page Qt appelle uniquement ces fonctions publiques
- aucune importation UI de modules internes

---

## 13.2. Sous-modules internes possibles

### `services/projection_base.py`
Responsabilité :
- construire l’état initial du patrimoine à projeter
- consolider actifs, passifs, revenus, dépenses, réserves
- produire un payload propre de base

### `services/projection_models.py`
Responsabilité :
- définitions de dataclasses / objets métier
- `ProjectionConfig`
- `ProjectionBase`
- `ProjectionScenario`
- `ProjectionResult`
- `RiskMetrics`
- `GoalResult`
- `ScenarioComparison`

### `services/projection_engines/`
Dossier pouvant contenir :

#### `deterministic_engine.py`
- projection simple
- rendement fixe
- inflation fixe
- cashflows simples

#### `monte_carlo_engine.py`
- simulation Monte Carlo
- corrélations
- trajectoires multiples
- percentiles

#### `regime_engine.py`
- simulation par régimes de marché
- matrices de transition
- paramètres par régime

#### `stress_engine.py`
- stress tests
- chocs historiques / hypothétiques

### `services/projection_risk.py`
Responsabilité :
- calcul des métriques de risque
- volatilité
- max drawdown
- VaR
- CVaR
- Sharpe
- Sortino
- recovery

### `services/projection_goals.py`
Responsabilité :
- calcul des objectifs
- probabilité d’atteinte
- temps médian d’atteinte
- comparaison des scénarios

### `services/projection_explain.py`
Responsabilité :
- générer diagnostics et explications lisibles
- points forts
- alertes
- sensibilités simples

### `services/projection_presets_repository.py`
Responsabilité :
- stockage des presets / scénarios utilisateur
- repository dédié si nécessaire

---

# 14. Structure de payload recommandée

L’UI a besoin de payloads stables, lisibles et faciles à exploiter.

## 14.1. ProjectionBase
Doit contenir au minimum :
- scope_type
- scope_id
- as_of_date
- currency
- current_net_worth
- asset_breakdown
- liabilities_breakdown
- recurring_income
- recurring_expenses
- savings_capacity_estimate
- liquidity_buffer
- exposures
- assumptions_default

---

## 14.2. ProjectionConfig
Doit contenir :
- horizon_years
- time_step
- engine_type
- inflation_assumption
- monthly_contribution_override
- rebalancing_policy
- withdrawal_policy
- return_assumptions
- volatility_assumptions
- correlation_matrix
- stress_profile
- goals
- include_tax
- include_real_estate
- include_private_equity
- include_business_assets

---

## 14.3. ProjectionResult
Doit contenir :
- metadata
- summary_kpis
- deterministic_series éventuelle
- percentile_series
- scenario_paths_sample
- ending_wealth_distribution
- ending_income_distribution
- risk_metrics
- goal_metrics
- diagnostics
- alerts
- chart_payloads

---

# 15. Comment brancher cela proprement dans l’UI

## 15.1. La page Qt ne calcule rien
`qt_ui/pages/goals_projection_page.py` doit :
- charger la base de projection via service
- construire le formulaire d’hypothèses
- appeler `run_projection(...)`
- afficher les résultats
- gérer l’état vide / loading / erreurs
- gérer la sélection des presets

Elle ne doit pas :
- recalculer des séries
- faire des groupby métiers complexes
- recoder le Monte Carlo
- recalculer les KPI de risque

---

## 15.2. Les panels de projection possibles
On peut découper l’interface en sous-panels légers :

- `projection_assumptions_panel.py`
- `projection_summary_panel.py`
- `projection_distribution_panel.py`
- `projection_risk_panel.py`
- `projection_stress_panel.py`
- `projection_goals_panel.py`
- `projection_scenarios_panel.py`

Mais ces panels restent purement UI.

---

## 15.3. Chart payloads
Comme l’app utilise Plotly, le service peut renvoyer des payloads déjà prêts ou semi-prêts pour :

- courbe simple
- fan chart percentiles
- histogramme
- comparaison de scénarios
- waterfall explicative
- radar de risque

Cela réduit encore la logique côté UI.

---

# 16. Ordre de développement recommandé

## V1 — Base crédible et propre
Objectif :
- avoir vite quelque chose d’utile et présentable

À faire :
- base de projection consolidée
- moteur déterministe
- moteur Monte Carlo simple corrélé
- fan chart
- histogramme du patrimoine final
- probabilité d’atteinte d’objectif
- premiers KPI : médiane, percentile 10, percentile 90, volatilité approx, max drawdown simulé

Pourquoi :
- déjà très différenciant
- relativement raisonnable à coder
- parfaitement montrable

---

## V2 — Version finance sérieuse
À faire :
- moteur de risque complet
- stress tests
- scénarios comparatifs
- moteur immobilier séparé
- gestion plus fine des revenus / dépenses
- réserves de liquidité
- score de robustesse patrimoniale

Pourquoi :
- rend la projection beaucoup plus crédible
- donne une vraie profondeur analytique

---

## V3 — Version premium
À faire :
- régimes de marché
- corrélations dynamiques
- distributions non normales
- private equity plus réaliste
- entreprise non cotée
- fiscalité plus détaillée
- optimisation multi-objectifs
- module transmission / donation

Pourquoi :
- vrai niveau family office / wealth tech premium
- mais beaucoup plus long

---

# 17. Ce qu’il faut afficher pour impressionner en entretien

Si tu veux que cette partie serve aussi de démonstration en entretien, il faut mettre l’accent sur :

## 17.1. La rigueur conceptuelle
Expliquer que :
- tu n’utilises pas un taux unique
- tu différencies les classes d’actifs
- tu simules des trajectoires
- tu raisonnes en probabilités
- tu distingues performance et risque
- tu tiens compte de la liquidité et des flux

## 17.2. La qualité d’architecture
Expliquer que :
- le domaine projection est proprement isolé dans `services`
- l’UI ne fait que l’orchestration
- les points d’entrée sont publics et stables
- les KPI viennent d’une SSOT
- l’app reste maintenable après refactor

## 17.3. La lisibilité utilisateur
Expliquer que :
- l’objectif n’est pas de faire “complexe pour faire complexe”
- l’objectif est d’aider à décider
- donc les résultats doivent être clairs, visuels et explicables

---

# 18. Idées de KPI / scores propriétaires

Pour enrichir l’app, on peut imaginer des indicateurs “maison”.

## 18.1. Score de robustesse patrimoniale
Composantes possibles :
- diversification
- liquidité
- stabilité des revenus
- levier
- risque de drawdown
- capacité à absorber un choc

## 18.2. Score d’autonomie financière
Composantes possibles :
- couverture des dépenses par revenus passifs
- stabilité des revenus passifs
- réserve de sécurité
- probabilité de maintien de l’autonomie

## 18.3. Score de concentration
Composantes possibles :
- poids du plus gros actif
- poids du non coté
- poids de l’immobilier
- dépendance à une seule source de revenu

## 18.4. Score de résilience de cashflow
Composantes possibles :
- mois de survie sans revenu actif
- part des dépenses incompressibles
- coussin liquide
- poids des mensualités de crédit

---

# 19. Stress tests très intéressants à intégrer un jour

- krach actions brutal dès l’année 1
- 10 ans de marché mou
- inflation forte pendant 5 ans
- hausse prolongée des taux
- crise immobilière
- vacance locative prolongée
- gros travaux imprévus
- perte de revenu principal pendant 12 ou 24 mois
- baisse forte de la valeur d’une entreprise non cotée
- double choc : marché baissier + perte de revenu

---

# 20. Exemples d’objectifs utilisateur à supporter

- atteindre 100 k€ de patrimoine financier
- atteindre 1 M€ de patrimoine net
- couvrir 100 % des dépenses par revenus passifs
- acheter une résidence principale à date cible
- rembourser tous les crédits avant telle date
- atteindre un niveau de revenu passif mensuel
- limiter le drawdown max sous un seuil
- conserver X mois de réserve de sécurité

---

# 21. Tests à prévoir côté développement

## 21.1. Tests unitaires
- projection déterministe simple
- cashflows récurrents
- calcul des percentiles
- calcul du max drawdown
- VaR / CVaR
- objectifs atteints / non atteints
- sensibilité aux hypothèses

## 21.2. Tests d’intégration
- base de projection personne
- base de projection famille
- cohérence entre base et résultat
- UI qui consomme bien le payload sans recalcul

## 21.3. Tests de non-régression
- mêmes inputs → mêmes outputs à seed fixée
- compatibilité avec le refactor SSOT
- absence d’imports interdits dans l’UI

## 21.4. Tests de performance
- 1 000 scénarios
- 10 000 scénarios
- horizon 10 / 20 / 40 ans
- temps de calcul acceptable pour desktop

---

# 22. Choix d’implémentation pratiques

## 22.1. Fréquence de calcul
Pour une V1 :
- projection annuelle peut suffire

Pour une V2 :
- projection mensuelle plus réaliste pour :
  - contributions
  - dépenses
  - crédits
  - cashflow

Compromis :
- moteur interne mensuel
- affichage annuel agrégé si besoin

---

## 22.2. Reproductibilité
Toujours permettre :
- seed fixe optionnelle
- mode debug
- échantillon de trajectoires stable

Très utile pour :
- tests
- debug
- comparaisons avant / après refactor

---

## 22.3. Séparation config / moteur / rendu
Il faut garder 3 couches claires :

### configuration
- hypothèses utilisateur
- presets
- objectifs

### calcul
- moteurs de simulation
- risque
- diagnostics

### rendu
- transformations Plotly
- widgets Qt
- mise en forme

---

# 23. Une proposition simple de roadmap concrète

## Étape 1
Créer une base documentaire solide
- ce fichier
- conventions du domaine
- liste de KPI ciblés en V1

## Étape 2
Nettoyer / confirmer `get_projection_base_for_scope`
- inventaire des données disponibles
- mapping par classes d’actifs
- flux revenus / dépenses utilisés
- dette / liquidités / bourse / immobilier / non coté

## Étape 3
Créer les dataclasses du domaine
- `ProjectionConfig`
- `ProjectionBase`
- `ProjectionResult`
- `RiskMetrics`
- `GoalMetrics`

## Étape 4
Implémenter moteur déterministe
- ultra simple
- stable
- testable
- base pour l’UI

## Étape 5
Implémenter Monte Carlo corrélé V1
- rendements aléatoires
- corrélations
- percentiles
- histogramme

## Étape 6
Implémenter métriques de risque principales
- volatilité
- max drawdown
- Sharpe simplifié
- VaR / CVaR simples

## Étape 7
Implémenter comparaison de scénarios
- scenario A / B / C
- même page
- très forte valeur produit

## Étape 8
Ajouter stress tests
- surtout si V1/V2 déjà propre

---

# 24. Résumé exécutif

Le moteur de projection idéal ne doit pas être :
- une calculatrice de taux composés

Il doit devenir :
- un moteur probabiliste
- multi-actifs
- orienté flux
- sensible à la liquidité
- capable d’analyser le risque
- capable de comparer des décisions
- proprement isolé dans l’architecture existante

La bonne ambition pour ton application est :

> Transformer l’onglet Projection en un véritable **moteur de pilotage patrimonial**, pas seulement en un simulateur de patrimoine final.

Et pour rester réaliste dans le développement :

- V1 : déterministe + Monte Carlo corrélé + objectifs + distribution
- V2 : risque + stress tests + scénarios
- V3 : régimes + fiscalité avancée + private equity + non coté + optimisation

---

# 25. Principe final à garder en tête

La phrase fondatrice du module pourrait être :

> Un patrimoine n’est pas un portefeuille qui capitalise à taux fixe.  
> C’est un système vivant, composé d’actifs, de passifs, de flux, de contraintes, de risques, de fiscalité et de décisions dans le temps.

Si le module Projection reste fidèle à cette idée, il pourra être :
- utile pour toi
- cohérent avec l’architecture refactorée
- techniquement propre
- intellectuellement crédible
- très fort à montrer en entretien
