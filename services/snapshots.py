from __future__ import annotations
import datetime as dt
import logging
from datetime import datetime
import pandas as pd
import pytz

from services import repositories as repo
from services import market_history
from services import positions
from services import private_equity_repository as pe_repo
from services import entreprises_repository as ent_repo
from services import immobilier_repository as immo_repo
from services.credits import list_credits_by_person, get_crd_a_date

_logger = logging.getLogger(__name__)

# pe cash tx repo (existe déjà chez toi)
try:
    from services import pe_cash_repository as pe_cash_repo
except Exception:
    pe_cash_repo = None

def _now_paris_iso() -> str:
    tz = pytz.timezone("Europe/Paris")
    return datetime.now(tz).replace(microsecond=0).isoformat()

def _today_paris_date() -> dt.date:
    tz = pytz.timezone("Europe/Paris")
    return datetime.now(tz).date()

def _list_weeks(start: dt.date, end: dt.date) -> list[str]:
    s = market_history.week_start(start)
    e = market_history.week_start(end)
    out = []
    cur = s
    while cur <= e:
        out.append(cur.isoformat())
        cur += dt.timedelta(days=7)
    return out


def _collect_person_market_sync_inputs(conn, person_id: int) -> tuple[list[str], list[tuple[str, str]]]:
    """Construit les symboles et paires FX à synchroniser pour une personne."""
    tx = repo.list_transactions(conn, person_id=person_id, limit=300000)
    symbols: list[str] = []
    pairs: set[tuple[str, str]] = set()

    if tx is not None and not tx.empty:
        tx2 = tx[tx["asset_symbol"].notna()].copy()
        symbols = sorted(set([str(s).strip() for s in tx2["asset_symbol"].tolist() if str(s).strip()]))

        asset_ids = sorted(set([int(x) for x in tx2["asset_id"].dropna().astype(int).tolist()]))
        if asset_ids:
            q = ",".join(["?"] * len(asset_ids))
            rows = conn.execute(f"SELECT id, currency FROM assets WHERE id IN ({q})", tuple(asset_ids)).fetchall()
            for r in rows:
                ccy = (r["currency"] or "EUR").upper()
                if ccy != "EUR":
                    pairs.add((ccy, "EUR"))

    accounts = repo.list_accounts(conn, person_id=person_id)
    if accounts is not None and not accounts.empty:
        for _, acc in accounts.iterrows():
            ccy = str(acc.get("currency") or "EUR").upper()
            if ccy != "EUR":
                pairs.add((ccy, "EUR"))

    pairs.add(("USD", "EUR"))
    return symbols, sorted(list(pairs))


def _sync_person_market_data_for_weeks(conn, person_id: int, week_start: str, week_end: str) -> None:
    """Synchronise les historiques marché utiles au rebuild entre deux semaines incluses."""
    symbols, pairs = _collect_person_market_sync_inputs(conn, person_id)
    if symbols:
        market_history.sync_asset_prices_weekly(conn, symbols, week_start, week_end)
    if pairs:
        market_history.sync_fx_weekly(conn, pairs, week_start, week_end)

# --------------------
# CASH BANQUE as-of
# --------------------

# Map vectorisé pour éviter .apply(lambda) ligne à ligne
_SENS_FLUX_MAP: dict[str, int] = {
    "DEPOT": 1, "ENTREE": 1, "CREDIT": 1, "VENTE": 1,
    "DIVIDENDE": 1, "INTERETS": 1, "LOYER": 1, "ABONDEMENT": 1,
    "RETRAIT": -1, "SORTIE": -1, "DEBIT": -1, "ACHAT": -1,
    "DEPENSE": -1, "FRAIS": -1, "IMPOT": -1, "REMBOURSEMENT_CREDIT": -1,
}


def _sum_cash_native(df: pd.DataFrame) -> float:
    """Calcule le solde natif d'un DataFrame de transactions (vectorisé)."""
    if df.empty:
        return 0.0
    amount = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    sens = df["type"].astype(str).str.strip().str.upper().map(_SENS_FLUX_MAP).fillna(0)
    return float((amount * sens).sum())


def _bank_cash_asof_eur(conn, person_id: int, week_date: str,
                        tx_cache: "dict[int, pd.DataFrame] | None" = None) -> float:
    accounts = repo.list_accounts(conn, person_id=person_id)
    if accounts is None or accounts.empty:
        return 0.0

    banks = accounts[accounts["account_type"].astype(str).str.upper() == "BANQUE"].copy()
    total_eur = 0.0

    def _get_tx(account_id: int) -> pd.DataFrame:
        """Récupère les transactions <= week_date depuis le cache ou la DB."""
        if tx_cache is not None and account_id in tx_cache:
            df = tx_cache[account_id]
            return df[df["date"] <= week_date] if not df.empty else df
        return repo.list_transactions(
            conn, person_id=person_id, account_id=account_id,
            limit=200000, date_asof=week_date,
        )

    for _, acc in banks.iterrows():
        acc_id = int(acc["id"])
        acc_ccy = str(acc.get("currency") or "EUR").upper()

        try:
            is_container = repo.is_bank_container(conn, acc_id)
        except Exception:
            is_container = False

        total_native = 0.0

        if is_container:
            subs = repo.list_bank_subaccounts(conn, acc_id)
            if subs is not None and not subs.empty:
                for _, s in subs.iterrows():
                    sub_id = int(s["sub_account_id"])
                    df = _get_tx(sub_id)
                    if df is not None and not df.empty:
                        total_native += _sum_cash_native(df)
        else:
            df = _get_tx(acc_id)
            if df is not None and not df.empty:
                total_native += _sum_cash_native(df)

        converted = market_history.convert_weekly(conn, float(total_native), acc_ccy, "EUR", week_date)
        if converted is None:
            _logger.warning(
                "_bank_cash_asof_eur: taux %s→EUR introuvable pour week=%s "
                "(compte %s exclu du snapshot — snapshot potentiellement incomplet)",
                acc_ccy, week_date, acc_id,
            )
            continue
        total_eur += converted

    return float(round(total_eur, 2))

