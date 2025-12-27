# services/private_equity.py
import pandas as pd

TX_INVEST = "INVEST"
TX_DISTRIB = "DISTRIB"
TX_FEES = "FEES"
TX_VALO = "VALO"
TX_VENTE = "VENTE"

STATUS_EN_COURS = "EN_COURS"
STATUS_SORTI = "SORTI"
STATUS_FAILLITE = "FAILLITE"

def _parse_date(s: str) -> pd.Timestamp:
    return pd.to_datetime(s, errors="coerce")

def build_pe_positions(projects: pd.DataFrame, tx: pd.DataFrame) -> pd.DataFrame:
    """
    Retourne une table 'positions' par projet :
    investi, cash_out, last_valo, pnl, moic, entry_date, exit_date_effective, holding_days...
    """
    if projects.empty:
        return projects.copy()

    if tx.empty:
        # Aucun mouvement : on renvoie les projets avec zéros
        out = projects.copy()
        out["invested"] = 0.0
        out["cash_out"] = 0.0
        out["last_valo"] = 0.0
        out["pnl"] = 0.0
        out["moic"] = None
        out["entry_date"] = None
        out["exit_date_effective"] = out.get("exit_date", None)
        out["holding_days"] = None
        return out

    tx2 = tx.copy()
    tx2["date_dt"] = pd.to_datetime(tx2["date"], errors="coerce")

    # Investi = somme INVEST
    invested = tx2[tx2["tx_type"] == TX_INVEST].groupby("project_id")["amount"].sum()

    # Frais = somme FEES
    fees = tx2[tx2["tx_type"] == TX_FEES].groupby("project_id")["amount"].sum()

    # Cash-out = DISTRIB + VENTE
    cash_out = tx2[tx2["tx_type"].isin([TX_DISTRIB, TX_VENTE])].groupby("project_id")["amount"].sum()

    # Last valo = dernière tx VALO (amount = valeur totale snapshot)
    valo = tx2[tx2["tx_type"] == TX_VALO].sort_values("date_dt").groupby("project_id").tail(1).set_index("project_id")["amount"]

    # Entry date = première INVEST
    entry = tx2[tx2["tx_type"] == TX_INVEST].sort_values("date_dt").groupby("project_id").head(1).set_index("project_id")["date_dt"]

    # Exit effective : si projet sort i -> exit_date si dispo sinon dernière VENTE
    last_sale = tx2[tx2["tx_type"] == TX_VENTE].sort_values("date_dt").groupby("project_id").tail(1).set_index("project_id")["date_dt"]

    out = projects.copy()
    out["invested"] = out["id"].map(invested).fillna(0.0)
    out["fees"] = out["id"].map(fees).fillna(0.0)
    out["cash_out"] = out["id"].map(cash_out).fillna(0.0)
    out["last_valo"] = out["id"].map(valo).fillna(0.0)
    out["has_valo"] = out["id"].map(valo).notna()
    out["value_used"] = out["last_valo"]
    out.loc[~out["has_valo"], "value_used"] = out.loc[~out["has_valo"], "invested"]
    out["entry_date"] = out["id"].map(entry)

    # exit date effective
    exit_date_dt = pd.to_datetime(out["exit_date"], errors="coerce") if "exit_date" in out.columns else pd.NaT
    out["exit_date_effective"] = exit_date_dt
    out.loc[out["exit_date_effective"].isna(), "exit_date_effective"] = out["id"].map(last_sale)

    # holding days (si entry ok)
    today = pd.Timestamp.today().normalize()
    end = out["exit_date_effective"].fillna(today)
    out["holding_days"] = (end - out["entry_date"]).dt.days

    # PNL/MOIC
    out["pnl"] = (out["cash_out"] + out["value_used"]) - (out["invested"] + out["fees"])

    den = (out["invested"] + out["fees"])
    out["moic"] = None
    mask = den > 0
    out.loc[mask, "moic"] = (out.loc[mask, "cash_out"] + out.loc[mask, "value_used"]) / den[mask]


    return out

def compute_pe_kpis(positions: pd.DataFrame) -> dict:
    if positions.empty:
        return {
            "invested": 0.0, "cash_out": 0.0, "value": 0.0, "pnl": 0.0, "moic": None,
            "n_total": 0, "n_en_cours": 0, "n_sortis": 0, "n_faillite": 0,
            "n_en_perte": 0, "n_en_gain": 0,
            "success_rate": None,
            "avg_holding_days": None, "avg_exit_days": None,
        }

    fees = float(positions["fees"].sum()) if "fees" in positions.columns else 0.0

    invested = float(positions["invested"].sum())
    cash_out = float(positions["cash_out"].sum())
    value = float(positions["value_used"].sum())
    pnl = float((cash_out + value) - (invested + fees))
    den = invested + fees
    moic = (cash_out + value) / den if den > 0 else None

    n_total = int(len(positions))
    n_en_cours = int((positions["status"] == "EN_COURS").sum())
    n_sortis = int((positions["status"] == "SORTI").sum())
    n_faillite = int((positions["status"] == "FAILLITE").sum())

    # En gain/perte : nécessite valo ou sortie ; mais on calcule quand même
    n_en_gain = int((positions["pnl"] > 0).sum())
    n_en_perte = int((positions["pnl"] < 0).sum())

    # Taux réussite : parmi les SORTI, combien en gain
    exited = positions[positions["status"] == "SORTI"]
    if len(exited) > 0:
        success_rate = float((exited["pnl"] > 0).mean())
        avg_exit_days = float(exited["holding_days"].dropna().mean()) if exited["holding_days"].notna().any() else None
    else:
        success_rate = None
        avg_exit_days = None

    avg_holding_days = float(positions["holding_days"].dropna().mean()) if positions["holding_days"].notna().any() else None

    return {
        "invested": invested,
        "cash_out": cash_out,
        "value": value,
        "pnl": pnl,
        "fees": fees,
        "moic": moic,
        "n_total": n_total,
        "n_en_cours": n_en_cours,
        "n_sortis": n_sortis,
        "n_faillite": n_faillite,
        "n_en_perte": n_en_perte,
        "n_en_gain": n_en_gain,
        "success_rate": success_rate,
        "avg_holding_days": avg_holding_days,
        "avg_exit_days": avg_exit_days,
    }
