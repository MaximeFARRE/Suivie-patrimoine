"""
Utilitaires bas niveau partagés par tous les services.
Pas de dépendances internes — importer librement.
"""

from __future__ import annotations

from typing import Any


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convertit en float avec fallback sûr."""
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def row_get(row: Any, key: str, idx: int = 0):
    """Accès tolérant à une row (dict-like ou tuple-like)."""
    if row is None:
        return None
    try:
        return row[key]
    except Exception:
        try:
            return row[idx]
        except Exception:
            return None


def fmt_amount(value: Any) -> str:
    """Formate un montant avec séparateur d'espace et 2 décimales."""
    num = safe_float(value, 0.0)
    return f"{num:,.2f}".replace(",", " ")


def get_asset_type_by_id(conn: Any, asset_ids: list[int]) -> dict[int, str]:
    """Retourne un mapping {asset_id: asset_type} pour les ids fournis."""
    if not asset_ids:
        return {}
    ids = sorted({int(aid) for aid in asset_ids if aid is not None})
    if not ids:
        return {}
    qmarks = ",".join(["?"] * len(ids))
    rows = conn.execute(
        f"SELECT id, asset_type FROM assets WHERE id IN ({qmarks})",
        tuple(ids),
    ).fetchall()
    out: dict[int, str] = {}
    for row in rows:
        try:
            rid = int(row["id"])
            at = str(row["asset_type"] or "autre")
        except Exception:
            rid = int(row[0])
            at = str(row[1] or "autre")
        out[rid] = at
    return out
