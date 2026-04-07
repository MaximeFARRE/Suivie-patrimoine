from dataclasses import dataclass, field
from typing import List, Dict, Optional
import pandas as pd

@dataclass
class PrevisionConfig:
    """Paramètres globaux pour la simulation de prévision."""
    horizon_years: int = 20
    monthly_contribution: float = 0.0
    expected_equity_return: float = 0.07
    expected_equity_volatility: float = 0.15
    expected_cash_return: float = 0.02
    num_simulations: int = 1000
    target_goal_amount: Optional[float] = None
    inflation_rate: float = 0.02
    seed: Optional[int] = 42

@dataclass
class PrevisionBase:
    """État patrimonial de départ pour la projection."""
    current_net_worth: float
    current_cash: float
    current_equity: float
    current_real_estate: float
    # TODO: Ajouter plus de granularité (PE, entreprises, crédits) pour la V2
    
@dataclass
class RiskMetrics:
    """Métriques de risque calculées sur l'ensemble de la projection."""
    volatility: float
    max_drawdown: float
    var_95: float
    cvar_95: float
    # TODO: Ajouter ratios qualitatifs par la suite (Sharpe, Sortino)

@dataclass
class GoalMetrics:
    """Évaluation de l'atteinte des objectifs patrimoniaux."""
    probability_of_success: float
    median_shortfall: Optional[float]
    years_to_goal_median: Optional[float]

@dataclass
class PrevisionResult:
    """Payload de résultat consolidé d'une simulation."""
    config: PrevisionConfig
    base: PrevisionBase
    
    # Séries temporelles
    median_series: pd.Series
    percentile_10_series: Optional[pd.Series] = None
    percentile_90_series: Optional[pd.Series] = None
    
    # Toutes les trajectoires si l'approche est stochastique
    trajectories_df: Optional[pd.DataFrame] = None
    
    final_net_worth_median: float = 0.0
    
    risk_metrics: Optional[RiskMetrics] = None
    goal_metrics: Optional[GoalMetrics] = None
    diagnostics: List[str] = field(default_factory=list)
