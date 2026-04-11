"""Tests pour services/import_lookup_service."""
import pytest
from services import import_lookup_service as lookup


def test_get_person_id_by_name_found(conn):
    conn.execute("INSERT INTO people(name) VALUES ('Alice')")
    conn.commit()
    pid = lookup.get_person_id_by_name(conn, "Alice")
    assert isinstance(pid, int)
    assert pid > 0


def test_get_person_id_by_name_not_found(conn):
    result = lookup.get_person_id_by_name(conn, "Inconnu")
    assert result is None


def test_get_person_id_by_name_exact_match(conn):
    conn.execute("INSERT INTO people(name) VALUES ('Bob')")
    conn.execute("INSERT INTO people(name) VALUES ('Bobby')")
    conn.commit()
    pid_bob = lookup.get_person_id_by_name(conn, "Bob")
    pid_bobby = lookup.get_person_id_by_name(conn, "Bobby")
    assert pid_bob != pid_bobby


def test_list_accounts_by_types_filters_correctly(conn):
    conn.execute("INSERT INTO people(name) VALUES ('Test')")
    conn.execute("INSERT INTO accounts(person_id, name, account_type, currency) VALUES (1, 'PEA Bourse', 'PEA', 'EUR')")
    conn.execute("INSERT INTO accounts(person_id, name, account_type, currency) VALUES (1, 'Banque Principale', 'BANQUE', 'EUR')")
    conn.execute("INSERT INTO accounts(person_id, name, account_type, currency) VALUES (1, 'CTO World', 'CTO', 'EUR')")
    conn.commit()

    bourse = lookup.list_accounts_by_types(conn, 1, ["PEA", "CTO"])
    assert len(bourse) == 2
    types = {a["account_type"] for a in bourse}
    assert types == {"PEA", "CTO"}


def test_list_accounts_by_types_empty_if_none_match(conn):
    conn.execute("INSERT INTO people(name) VALUES ('Test')")
    conn.execute("INSERT INTO accounts(person_id, name, account_type, currency) VALUES (1, 'Banque', 'BANQUE', 'EUR')")
    conn.commit()

    result = lookup.list_accounts_by_types(conn, 1, ["CREDIT"])
    assert result == []


def test_list_accounts_by_types_returns_dicts_with_expected_keys(conn):
    conn.execute("INSERT INTO people(name) VALUES ('Test')")
    conn.execute("INSERT INTO accounts(person_id, name, account_type, currency) VALUES (1, 'Crédit Immo', 'CREDIT', 'EUR')")
    conn.commit()

    result = lookup.list_accounts_by_types(conn, 1, ["CREDIT"])
    assert len(result) == 1
    keys = set(result[0].keys())
    assert {"id", "name", "account_type"}.issubset(keys)
