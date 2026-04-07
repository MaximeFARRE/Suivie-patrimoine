import pytest
from services.prevision_models import PrevisionConfig
from services.prevision import run_prevision

@pytest.fixture
def dummy_conn():
    return None

def test_run_prevision_deterministic(dummy_conn):
    config = PrevisionConfig(
        horizon_years=5,
        monthly_contribution=1000.0,
        expected_equity_return=0.08,
        expected_cash_return=0.02,
        inflation_rate=0.02
    )
    result = run_prevision(dummy_conn, "person", 1, config, engine="deterministic")
    
    assert result is not None
    assert result.base.current_net_worth == 100000.0
    assert result.final_net_worth_median > 100000.0
    # 5 ans * 12 + 1 = 61 dates
    assert len(result.median_series) == 61
    
    assert result.risk_metrics is not None
    assert result.diagnostics is not None

def test_run_prevision_monte_carlo(dummy_conn):
    config = PrevisionConfig(
        horizon_years=3,
        num_simulations=100,
        target_goal_amount=120000.0,
        seed=42
    )
    result = run_prevision(dummy_conn, "person", 1, config, engine="monte_carlo")
    
    assert result is not None
    assert result.trajectories_df is not None
    assert result.trajectories_df.shape == (100, 37)
    
    assert result.percentile_10_series is not None
    assert result.percentile_90_series is not None
    
    assert result.risk_metrics is not None
    assert result.risk_metrics.max_drawdown <= 0.0
    assert result.goal_metrics is not None
    assert result.goal_metrics.probability_of_success >= 0.0
