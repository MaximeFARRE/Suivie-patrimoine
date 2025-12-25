import streamlit as st
import pandas as pd
from datetime import date

from services.depenses_repository import (
    ajouter_depense,
    depenses_du_mois,
    derniere_depense,
    supprimer_depense_par_id,
)   

# Catégories simples (comme ton Google Sheet)
CATEGORIES_DEPENSES = [
    "Loyer",
    "Remboursement crédit",
    "Nourriture",
    "Éducation",
    "Transports",
    "Autres",
]

MOIS_FR = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]


def onglet_depenses(conn, person_id: int, key_prefix: str = "depenses"):
    st.subheader("Dépenses")

    # ----------------------------
    # Sélection mois (Année + Mois)
    # ----------------------------
    today = date.today()

    col_a, col_m = st.columns(2)

    with col_a:
        annees = list(range(today.year - 5, today.year + 1))
        annee = st.selectbox(
            "Année",
            options=annees,
            index=len(annees) - 1,  # année actuelle
            key=f"{key_prefix}_annee",
        )

    with col_m:
        mois_nom = st.selectbox(
            "Mois",
            options=MOIS_FR,
            index=today.month - 1,
            key=f"{key_prefix}_mois",
        )

    mois_num = MOIS_FR.index(mois_nom) + 1
    mois = f"{annee:04d}-{mois_num:02d}-01"  # format stable pour la DB

    st.caption(f"Mois sélectionné : {mois_nom} {annee}")

    st.divider()

    # ----------------------------
    # Scanner (avec callback => pas d'erreur session_state)
    # ----------------------------
    st.markdown("### Saisie rapide (mode scanner)")

    categorie_active = st.selectbox(
        "Catégorie active",
        CATEGORIES_DEPENSES,
        key=f"{key_prefix}_cat",
    )

    with st.form(key=f"{key_prefix}_form", clear_on_submit=True):
        montant_str = st.text_input(
            "Montant",
            placeholder="Ex : 4, 12.5, 23",
            key=f"{key_prefix}_montant_txt",
        )

        ajouter = st.form_submit_button("Ajouter ➕")

        if ajouter:
            try:
                montant = float(montant_str.replace(",", "."))
            except ValueError:
                st.error("Montant invalide")
                st.stop()

            if montant <= 0:
                st.error("Montant invalide")
                st.stop()

            ajouter_depense(
                conn,
                person_id,
                mois,
                categorie_active,
                montant,
            )

    # Bouton Annuler la dernière saisie
    col_undo1, col_undo2 = st.columns([2, 1])
    with col_undo2:
        if st.button("Annuler la dernière saisie ↩️", use_container_width=True, key=f"{key_prefix}_undo"):
            last = derniere_depense(conn, person_id, mois)
            if last is None:
                st.warning("Rien à annuler pour ce mois.")
            else:
                depense_id, cat, montant = last
                supprimer_depense_par_id(conn, depense_id)
                st.success(f"Annulé : {cat} — {montant:.2f} €")
                st.rerun()

    # ----------------------------
    # Synthèse (catégorie -> somme)
    # ----------------------------
    st.markdown("### Synthèse du mois")

    df = depenses_du_mois(conn, person_id, mois)

    if df.empty:
        st.info("Aucune dépense pour ce mois.")
        return

    resume = (
        df.groupby("categorie")["montant"]
        .sum()
        .reindex(CATEGORIES_DEPENSES, fill_value=0.0)
        .reset_index()
    )
    resume.columns = ["Catégorie", "Total (€)"]

    total = float(resume["Total (€)"].sum())

    st.dataframe(resume, use_container_width=True)
    st.markdown(f"### Total du mois : **{total:.2f} €**")
