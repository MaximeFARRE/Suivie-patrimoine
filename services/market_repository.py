import sqlite3
import pandas as pd

def upsert_asset_price_weekly(conn: sqlite3.Connection, symbol: str, week_date: str, adj_close: float, currency: str | None = None, source: str = "YFINANCE") -> None:
    conn.execute(
        """
        INSERT INTO asset_prices_weekly(symbol, week_date, adj_close, currency, source)
        VALUES (?,?,?,?,?)
        ON CONFLICT(symbol, week_date) DO UPDATE SET
            adj_close = excluded.adj_close,
            currency = excluded.currency,
            source = excluded.source
        """,
        (symbol, week_date, float(adj_close), currency, source),
    )

def get_asset_price_asof(conn: sqlite3.Connection, symbol: str, week_date: str):
    return conn.execute(
        """
        SELECT symbol, week_date, adj_close, currency, source
        FROM asset_prices_weekly
        WHERE symbol = ? AND week_date <= ?
        ORDER BY week_date DESC
        LIMIT 1
        """,
        (symbol, week_date),
    ).fetchone()

def upsert_fx_rate_weekly(conn: sqlite3.Connection, base_ccy: str, quote_ccy: str, week_date: str, rate: float, source: str = "YFINANCE") -> None:
    conn.execute(
        """
        INSERT INTO fx_rates_weekly(base_ccy, quote_ccy, week_date, rate, source)
        VALUES (?,?,?,?,?)
        ON CONFLICT(base_ccy, quote_ccy, week_date) DO UPDATE SET
            rate = excluded.rate,
            source = excluded.source
        """,
        (base_ccy.upper(), quote_ccy.upper(), week_date, float(rate), source),
    )

def get_fx_rate_asof(conn: sqlite3.Connection, base_ccy: str, quote_ccy: str, week_date: str):
    return conn.execute(
        """
        SELECT base_ccy, quote_ccy, week_date, rate, source
        FROM fx_rates_weekly
        WHERE base_ccy = ? AND quote_ccy = ? AND week_date <= ?
        ORDER BY week_date DESC
        LIMIT 1
        """,
        (base_ccy.upper(), quote_ccy.upper(), week_date),
    ).fetchone()

def list_weekly_snapshots(conn: sqlite3.Connection, person_id: int) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT week_date, week_date AS snapshot_date, created_at, mode,
               patrimoine_net, patrimoine_brut,
               liquidites_total, bank_cash, bourse_cash, pe_cash,
               bourse_holdings, pe_value, ent_value, credits_remaining
        FROM patrimoine_snapshots_weekly
        WHERE person_id = ?
        ORDER BY week_date ASC
        """,
        conn,
        params=(int(person_id),),
    )
