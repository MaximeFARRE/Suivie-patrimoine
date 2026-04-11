"""
Tests contrat FX : vérifie que les fonctions de conversion respectent le contrat
"None si taux manquant, jamais de montant brut silencieux".
"""
import pytest
from unittest.mock import patch


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_conn_no_fx():
    """Connexion SQLite en mémoire sans aucun taux FX en base."""
    import sqlite3
    from pathlib import Path

    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    schema = (Path(__file__).parent.parent / "db" / "schema.sql").read_text(encoding="utf-8")
    for stmt in schema.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.upper().startswith("PRAGMA"):
            try:
                c.execute(stmt)
            except Exception:
                pass
    c.commit()
    return c


# ── fx.convert ────────────────────────────────────────────────────────────────

class TestFxConvert:
    def test_same_currency_returns_amount(self, conn):
        from services import fx
        result = fx.convert(conn, 100.0, "EUR", "EUR")
        assert result == pytest.approx(100.0)

    def test_missing_rate_returns_none(self):
        """Si le taux est absent en DB et que l'API échoue → None, pas le montant brut."""
        conn = _make_conn_no_fx()
        from services import fx

        with patch("services.fx.fetch_fx_rate", return_value=None):
            result = fx.convert(conn, 100.0, "USD", "EUR")

        assert result is None, (
            "fx.convert doit retourner None quand le taux est introuvable, "
            f"mais a retourné {result!r}"
        )

    def test_known_rate_converts_correctly(self, conn):
        from services import fx, repositories as repo, pricing

        repo.insert_fx_rate(conn, "USD", "EUR", pricing.today_str(), 0.92)
        conn.commit()

        result = fx.convert(conn, 100.0, "USD", "EUR")
        assert result == pytest.approx(92.0)


# ── market_history.convert_weekly ────────────────────────────────────────────

class TestConvertWeekly:
    def test_same_currency_returns_amount(self, conn):
        from services import market_history
        result = market_history.convert_weekly(conn, 50.0, "EUR", "EUR", "2024-01-01")
        assert result == pytest.approx(50.0)

    def test_missing_fx_returns_none(self, conn):
        """Taux hebdo absent → None, pas le montant brut."""
        from services import market_history
        result = market_history.convert_weekly(conn, 100.0, "USD", "EUR", "2024-01-01")
        assert result is None, (
            "convert_weekly doit retourner None quand le taux hebdo est absent, "
            f"mais a retourné {result!r}"
        )

    def test_known_weekly_rate_converts(self, conn):
        from services import market_history
        from services import market_repository as mrepo

        mrepo.upsert_fx_rate_weekly(conn, "USD", "EUR", "2024-01-01", 0.91)
        conn.commit()

        result = market_history.convert_weekly(conn, 200.0, "USD", "EUR", "2024-01-01")
        assert result == pytest.approx(182.0)


# ── liquidites._fx_to_eur ────────────────────────────────────────────────────

class TestFxToEur:
    def test_eur_returns_amount_unchanged(self, conn):
        from services.liquidites import _fx_to_eur
        assert _fx_to_eur(conn, 42.0, "EUR") == pytest.approx(42.0)

    def test_missing_rate_returns_none_not_raw_amount(self):
        """Cas critique : pas de taux → None, jamais le montant brut."""
        conn = _make_conn_no_fx()
        from services.liquidites import _fx_to_eur

        result = _fx_to_eur(conn, 100.0, "USD")
        assert result is None, (
            "_fx_to_eur doit retourner None quand le taux est absent, "
            f"mais a retourné {result!r} (fallback dangereux détecté)"
        )

    def test_direct_rate_used(self, conn):
        from services import repositories as repo, pricing
        from services.liquidites import _fx_to_eur

        repo.insert_fx_rate(conn, "USD", "EUR", pricing.today_str(), 0.93)
        conn.commit()

        result = _fx_to_eur(conn, 100.0, "USD")
        assert result == pytest.approx(93.0)

    def test_inverse_rate_used_when_direct_absent(self, conn):
        """Si seul EUR→USD est en base, on doit l'inverser pour obtenir USD→EUR."""
        from services import repositories as repo, pricing
        from services.liquidites import _fx_to_eur

        repo.insert_fx_rate(conn, "EUR", "USD", pricing.today_str(), 1.10)
        conn.commit()

        result = _fx_to_eur(conn, 110.0, "USD")
        # 110 USD / 1.10 = 100 EUR
        assert result == pytest.approx(100.0, rel=1e-4)


# ── valorisation impossible ───────────────────────────────────────────────────

class TestValuationImpossible:
    def test_convert_weekly_zero_amount_no_rate(self, conn):
        """Même un montant nul avec FX manquant doit retourner None."""
        from services import market_history
        result = market_history.convert_weekly(conn, 0.0, "GBP", "EUR", "2024-01-01")
        # 0.0 * None ne doit pas crasher, mais le taux reste absent
        # GBP→EUR pas en base → None
        assert result is None

    def test_fx_convert_exotic_currency_no_rate(self):
        """Devise exotique sans taux → None, jamais le montant original."""
        conn = _make_conn_no_fx()
        from services import fx

        with patch("services.fx.fetch_fx_rate", return_value=None):
            result = fx.convert(conn, 500.0, "COP", "EUR")

        assert result is None
