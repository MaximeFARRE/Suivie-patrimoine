from __future__ import annotations
import pandas as pd
from datetime import datetime
import pytz


def _paris_today() -> pd.Timestamp:
    tz = pytz.timezone("Europe/Paris")
    return pd.Timestamp(datetime.now(tz).date())


def _week_monday(d: pd.Timestamp) -> pd.Timestamp:
    d = pd.to_datetime(d)
    return (d - pd.Timedelta(days=int(d.weekday()))).normalize()


def list_people(conn) -> pd.DataFrame:
    try:
        return pd.read_sql_query("SELECT id, name FROM people ORDER BY id", conn)
    except Exception:
        return pd.DataFrame()


def last_market_dates(conn) -> dict:
    """
    Dernières dates en base pour prix & FX weekly.
    """
    out = {"last_price_week": None, "last_fx_week": None}
    try:
        r = conn.execute("SELECT MAX(week_date) AS d FROM asset_prices_weekly").fetchone()
        out["last_price_week"] = r["d"] if r else None
    except Exception:
        pass
    try:
        r = conn.execute("SELECT MAX(week_date) AS d FROM fx_rates_weekly").fetchone()
        out["last_fx_week"] = r["d"] if r else None
    except Exception:
        pass
    return out


def last_snapshot_week_by_person(conn) -> pd.DataFrame:
    """
    Dernière semaine snapshot par personne.
    """
    try:
        return pd.read_sql_query(
            """
            SELECT p.id AS person_id, p.name AS person_name,
                   MAX(s.week_date) AS last_week
            FROM people p
            LEFT JOIN patrimoine_snapshots_weekly s ON s.person_id = p.id
            GROUP BY p.id, p.name
            ORDER BY p.id
            """,
            conn,
        )
    except Exception:
        return pd.DataFrame(columns=["person_id", "person_name", "last_week"])


def missing_snapshot_weeks(conn, person_id: int, lookback_days: int = 90) -> pd.DataFrame:
    """
    Liste des semaines manquantes (W-MON) pour une personne sur une fenêtre.
    """
    end = _week_monday(_paris_today())
    start = _week_monday(end - pd.Timedelta(days=int(lookback_days)))

    all_weeks = pd.date_range(start=start, end=end, freq="W-MON")
    try:
        df = pd.read_sql_query(
            "SELECT week_date FROM patrimoine_snapshots_weekly WHERE person_id=?",
            conn,
            params=(int(person_id),),
        )
        df["week_date"] = pd.to_datetime(df["week_date"], errors="coerce")
        have = set(df.dropna(subset=["week_date"])["week_date"].dt.normalize().tolist())
    except Exception:
        have = set()

    missing = [w for w in all_weeks if w.normalize() not in have]
    return pd.DataFrame({"missing_week": [x.strftime("%Y-%m-%d") for x in missing]})


def family_missing_weeks(conn, lookback_days: int = 90) -> pd.DataFrame:
    """
    Semaines manquantes côté famille (table famille weekly) si tu l'as.
    """
    end = _week_monday(_paris_today())
    start = _week_monday(end - pd.Timedelta(days=int(lookback_days)))
    all_weeks = pd.date_range(start=start, end=end, freq="W-MON")

    have = set()
    try:
        df = pd.read_sql_query("SELECT week_date FROM patrimoine_snapshots_family_weekly", conn)
        df["week_date"] = pd.to_datetime(df["week_date"], errors="coerce")
        have = set(df.dropna(subset=["week_date"])["week_date"].dt.normalize().tolist())
    except Exception:
        have = set()

    missing = [w for w in all_weeks if w.normalize() not in have]
    return pd.DataFrame({"missing_week": [x.strftime("%Y-%m-%d") for x in missing]})


def tickers_missing_weekly_prices(conn, max_show: int = 30) -> pd.DataFrame:
    """
    Diagnostic simple : tickers vus dans transactions (ACHAT/VENTE)
    qui n'ont AUCUN prix weekly en base.
    (V1 : facile, utile, pas parfait mais efficace)
    """
    try:
        tx = pd.read_sql_query(
            """
            SELECT DISTINCT asset_symbol AS ticker
            FROM transactions
            WHERE asset_symbol IS NOT NULL
              AND TRIM(asset_symbol) <> ''
              AND type IN ('ACHAT','VENTE')
            """,
            conn,
        )
    except Exception:
        return pd.DataFrame(columns=["ticker", "has_price"])

    if tx.empty:
        return pd.DataFrame(columns=["ticker", "has_price"])

    tickers = tx["ticker"].astype(str).str.strip().unique().tolist()

    rows = []
    for t in tickers:
        try:
            r = conn.execute(
                "SELECT 1 FROM asset_prices_weekly WHERE ticker=? LIMIT 1",
                (t,),
            ).fetchone()
            has = True if r else False
        except Exception:
            has = False
        if not has:
            rows.append({"ticker": t, "has_price": False})

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.head(int(max_show))
