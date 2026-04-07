import pandas as pd
import numpy as np
from ..prevision_models import PrevisionBase, PrevisionConfig, PrevisionResult

def run_monte_carlo_projection(base: PrevisionBase, config: PrevisionConfig) -> PrevisionResult:
    """
    Moteur probabiliste (Monte Carlo) : introduit de l'aléa autour du rendement pour obtenir
    une distribution de trajectoires et une fan chart.
    """
    if config.seed is not None:
        np.random.seed(config.seed)
        
    years = config.horizon_years
    months = years * 12
    n_sims = config.num_simulations
    
    initial_wealth = base.current_net_worth
    
    weighted_return = config.expected_equity_return
    weighted_vol = config.expected_equity_volatility
    
    # Paramètres mensuels standardisés
    mu_monthly = weighted_return / 12
    sigma_monthly = weighted_vol / np.sqrt(12)
    inflation_monthly = config.inflation_rate / 12
    
    # Génération des rendements (N simulations x nb mois)
    random_returns = np.random.normal(mu_monthly, sigma_monthly, (n_sims, months))
    real_returns = random_returns - inflation_monthly
    
    paths = np.zeros((n_sims, months + 1))
    paths[:, 0] = initial_wealth
    
    for t in range(1, months + 1):
        paths[:, t] = paths[:, t-1] * (1 + real_returns[:, t-1]) + config.monthly_contribution
        
    dates = pd.date_range(start=pd.Timestamp.today().normalize(), periods=months+1, freq='ME')
    df_paths = pd.DataFrame(paths.T, index=dates)
    
    # Extraction des métriques
    median_series = df_paths.median(axis=1)
    p10_series = df_paths.quantile(0.10, axis=1)
    p90_series = df_paths.quantile(0.90, axis=1)
    
    result = PrevisionResult(
        config=config,
        base=base,
        median_series=median_series,
        percentile_10_series=p10_series,
        percentile_90_series=p90_series,
        trajectories_df=df_paths,
        final_net_worth_median=float(median_series.iloc[-1])
    )
    
    return result