# --------------------
# CASH BOURSE as-of
# --------------------
from services.bourse_analytics import _broker_cash_asof_native  # noqa: E402

def _bourse_cash_and_holdings_eur_asof(conn, person_id: int, week_date: str) -> tuple[float, float]:
    accounts = repo.list_accounts(conn, person_id=person_id)
    if accounts is None or accounts.empty:
        return 0.0, 0.0

    bourse_acc = accounts[accounts["account_type"].astype(str).str.upper().isin(["PEA", "CTO", "CRYPTO"])].copy()
    if bourse_acc.empty:
        return 0.0, 0.0

    acc_ids = [int(x) for x in bourse_acc["id"].tolist()]
    pos = positions.compute_positions_asof(conn, person_id, week_date, account_ids=acc_ids)

    cash_eur = 0.0
    for _, a in bourse_acc.iterrows():
        acc_id = int(a["id"])
        acc_ccy = str(a.get("currency") or "EUR").upper()
        tx = repo.list_transactions(conn, person_id=person_id, account_id=acc_id, limit=200000)
        if tx is None or tx.empty:
            continue
        df = tx.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df[df["date"] <= pd.to_datetime(week_date)]
        cash_native = _broker_cash_asof_native(df)
        converted_cash = market_history.convert_weekly(conn, cash_native, acc_ccy, "EUR", week_date)
        if converted_cash is None:
            _logger.warning(
                "_bourse_cash_and_holdings_eur_asof: taux %s→EUR introuvable pour week=%s "
                "(cash compte %s exclu du snapshot — snapshot potentiellement incomplet)",
                acc_ccy, week_date, acc_id,
            )
            continue
        cash_eur += converted_cash

    holdings_eur = 0.0
    if pos is not None and not pos.empty:
        for _, r in pos.iterrows():
            sym = str(r.get("symbol") or "").strip()
            qty = float(r.get("quantity") or 0.0)
            asset_ccy = str(r.get("asset_ccy") or "EUR").upper()
            if not sym or qty <= 0:
                continue
            px = market_history.get_price_asof(conn, sym, week_date)
            if px is None:
                continue
            value_native = qty * float(px)
            converted_holding = market_history.convert_weekly(conn, value_native, asset_ccy, "EUR", week_date)
            if converted_holding is None:
                _logger.warning(
                    "_bourse_cash_and_holdings_eur_asof: taux %s→EUR introuvable pour week=%s "
                    "(actif %s exclu du snapshot — snapshot potentiellement incomplet)",
                    asset_ccy, week_date, sym,
                )
                continue
            holdings_eur += converted_holding

    return float(round(cash_eur, 2)), float(round(holdings_eur, 2))

# --------------------
# PE cash + valo as-of
# --------------------
def _pe_cash_asof_eur(conn, person_id: int, week_date: str) -> float:
    if pe_cash_repo is None:
        return 0.0
    df = pe_cash_repo.list_pe_cash_transactions(conn, person_id=person_id)
    if df is None or df.empty:
        return 0.0
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"] if "date" in d.columns else None, errors="coerce")
    d = d.dropna(subset=["date"])
    d = d[d["date"] <= pd.to_datetime(week_date)]
    if d.empty:
        return 0.0
    d["tx_type"] = d["tx_type"].astype(str).str.upper()
    d["amount"] = pd.to_numeric(d["amount"] if "amount" in d.columns else 0.0, errors="coerce").fillna(0.0)

    def sign(t: str) -> float:
        if t == "DEPOSIT":
            return 1.0
        if t == "WITHDRAW":
            return -1.0
        return 1.0  # ADJUST: laisse le signe de amount

    total = float(d.apply(lambda r: float(r["amount"]) * sign(r["tx_type"]), axis=1).sum())
    return float(round(total, 2))  # supposé EUR

