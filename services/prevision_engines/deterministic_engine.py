import pandas as pd
from ..prevision_models import PrevisionBase, PrevisionConfig, PrevisionResult

def run_deterministic_projection(base: PrevisionBase, config: PrevisionConfig) -> PrevisionResult:
    """
    Moteur déterministe simple : applique des taux constants.
    Idéal pour une projection pédagogique très basique.
    """
    years = config.horizon_years
    months = years * 12
    
    total_wealth = base.current_net_worth
    
    # Calcul d'un rendement global pondéré (V1 très grossière)
    weighted_return = (
        (base.current_cash / total_wealth * config.expected_cash_return) +
        (base.current_equity / total_wealth * config.expected_equity_return)
        if total_wealth > 0 else 0
    )
    
    monthly_rate = (1 + weighted_return) ** (1/12) - 1
    inflation_monthly = (1 + config.inflation_rate) ** (1/12) - 1
    
    # Taux réel simple
    real_rate = (1 + monthly_rate) / (1 + inflation_monthly) - 1
    
    values = [total_wealth]
    current_val = total_wealth
    
    for _ in range(months):
        current_val = current_val * (1 + real_rate) + config.monthly_contribution
        values.append(current_val)
        
    dates = pd.date_range(start=pd.Timestamp.today().normalize(), periods=months+1, freq='ME')
    series = pd.Series(values, index=dates)
    
    result = PrevisionResult(
        config=config,
        base=base,
        median_series=series,
        final_net_worth_median=values[-1]
    )
    
    return result
