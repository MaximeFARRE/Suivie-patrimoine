import streamlit as st

from utils.cache import cached_conn
from services.imports import import_wide_csv_to_monthly_table, import_bankin_csv

PEOPLE = ["Papa", "Maman", "Maxime", "Valentin"]

st.set_page_config(page_title="Import", layout="wide")
st.title("Importer des données (CSV)")

conn = cached_conn()

person = st.selectbox("Personne", PEOPLE)

mode = st.selectbox(
    "Type d'import",
    ["Dépenses (mensuel)", "Revenus (mensuel)", "Bankin (transactions)"]
)

uploaded = st.file_uploader("Choisir un CSV", type=["csv"])

# --- Dépenses / Revenus (format tableur mensuel "wide") ---
if mode in ("Dépenses (mensuel)", "Revenus (mensuel)"):
    table = "depenses" if mode.startswith("Dépenses") else "revenus"

    st.caption("Format attendu : Date | Catégories... | Total (Total ignoré).")
    delete_existing = st.checkbox("Remplacer les données existantes (cette personne)", value=True)

    if uploaded and st.button("Importer"):
        try:
            res = import_wide_csv_to_monthly_table(
                conn,
                table=table,
                person_name=person,
                file=uploaded,
                delete_existing=delete_existing,
            )
            st.success(f"Import OK ✅ {res['nb_lignes']} lignes insérées dans {res['table']}")
            st.write("Mois importés :", res["mois"])
            st.write("Catégories détectées :", res["categories"])
        except Exception as e:
            st.error(str(e))


# --- Bankin (format export transactions) ---
if mode == "Bankin (transactions)":
    st.caption("Importe le CSV Bankin dans la table transactions (et optionnellement remplit depenses/revenus).")

    also_fill = st.checkbox("Créer aussi les totaux mensuels (depenses/revenus)", value=True)
    purge_tx = st.checkbox("Supprimer les anciennes transactions de cette personne", value=False)

    if uploaded and st.button("Importer Bankin"):
        try:
            res = import_bankin_csv(
                conn,
                person_name=person,
                file=uploaded,
                also_fill_monthly_tables=also_fill,
                purge_existing_transactions=purge_tx,
            )
            st.success(f"Import Bankin OK ✅ {res['transactions_inserted']} transactions ajoutées")
            st.write("Mois dépenses :", res["months_depenses"])
            st.write("Mois revenus :", res["months_revenus"])
            st.write("Catégories dépenses :", res["dep_categories"])
            st.write("Catégories revenus :", res["rev_categories"])
        except Exception as e:
            st.error(str(e))