def _pe_value_asof_eur(conn, person_id: int, week_date: str) -> float:
    projects = pe_repo.list_pe_projects(conn, person_id=person_id)
    tx = pe_repo.list_pe_transactions(conn, person_id=person_id)
    if projects is None or projects.empty or tx is None or tx.empty:
        return 0.0

    d = tx.copy()
    d["date_dt"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date_dt"])
    d = d[d["date_dt"] <= pd.to_datetime(week_date)]

    p = projects.copy()
    p["exit_date_dt"] = pd.to_datetime(p.get("exit_date"), errors="coerce")

    total = 0.0
    for _, pr in p.iterrows():
        pid = int(pr["id"])
        status = str(pr.get("status") or "").upper()

        if status == "SORTI" and pd.notna(pr["exit_date_dt"]) and pr["exit_date_dt"] <= pd.to_datetime(week_date):
            continue

        dpr = d[d["project_id"] == pid].sort_values("date_dt")
        if dpr.empty:
            continue

        valos = dpr[dpr["tx_type"].astype(str).str.upper() == "VALO"]
        if not valos.empty:
            total += float(valos.iloc[-1]["amount"])
        else:
            invests = dpr[dpr["tx_type"].astype(str).str.upper() == "INVEST"]
            total += float(pd.to_numeric(invests["amount"], errors="coerce").fillna(0.0).sum())

    return float(round(total, 2))

# --------------------
# Entreprises as-of
# --------------------
def _enterprise_value_asof_eur(conn, person_id: int, week_date: str) -> float:
    # positions pour la personne (avec pct)
    pos = ent_repo.list_positions_for_person(conn, person_id=person_id)
    if pos is None or pos.empty:
        return 0.0

    total = 0.0
    wd = pd.to_datetime(week_date).strftime("%Y-%m-%d")
    eids = [int(eid) for eid in pos["enterprise_id"].unique()]

    if not eids:
        return 0.0

    placeholders = ",".join(["?"] * len(eids))
    q = f"""
        SELECT enterprise_id, valuation_eur, debt_eur
        FROM (
            SELECT enterprise_id, valuation_eur, debt_eur,
                   ROW_NUMBER() OVER(PARTITION BY enterprise_id ORDER BY effective_date DESC, id DESC) as rn
            FROM enterprise_history
            WHERE enterprise_id IN ({placeholders})
              AND effective_date <= ?
        )
        WHERE rn = 1
    """
    params = tuple(eids) + (wd,)
    
    rows = conn.execute(q, params).fetchall()
    hist_map = {}
    for r in rows:
        hist_map[int(r["enterprise_id"])] = (float(r["valuation_eur"] or 0.0), float(r["debt_eur"] or 0.0))

    for _, r in pos.iterrows():
        eid = int(r["enterprise_id"])
        pct = float(r.get("pct") or 0.0) / 100.0

        if eid in hist_map:
            valuation, debt = hist_map[eid]
        else:
            valuation = float(r.get("valuation_eur") or 0.0)
            debt = float(r.get("debt_eur") or 0.0)

        net = max(valuation - debt, 0.0)
        total += pct * net

    return float(round(total, 2))

# --------------------
# Immobilier as-of
# --------------------
def _immobilier_value_asof_eur(conn, person_id: int, week_date: str) -> float:
    # 1. Biens directs
    shares = immo_repo.list_positions_for_person(conn, person_id)
    total_direct = 0.0
    wd = pd.to_datetime(week_date).strftime("%Y-%m-%d")

    if shares is not None and not shares.empty:
        pids = [int(pid) for pid in shares["property_id"].unique()]
        if pids:
            placeholders = ",".join(["?"] * len(pids))
            q = f"""
                SELECT property_id, valuation_eur
                FROM (
                    SELECT property_id, valuation_eur,
                           ROW_NUMBER() OVER(PARTITION BY property_id ORDER BY effective_date DESC, id DESC) as rn
                    FROM immobilier_history
                    WHERE property_id IN ({placeholders})
                      AND effective_date <= ?
                )
                WHERE rn = 1
            """
            params = tuple(pids) + (wd,)
            rows = conn.execute(q, params).fetchall()
            hist_map = {int(r["property_id"]): float(r["valuation_eur"] or 0.0) for r in rows}

            for _, r in shares.iterrows():
                property_id = int(r["property_id"])
                pct = float(r.get("pct", 100.0)) / 100.0

                if property_id in hist_map:
                    valo = hist_map[property_id]
                else:
                    # Fallback to current valuation from immobiliers table
                    valo = float(r.get("valuation_eur") or 0.0)

                total_direct += valo * pct

    # 2. SCPI automatiques (via transactions)
    # On recalcule les positions à la date T
    scpi_tx = conn.execute(
        """
        SELECT
            a.id     AS asset_id,
            a.symbol,
            SUM(CASE
                WHEN t.type = 'ACHAT' THEN  t.quantity
                WHEN t.type = 'VENTE' THEN -t.quantity
                ELSE 0
            END) AS qty
        FROM transactions t
        JOIN assets a ON a.id = t.asset_id
        WHERE t.person_id = ?
          AND a.asset_type = 'scpi'
          AND t.date <= ?
        GROUP BY a.id
        HAVING qty > 0.0001
        """,
        (int(person_id), wd),
    ).fetchall()

    total_scpi = 0.0
    for s in scpi_tx:
        qty = float(s["qty"])
        sym = str(s["symbol"])
        px = market_history.get_price_asof(conn, sym, week_date)
        if px is not None:
            total_scpi += qty * float(px)

    return float(round(total_direct + total_scpi, 2))

# --------------------
# Crédit as-of
# --------------------
def _credits_remaining_asof(conn, person_id: int, week_date: str) -> float:
    df = list_credits_by_person(conn, person_id=person_id, only_active=True)
    if df is None or df.empty:
        return 0.0
    total = 0.0
    for _, c in df.iterrows():
        cid = int(c["id"])
        total += float(get_crd_a_date(conn, credit_id=cid, date_ref=week_date))
    return float(round(total, 2))

# --------------------
# Snapshot write
# --------------------
def upsert_weekly_snapshot(conn, person_id: int, week_date: str, mode: str, payload: dict) -> None:
    import math
    pn = float(payload.get("patrimoine_net", 0.0))
    if math.isnan(pn):
        import logging
        logging.getLogger(__name__).warning("Snapshot for person %s on %s has missing prices (NaN). Skipping insert.", person_id, week_date)
        return

    conn.execute(
        """
        INSERT INTO patrimoine_snapshots_weekly(
            person_id, week_date, created_at, mode,
            patrimoine_net, patrimoine_brut,
            liquidites_total, bank_cash, bourse_cash, pe_cash,
            bourse_holdings, pe_value, ent_value, immobilier_value,
            credits_remaining, notes
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(person_id, week_date) DO UPDATE SET
            created_at = excluded.created_at,
            mode = excluded.mode,
            patrimoine_net = excluded.patrimoine_net,
            patrimoine_brut = excluded.patrimoine_brut,
            liquidites_total = excluded.liquidites_total,
            bank_cash = excluded.bank_cash,
            bourse_cash = excluded.bourse_cash,
            pe_cash = excluded.pe_cash,
            bourse_holdings = excluded.bourse_holdings,
            pe_value = excluded.pe_value,
            ent_value = excluded.ent_value,
            immobilier_value = excluded.immobilier_value,
            credits_remaining = excluded.credits_remaining,
            notes = excluded.notes
        """,
        (
            int(person_id),
            str(week_date),
            _now_paris_iso(),
            str(mode),
            float(payload.get("patrimoine_net", 0.0)),
            float(payload.get("patrimoine_brut", 0.0)),
            float(payload.get("liquidites_total", 0.0)),
            float(payload.get("bank_cash", 0.0)),
            float(payload.get("bourse_cash", 0.0)),
            float(payload.get("pe_cash", 0.0)),
            float(payload.get("bourse_holdings", 0.0)),
            float(payload.get("pe_value", 0.0)),
            float(payload.get("ent_value", 0.0)),
            float(payload.get("immobilier_value", 0.0)),
            float(payload.get("credits_remaining", 0.0)),
            payload.get("notes"),
        ),
    )

def compute_weekly_snapshot_person(conn, person_id: int, week_date: str,
                                    tx_cache: "dict[int, pd.DataFrame] | None" = None) -> dict:
    bank_cash = _bank_cash_asof_eur(conn, person_id, week_date, tx_cache=tx_cache)
    bourse_cash, bourse_holdings = _bourse_cash_and_holdings_eur_asof(conn, person_id, week_date)
    pe_cash = _pe_cash_asof_eur(conn, person_id, week_date)
    pe_value = _pe_value_asof_eur(conn, person_id, week_date)
    ent_value = _enterprise_value_asof_eur(conn, person_id, week_date)
    immo_value = _immobilier_value_asof_eur(conn, person_id, week_date)
    credits_remaining = _credits_remaining_asof(conn, person_id, week_date)

    liquidites_total = float(round(bank_cash + bourse_cash + pe_cash, 2))
    patrimoine_brut = float(round(liquidites_total + bourse_holdings + pe_value + ent_value + immo_value, 2))
    patrimoine_net = float(round(patrimoine_brut - credits_remaining, 2))

    return {
        "bank_cash": bank_cash,
        "bourse_cash": bourse_cash,
        "pe_cash": pe_cash,
        "liquidites_total": liquidites_total,
        "bourse_holdings": bourse_holdings,
        "pe_value": pe_value,
        "ent_value": ent_value,
        "immobilier_value": immo_value,
        "credits_remaining": credits_remaining,
        "patrimoine_brut": patrimoine_brut,
        "patrimoine_net": patrimoine_net,
        "notes": "Weekly snapshot (as-of) rebuilt",
    }

def rebuild_snapshots_person(conn, person_id: int, lookback_days: int = 90) -> dict:
    end = market_history.week_start(_today_paris_date())
    start = end - dt.timedelta(days=int(lookback_days))
    weeks = _list_weeks(start, end)
    if not weeks:
        return {"did_run": False, "reason": "no_weeks"}

    _sync_person_market_data_for_weeks(conn, person_id, weeks[0], weeks[-1])

    # Cache des transactions bancaires par account_id (évite N*W requêtes SQL)
    bank_tx_cache: dict[int, pd.DataFrame] = {}
    accounts = repo.list_accounts(conn, person_id=person_id)
    if accounts is not None and not accounts.empty:
        bank_accs = accounts[accounts["account_type"].astype(str).str.upper() == "BANQUE"]
        for _, acc in bank_accs.iterrows():
            acc_id = int(acc["id"])
            try:
                is_container = repo.is_bank_container(conn, acc_id)
            except Exception:
                is_container = False
            if is_container:
                subs = repo.list_bank_subaccounts(conn, acc_id)
                if subs is not None and not subs.empty:
                    for _, s in subs.iterrows():
                        sub_id = int(s["sub_account_id"])
                        df = repo.list_transactions(conn, person_id=person_id, account_id=sub_id, limit=200000)
                        if df is not None and not df.empty:
                            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
                            bank_tx_cache[sub_id] = df
            else:
                df = repo.list_transactions(conn, person_id=person_id, account_id=acc_id, limit=200000)
                if df is not None and not df.empty:
                    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
                    bank_tx_cache[acc_id] = df

    n_ok = 0
    for wd in weeks:
        payload = compute_weekly_snapshot_person(conn, person_id, wd, tx_cache=bank_tx_cache)
        upsert_weekly_snapshot(conn, person_id, wd, mode="REBUILD", payload=payload)
        n_ok += 1

    conn.commit()
    return {"did_run": True, "n_weeks": len(weeks), "start": weeks[0], "end": weeks[-1], "n_ok": n_ok}


def rebuild_snapshots_person_missing_only(
    conn,
    person_id: int,
    lookback_days: int = 90,
    recalc_days: int = 0,
) -> dict:
    """
    Rebuild intelligent :
    - Crée UNIQUEMENT les snapshots weekly manquantes dans la fenêtre lookback_days
    - Optionnel: recalc les X derniers jours (fenêtre glissante) même si déjà présents
      (recalc_days=0 => pas de recalcul supplémentaire)
    """
    end = market_history.week_start(_today_paris_date())
    start = end - dt.timedelta(days=int(lookback_days))
    weeks = _list_weeks(start, end)
    if not weeks:
        return {"did_run": False, "reason": "no_weeks"}

    # 1) semaines existantes en base
    df_have = pd.read_sql_query(
        """
        SELECT week_date
        FROM patrimoine_snapshots_weekly
        WHERE person_id = ?
          AND week_date >= ?
          AND week_date <= ?
        """,
        conn,
        params=(int(person_id), str(weeks[0]), str(weeks[-1])),
    )
    have = set()
    if df_have is not None and not df_have.empty:
        have = set(df_have["week_date"].astype(str).tolist())

    missing = [wd for wd in weeks if wd not in have]

    # 2) fenêtre glissante optionnelle (recalc)
    recalc_weeks = []
    if int(recalc_days) > 0:
        recalc_start = end - dt.timedelta(days=int(recalc_days))
        recalc_weeks = _list_weeks(recalc_start, end)

    # 3) semaines à traiter = missing + recalc_weeks (unique)
    todo = sorted(set(missing + recalc_weeks))
    if not todo:
        return {"did_run": False, "reason": "nothing_to_do", "n_missing": 0, "n_recalc": 0}

    _sync_person_market_data_for_weeks(conn, person_id, weeks[0], weeks[-1])

    # 4) upsert uniquement semaines todo
    n_ok = 0
    for wd in todo:
        payload = compute_weekly_snapshot_person(conn, person_id, wd)
        upsert_weekly_snapshot(conn, person_id, wd, mode="REBUILD", payload=payload)
        n_ok += 1

    conn.commit()
    return {
        "did_run": True,
        "mode": "MISSING_ONLY",
        "person_id": int(person_id),
        "window_start": weeks[0],
        "window_end": weeks[-1],
        "n_missing": len(missing),
        "n_recalc": len(recalc_weeks),
        "n_done": len(todo),
        "n_ok": n_ok,
    }


def _get_last_snapshot_week_ts(conn, person_id: int) -> "pd.Timestamp | None":
    """Retourne la dernière week_date snapshot d'une personne (ou None)."""
    row = conn.execute(
        "SELECT MAX(week_date) AS d FROM patrimoine_snapshots_weekly WHERE person_id=?",
        (int(person_id),),
    ).fetchone()
    if not row:
        return None

    try:
        raw = row["d"]
    except (TypeError, KeyError):
        raw = row[0]

    if not raw:
        return None

    try:
        val = pd.to_datetime(raw, errors="coerce")
        return None if pd.isna(val) else val
    except Exception:
        return None


def rebuild_snapshots_person_from_last(
    conn,
    person_id: int,
    safety_weeks: int = 4,
    fallback_lookback_days: int = 90,
    cancel_check = None,
) -> dict:
    """
    Rebuild "quotidien" ultra rapide :
    - Cherche la dernière snapshot weekly existante pour la personne
    - Rebuild depuis cette date jusqu'à aujourd'hui
    - + recalcul d'une fenêtre de sécurité (safety_weeks) pour corriger les incohérences récentes
    - Si aucune snapshot n'existe, fallback sur lookback_days (90j)

    ⚠️ Ne casse pas l'existant : fonction additive.
    """
    end = market_history.week_start(_today_paris_date())

    # 1) Dernière snapshot existante
    last_week = _get_last_snapshot_week_ts(conn, person_id)

    # 2) Définir start
    if last_week is None:
        # aucun historique => fallback fenêtre 90j
        start = end - dt.timedelta(days=int(fallback_lookback_days))
        start = market_history.week_start(start)
        mode = "FROM_LAST_FALLBACK"
    else:
        # on recule d'une fenêtre de sécurité
        start = (last_week.date() - dt.timedelta(days=int(safety_weeks) * 7))
        start = market_history.week_start(start)
        mode = "FROM_LAST"

    weeks = _list_weeks(start, end)
    if not weeks:
        return {"did_run": False, "reason": "no_weeks", "mode": mode}

    _sync_person_market_data_for_weeks(conn, person_id, weeks[0], weeks[-1])

    # 4) Traitement :
    n_ok = 0
    for wd in weeks:
        if cancel_check and cancel_check():
            import logging
            logging.getLogger(__name__).info("Rebuild cancelled. Processed %d/%d weeks.", n_ok, len(weeks))
            break
        payload = compute_weekly_snapshot_person(conn, person_id, wd)
        upsert_weekly_snapshot(conn, person_id, wd, mode="REBUILD", payload=payload)
        n_ok += 1

    if not (cancel_check and cancel_check()):
        conn.commit()
    else:
        conn.rollback()

    return {
        "did_run": True,
        "mode": mode,
        "person_id": int(person_id),
        "start": weeks[0],
        "end": weeks[-1],
        "safety_weeks": int(safety_weeks),
        "fallback_lookback_days": int(fallback_lookback_days),
        "n_weeks": len(weeks),
        "n_ok": n_ok,
    }


def _ensure_rebuild_watermarks(conn) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS rebuild_watermarks (
      scope TEXT NOT NULL,          -- ex: 'WEEKLY_PERSON'
      entity_id INTEGER NOT NULL,   -- person_id
      last_tx_id INTEGER,
      last_tx_created_at TEXT,
      updated_at TEXT NOT NULL,
      PRIMARY KEY(scope, entity_id)
    );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rw_scope_entity ON rebuild_watermarks(scope, entity_id);")
    conn.commit()


def _get_person_watermark(conn, person_id: int) -> dict:
    _ensure_rebuild_watermarks(conn)
    row = conn.execute(
        "SELECT last_tx_id, last_tx_created_at FROM rebuild_watermarks WHERE scope=? AND entity_id=?",
        ("WEEKLY_PERSON", int(person_id)),
    ).fetchone()
    if not row:
        return {"last_tx_id": None, "last_tx_created_at": None}
    try:
        return {"last_tx_id": row["last_tx_id"], "last_tx_created_at": row["last_tx_created_at"]}
    except (TypeError, KeyError):
        return {"last_tx_id": row[0], "last_tx_created_at": row[1]}


def _set_person_watermark(conn, person_id: int, last_tx_id: int | None, last_tx_created_at: str | None) -> None:
    _ensure_rebuild_watermarks(conn)
    now = pd.Timestamp.now(tz="Europe/Paris").replace(microsecond=0).isoformat()
    conn.execute(
        """
        INSERT INTO rebuild_watermarks(scope, entity_id, last_tx_id, last_tx_created_at, updated_at)
        VALUES (?,?,?,?,?)
        ON CONFLICT(scope, entity_id) DO UPDATE SET
          last_tx_id = excluded.last_tx_id,
          last_tx_created_at = excluded.last_tx_created_at,
          updated_at = excluded.updated_at
        """,
        ("WEEKLY_PERSON", int(person_id), last_tx_id, last_tx_created_at, now),
    )
    conn.commit()


def rebuild_snapshots_person_backdated_aware(
    conn,
    person_id: int,
    safety_weeks: int = 4,
    fallback_lookback_days: int = 3650,
) -> dict:
    """
    B4: Rebuild backdated-aware (transactions ajoutées récemment mais avec date ancienne)
    - Detecte les NOUVELLES transactions depuis le dernier run (via id/created_at)
    - Trouve la date métier la plus ancienne parmi ces nouvelles transactions
    - Rebuild de la semaine correspondante (moins safety_weeks) jusqu'à aujourd'hui
    - Met à jour un watermark (last_tx_id / last_tx_created_at)

    Limite: si tu EDITES une transaction existante, on ne la détecte pas (pas d'updated_at).
    """
    _ensure_rebuild_watermarks(conn)

    # Seuil "aujourd'hui" en weekly
    end = market_history.week_start(_today_paris_date())

    # 1) watermark actuel
    wm = _get_person_watermark(conn, person_id)
    last_tx_id = wm.get("last_tx_id")

    # 2) récupérer les transactions "nouvelles"
    #    V1: basé sur ID (simple et fiable si tu n'update pas les IDs)
    if last_tx_id is None:
        df_new = pd.read_sql_query(
            """
            SELECT t.id, t.date, t.created_at, t.asset_id,
                   a.symbol AS asset_symbol
            FROM transactions t
            LEFT JOIN assets a ON a.id = t.asset_id
            WHERE t.person_id=?
            ORDER BY t.id ASC
            """,
            conn,
            params=(int(person_id),),
        )
    else:
        df_new = pd.read_sql_query(
            """
            SELECT t.id, t.date, t.created_at, t.asset_id,
                   a.symbol AS asset_symbol
            FROM transactions t
            LEFT JOIN assets a ON a.id = t.asset_id
            WHERE t.person_id=? AND t.id > ?
            ORDER BY t.id ASC
            """,
            conn,
            params=(int(person_id), int(last_tx_id)),
        )

    if df_new is None or df_new.empty:
        # Rien de nouveau => à jour
        return {"did_run": False, "mode": "BACKDATED_AWARE", "reason": "no_new_transactions", "person_id": int(person_id)}

    # 3) date métier la plus ancienne parmi les nouvelles tx
    df_new["date"] = pd.to_datetime(df_new["date"], errors="coerce")
    df_new = df_new.dropna(subset=["date"])
    if df_new.empty:
        return {"did_run": False, "mode": "BACKDATED_AWARE", "reason": "new_transactions_no_valid_date", "person_id": int(person_id)}

    min_date = df_new["date"].min().date()

    # 4) start = semaine(min_date) - safety_weeks
    start = market_history.week_start(min_date - dt.timedelta(days=int(safety_weeks) * 7))

    # garde-fou : si ça remonte trop loin, on limite (mais on te le dit)
    floor = end - dt.timedelta(days=int(fallback_lookback_days))
    floor = market_history.week_start(floor)
    truncated = False
    if start < floor:
        start = floor
        truncated = True

    weeks = _list_weeks(start, end)
    if not weeks:
        return {"did_run": False, "mode": "BACKDATED_AWARE", "reason": "no_weeks", "person_id": int(person_id)}

    _sync_person_market_data_for_weeks(conn, person_id, weeks[0], weeks[-1])

    # 6) Recalc weeks
    n_ok = 0
    for wd in weeks:
        payload = compute_weekly_snapshot_person(conn, person_id, wd)
        upsert_weekly_snapshot(conn, person_id, wd, mode="REBUILD", payload=payload)
        n_ok += 1

    conn.commit()

    # 7) Update watermark vers le MAX ID existant
    max_row = conn.execute(
        "SELECT MAX(id) AS max_id, MAX(created_at) AS max_created FROM transactions WHERE person_id=?",
        (int(person_id),),
    ).fetchone()
    _set_person_watermark(
        conn,
        person_id,
        (int(max_row[0]) if max_row and max_row[0] is not None else None),
        (str(max_row[1]) if max_row and max_row[1] is not None else None),
    )

    return {
        "did_run": True,
        "mode": "BACKDATED_AWARE",
        "person_id": int(person_id),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "n_weeks": len(weeks),
        "n_ok": n_ok,
        "truncated": truncated
    }


# ─────────────────────────────────────────────────────────────────────────────
# Lecture de la série hebdomadaire personne (SSOT)
# ─────────────────────────────────────────────────────────────────────────────

PERSON_WEEKLY_COLUMNS = [
    "week_date",
    "patrimoine_net",
    "patrimoine_brut",
    "liquidites_total",
    "bourse_holdings",
    "pe_value",
    "ent_value",
    "immobilier_value",
    "credits_remaining",
]


def _snapshot_row_to_dict(
    row,
    *,
    person_id: int,
    week_str: str | None = None,
    warn_invalid_fields: bool = False,
) -> dict:
    """Convertit une row snapshot SQLite en payload métier normalisé."""
    def _val(key: str) -> float:
        try:
            v = row[key]
            return float(v) if v is not None else 0.0
        except (KeyError, IndexError, TypeError, ValueError):
            if warn_invalid_fields:
                _logger.warning(
                    "get_person_snapshot_at_week: colonne '%s' absente ou invalide "
                    "pour person_id=%s semaine=%s", key, person_id, week_str,
                )
            return 0.0

    return {
        "week_date":         str(row["week_date"]) if row["week_date"] else None,
        "patrimoine_net":    _val("patrimoine_net"),
        "patrimoine_brut":   _val("patrimoine_brut"),
        "liquidites_total":  _val("liquidites_total"),
        "bourse_holdings":   _val("bourse_holdings"),
        "immobilier_value":  _val("immobilier_value"),
        "pe_value":          _val("pe_value"),
        "ent_value":         _val("ent_value"),
        "credits_remaining": _val("credits_remaining"),
    }


def get_person_weekly_series(conn, person_id: int) -> pd.DataFrame:
    """
    Point d'entrée officiel (SSOT) pour lire la série hebdomadaire
    de patrimoine d'une personne.

    Symétrique à ``family_snapshots.get_family_weekly_series``.

    Retourne un DataFrame avec les colonnes :
        week_date           datetime64
        patrimoine_net      float
        patrimoine_brut     float
        liquidites_total    float
        bourse_holdings     float
        pe_value            float
        ent_value           float
        immobilier_value    float
        credits_remaining   float

    Les lignes sont triées par ``week_date`` croissant.
    Retourne un DataFrame vide (avec les colonnes) si aucun snapshot.
    """
    empty = pd.DataFrame(columns=PERSON_WEEKLY_COLUMNS)

    try:
        rows = conn.execute(
            """
            SELECT week_date,
                   patrimoine_net,
                   patrimoine_brut,
                   liquidites_total,
                   bourse_holdings,
                   pe_value,
                   ent_value,
                   immobilier_value,
                   credits_remaining
            FROM patrimoine_snapshots_weekly
            WHERE person_id = ?
            ORDER BY week_date ASC
            """,
            (int(person_id),),
        ).fetchall()
        df = pd.DataFrame(rows, columns=PERSON_WEEKLY_COLUMNS) if rows else pd.DataFrame(columns=PERSON_WEEKLY_COLUMNS)
    except Exception:
        _logger.error(
            "get_person_weekly_series: erreur lecture snapshots pour person_id=%s",
            person_id, exc_info=True,
        )
        return empty

    if df is None or df.empty:
        _logger.info(
            "get_person_weekly_series: aucun snapshot pour person_id=%s", person_id,
        )
        return empty

    # Normalisation (même logique que family_snapshots._normalize_family_weekly_series)
    df["week_date"] = pd.to_datetime(df["week_date"], errors="coerce")
    n_before = len(df)
    df = df.dropna(subset=["week_date"]).sort_values("week_date")
    n_dropped = n_before - len(df)
    if n_dropped > 0:
        _logger.warning(
            "get_person_weekly_series: %d ligne(s) ignorée(s) (date invalide) "
            "pour person_id=%s", n_dropped, person_id,
        )

    for col in PERSON_WEEKLY_COLUMNS:
        if col == "week_date":
            continue
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return df[PERSON_WEEKLY_COLUMNS].reset_index(drop=True)


def get_latest_person_snapshot(conn, person_id: int) -> dict | None:
    """
    Retourne le dernier snapshot hebdomadaire d'une personne.

    Point d'entrée officiel pour obtenir l'état patrimonial le plus
    récent d'une personne sans charger toute la série.

    Retourne un dictionnaire avec les clés :
        week_date           str   (format YYYY-MM-DD)
        patrimoine_net      float
        patrimoine_brut     float
        liquidites_total    float
        bourse_holdings     float
        pe_value            float
        ent_value           float
        immobilier_value    float
        credits_remaining   float

    Retourne None si aucun snapshot n'existe.
    """
    if person_id is None:
        _logger.warning("get_latest_person_snapshot: person_id est None")
        return None

    try:
        row = conn.execute(
            """
            SELECT week_date, patrimoine_net, patrimoine_brut,
                   liquidites_total, bourse_holdings, immobilier_value,
                   pe_value, ent_value, credits_remaining
            FROM patrimoine_snapshots_weekly
            WHERE person_id = ?
            ORDER BY week_date DESC, id DESC
            LIMIT 1
            """,
            (int(person_id),),
        ).fetchone()
    except Exception:
        _logger.error(
            "get_latest_person_snapshot: erreur lecture pour person_id=%s",
            person_id, exc_info=True,
        )
        return None

    if row is None:
        _logger.info(
            "get_latest_person_snapshot: aucun snapshot pour person_id=%s",
            person_id,
        )
        return None

    return _snapshot_row_to_dict(row, person_id=int(person_id))


def get_person_snapshot_at_week(
    conn,
    person_id: int,
    week_date: "pd.Timestamp | str",
) -> "dict | None":
    """
    Retourne le snapshot hebdomadaire d'une personne à une semaine précise.

    Symétrique à ``get_latest_person_snapshot`` mais filtré sur une date donnée
    plutôt que sur le dernier enregistrement.

    Paramètres
    ----------
    week_date : pd.Timestamp ou str (YYYY-MM-DD)
        La semaine exacte souhaitée.

    Retourne un dictionnaire avec les mêmes clés que ``get_latest_person_snapshot``:
        week_date           str   (format YYYY-MM-DD)
        patrimoine_net      float
        patrimoine_brut     float
        liquidites_total    float
        bourse_holdings     float
        pe_value            float
        ent_value           float
        immobilier_value    float
        credits_remaining   float

    Retourne None si aucun snapshot n'existe pour cette semaine.
    """
    if person_id is None:
        _logger.warning("get_person_snapshot_at_week: person_id est None")
        return None

    # Normalisation de la date en chaîne YYYY-MM-DD
    try:
        if isinstance(week_date, str):
            week_str = week_date
        else:
            week_str = pd.Timestamp(week_date).strftime("%Y-%m-%d")
    except Exception:
        _logger.warning(
            "get_person_snapshot_at_week: week_date invalide (%r) pour person_id=%s",
            week_date, person_id,
        )
        return None

    try:
        row = conn.execute(
            """
            SELECT week_date, patrimoine_net, patrimoine_brut,
                   liquidites_total, bourse_holdings, immobilier_value,
                   pe_value, ent_value, credits_remaining
            FROM patrimoine_snapshots_weekly
            WHERE person_id = ? AND week_date = ?
            LIMIT 1
            """,
            (int(person_id), week_str),
        ).fetchone()
    except Exception:
        _logger.error(
            "get_person_snapshot_at_week: erreur lecture pour person_id=%s week_date=%s",
            person_id, week_str, exc_info=True,
        )
        return None

    if row is None:
        _logger.info(
            "get_person_snapshot_at_week: aucun snapshot pour person_id=%s semaine=%s",
            person_id, week_str,
        )
        return None

    return _snapshot_row_to_dict(
        row,
        person_id=int(person_id),
        week_str=week_str,
        warn_invalid_fields=True,
    )
