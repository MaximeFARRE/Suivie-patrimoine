# services/pe_cash_repository.py
import pandas as pd

def list_pe_cash_transactions(conn, person_id: int) -> pd.DataFrame:
    q = """
    SELECT id, person_id, platform, date, tx_type, amount, note
    FROM pe_cash_transactions
    WHERE person_id = ?
    ORDER BY date DESC, id DESC
    """
    return pd.read_sql_query(q, conn, params=(person_id,))

def add_pe_cash_transaction(
    conn,
    person_id: int,
    platform: str,
    date: str,
    tx_type: str,   # ADJUST | DEPOSIT | WITHDRAW
    amount: float,
    note: str | None = None,
):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO pe_cash_transactions (person_id, platform, date, tx_type, amount, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (person_id, platform.strip(), date, tx_type, float(amount), (note or None)),
    )
    conn.commit()
