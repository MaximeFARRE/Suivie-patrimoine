"""
Façade de compatibilité pour les snapshots hebdomadaires personne.

API publique inchangée : les fonctions historiques restent importables depuis
`services.snapshots`, mais l'implémentation est découpée en sous-modules.
"""

from services.snapshots_compute import (
    compute_weekly_snapshot_person,
    upsert_weekly_snapshot,
)
from services.snapshots_read import (
    PERSON_WEEKLY_COLUMNS,
    get_latest_person_snapshot,
    get_latest_snapshot_notes,
    get_person_snapshot_at_week,
    get_person_weekly_series,
)
from services.snapshots_rebuild import (
    get_first_transaction_date,
    has_new_transactions_since_person_watermark,
    rebuild_snapshots_person,
    rebuild_snapshots_person_backdated_aware,
    rebuild_snapshots_person_from_last,
    rebuild_snapshots_person_full_history,
    rebuild_snapshots_person_missing_only,
)

__all__ = [
    "PERSON_WEEKLY_COLUMNS",
    "compute_weekly_snapshot_person",
    "get_latest_person_snapshot",
    "get_latest_snapshot_notes",
    "get_person_snapshot_at_week",
    "get_person_weekly_series",
    "rebuild_snapshots_person",
    "rebuild_snapshots_person_backdated_aware",
    "rebuild_snapshots_person_from_last",
    "rebuild_snapshots_person_missing_only",
    "rebuild_snapshots_person_full_history",
    "get_first_transaction_date",
    "has_new_transactions_since_person_watermark",
    "upsert_weekly_snapshot",
]
