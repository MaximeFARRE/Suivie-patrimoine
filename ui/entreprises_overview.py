import streamlit as st
import pandas as pd
import altair as alt

from services import repositories as repo
from services import entreprises_repository as ent_repo


def _fmt_eur(x: float) -> str:
    try:
        return f"{float(x):,.2f} €".replace(",", " ")
    except Exception:
        return "0,00 €"


def afficher_entreprises_overview(conn, person_id: int, key_prefix: str = "ent"):
    st.subheader("🏢 Entreprises (non cotées)")
    st.caption("Valorisation partagée : si quelqu’un modifie la valo, tout le monde voit la mise à jour.")

    people = repo.list_people(conn)
    entreprises = ent_repo.list_enterprises(conn)
    
    # ---------- NOUVELLE SECTION : Récap global non coté (perso) ----------
    st.markdown("## Récap global (entreprises non cotées)")

    positions = ent_repo.list_positions_for_person(conn, person_id)

    if positions.empty:
        st.info("Aucune participation non cotée enregistrée pour cette personne.")
    else:
        # Valeur actuelle nette par entreprise (valo - dette) * %
        positions = positions.copy()
        positions["net_enterprise"] = (positions["valuation_eur"].fillna(0) - positions["debt_eur"].fillna(0))
        positions["value_now"] = positions["net_enterprise"] * positions["pct"].fillna(0) / 100.0
        positions["initial"] = positions["initial_invest_eur"].fillna(0)
        positions["cca"] = positions["cca_eur"].fillna(0)

        value_total = float(positions["value_now"].sum())
        initial_total = float(positions["initial"].sum())
        cca_total = float(positions["cca"].sum())

        perf_total_eur = value_total - initial_total
        perf_total_pct = (perf_total_eur / initial_total * 100.0) if initial_total > 0 else None

        # CAGR portefeuille (simple) : depuis la date la plus ancienne "start_at"
        positions["start_at_dt"] = pd.to_datetime(positions["start_at"], errors="coerce")
        start_dt = positions["start_at_dt"].min()
        cagr_port = None
        if pd.notna(start_dt) and initial_total > 0 and value_total > 0:
            years = (pd.Timestamp.now() - start_dt).days / 365.25
            if years > 0:
                cagr_port = (value_total / initial_total) ** (1 / years) - 1

        k1, k2, k3 = st.columns(3)
        k1.metric("Valeur actuelle totale", _fmt_eur(value_total))
        k2.metric("Investissement initial total", _fmt_eur(initial_total))
        if perf_total_pct is None:
            k3.metric("Perf totale (sur initial)", "—")
        else:
            k3.metric("Perf totale (sur initial)", f"{_fmt_eur(perf_total_eur)} ({perf_total_pct:.1f}%)")

        k4, k5, k6 = st.columns(3)
        k4.metric("CCA total", _fmt_eur(cca_total))
        if cagr_port is None:
            k5.metric("CAGR portefeuille", "—")
        else:
            k5.metric("CAGR portefeuille", f"{cagr_port*100:.1f}% / an")
        k6.metric("Nombre d’entreprises", str(len(positions)))

        st.caption("Perf et CAGR calculés uniquement sur l’investissement initial (CCA ignoré).")

        # Répartition (allocation)
        st.markdown("### Répartition (par valeur actuelle)")
        alloc = positions[["enterprise_name", "value_now", "initial", "cca"]].copy()
        total = float(alloc["value_now"].sum())
        alloc["allocation_%"] = (alloc["value_now"] / total * 100.0) if total > 0 else 0.0
        alloc = alloc.sort_values("value_now", ascending=False)

        # Petit graphe barres + tableau recap
        st.bar_chart(data=alloc.set_index("enterprise_name")["allocation_%"], use_container_width=True)

        alloc["Perf initial (€)"] = alloc["value_now"] - alloc["initial"]
        alloc["Perf initial (%)"] = alloc.apply(lambda r: (r["Perf initial (€)"] / r["initial"] * 100.0) if r["initial"] > 0 else None, axis=1)

        st.dataframe(
            alloc.rename(
                columns={
                    "enterprise_name": "Entreprise",
                    "value_now": "Valeur actuelle (€)",
                    "initial": "Invest initial (€)",
                    "cca": "CCA (€)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()


    # ---------- SECTION A : Sélection + Actions ----------
    st.markdown("## Sélection & actions")

    if entreprises.empty:
        st.info("Aucune entreprise pour le moment. Ajoute la première ci-dessous.")
        selected_id = None
    else:
        noms = entreprises["name"].tolist()
        nom_sel = st.selectbox("Choisir une entreprise", noms, key=f"{key_prefix}_sel")
        selected_id = int(entreprises.loc[entreprises["name"] == nom_sel, "id"].iloc[0])

        row = ent_repo.get_enterprise(conn, selected_id)
        valo = float(row["valuation_eur"] or 0)
        debt = float(row["debt_eur"] or 0)
        net = valo - debt

        # --- Données perso sur cette entreprise ---
        shares_df = ent_repo.list_shares(conn, selected_id)
        pct_me = 0.0
        my_initial = 0.0
        my_cca = 0.0

        if not shares_df.empty:
            me = shares_df[shares_df["person_id"] == person_id]
            if not me.empty:
                pct_me = float(me["pct"].iloc[0] or 0)
                my_initial = float(me.get("initial_invest_eur", pd.Series([0])).iloc[0] or 0)
                my_cca = float(me.get("cca_eur", pd.Series([0])).iloc[0] or 0)

        # --- KPIs personnels ---
        my_gross = valo * pct_me / 100.0
        my_debt = debt * pct_me / 100.0
        my_net = my_gross - my_debt

        perf_eur = None
        perf_pct = None
        if my_initial > 0:
            perf_eur = my_net - my_initial
            perf_pct = (perf_eur / my_initial) * 100.0

        st.markdown("### Mes KPIs (personnels)")
        p1, p2, p3 = st.columns(3)
        p1.metric("Ma valorisation", _fmt_eur(my_gross))
        p2.metric("Ma dette (quote-part)", _fmt_eur(my_debt))
        p3.metric("Ma valeur nette", _fmt_eur(my_net))

        p4, p5, p6 = st.columns(3)
        p4.metric("Investissement initial", _fmt_eur(my_initial))
        p5.metric("Apport CCA", _fmt_eur(my_cca))
        if perf_eur is None:
            p6.metric("Perf (sur initial)", "—")
        else:
            p6.metric("Perf (sur initial)", f"{_fmt_eur(perf_eur)} ({perf_pct:.1f}%)")

        st.caption("Perf = (valeur nette - investissement initial). Les apports en CCA ne sont pas pris en compte.")
        # --- KPIs globaux ---

        st.markdown("### KPIs globaux (entreprise)")
        g1, g2, g3 = st.columns(3)
        g1.metric("Valorisation totale", _fmt_eur(valo))
        g2.metric("Dette totale", _fmt_eur(debt))
        g3.metric("Valeur nette totale", _fmt_eur(net))


    # --- Ajouter ---
    with st.expander("➕ Ajouter une entreprise", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nom", key=f"{key_prefix}_add_name")
            entity_type = st.selectbox("Type", ["SAS", "SCI", "SARL", "Holding", "Autre"], key=f"{key_prefix}_add_type")
            valuation = st.number_input("Valorisation (€)", min_value=0.0, step=1000.0, key=f"{key_prefix}_add_valo")
        with col2:
            debt = st.number_input("Dette (€)", min_value=0.0, step=1000.0, key=f"{key_prefix}_add_debt")
            effective_date = st.date_input("Date de valorisation", key=f"{key_prefix}_add_effective_date")
            note = st.text_input("Note (optionnel)", key=f"{key_prefix}_add_note")


        st.markdown("### Répartition + investissement")
        shares = {}
        total_pct = 0.0

        for _, p in people.iterrows():
            pid = int(p["id"])
            st.markdown(f"**{p['name']}**")
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                pct = st.number_input(
                    "Part (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    key=f"{key_prefix}_add_pct_{pid}",
                )
            with c2:
                initial = st.number_input(
                    "Investissement initial (€)",
                    min_value=0.0,
                    step=100.0,
                    key=f"{key_prefix}_add_initial_{pid}",
                )
            with c3:
                cca = st.number_input(
                    "Apport CCA (€)",
                    min_value=0.0,
                    step=100.0,
                    key=f"{key_prefix}_add_cca_{pid}",
                )
            with c4:
                initial_date = st.date_input(
                    "Date investissement initial",
                    key=f"{key_prefix}_add_initial_date_{pid}",
                )

            shares[pid] = {
                "pct": float(pct),
                "initial": float(initial),
                "cca": float(cca),
                "initial_date": initial_date.isoformat() if initial > 0 else None,
            }
            total_pct += float(pct)


        st.caption(f"Total : {total_pct:.2f}%")
        if abs(total_pct - 100.0) > 0.01:
            st.warning("Le total n’est pas à 100%. (Tu peux quand même enregistrer, mais c’est recommandé.)")

        if st.button("Créer l’entreprise", use_container_width=True, key=f"{key_prefix}_add_btn"):
            if not name or not name.strip():
                st.error("Nom obligatoire.")
            else:
                new_id = ent_repo.create_enterprise(conn, name=name, entity_type=entity_type, valuation_eur=valuation, debt_eur=debt, note=note, effective_date=effective_date.isoformat(),)
                ent_repo.replace_shares(conn, new_id, shares)
                st.success("Entreprise créée ✅ (recharge la page si besoin).")

    # --- Modifier ---
    with st.expander("✏️ Modifier l’entreprise sélectionnée", expanded=False):
        if not selected_id:
            st.info("Sélectionne une entreprise au-dessus.")
        else:
            row = ent_repo.get_enterprise(conn, selected_id)
            shares_df = ent_repo.list_shares(conn, selected_id)

            entity_type = st.selectbox(
                "Type",
                ["SAS", "SCI", "SARL", "Holding", "Autre"],
                index=["SAS", "SCI", "SARL", "Holding", "Autre"].index(str(row["entity_type"])),
                key=f"{key_prefix}_edit_type",
            )
            valuation = st.number_input("Valorisation (€)", min_value=0.0, step=1000.0, value=float(row["valuation_eur"] or 0), key=f"{key_prefix}_edit_valo")
            debt = st.number_input("Dette (€)", min_value=0.0, step=1000.0, value=float(row["debt_eur"] or 0), key=f"{key_prefix}_edit_debt")
            effective_date = st.date_input("Date de valorisation", key=f"{key_prefix}_edit_effective_date")
            note = st.text_input("Note (optionnel)", value=str(row["note"] or ""), key=f"{key_prefix}_edit_note")

            st.markdown("### Répartition (%)")
            shares = {}
            total_pct = 0.0

            # map actuel (si absent => 0)
            current = (
                {
                    int(r["person_id"]): {
                        "pct": float(r.get("pct", 0.0) or 0.0),
                        "initial": float(r.get("initial_invest_eur", 0.0) or 0.0),
                        "cca": float(r.get("cca_eur", 0.0) or 0.0),
                        "initial_date": r.get("initial_invest_date", None),
                    }
                    for _, r in shares_df.iterrows()
                }
                if not shares_df.empty
                else {}
            )

            for _, p in people.iterrows():
                pid = int(p["id"])
                cur = current.get(pid, {"pct": 0.0, "initial": 0.0, "cca": 0.0})

                st.markdown(f"**{p['name']}**")
                c1, c2, c3 = st.columns(3)

                with c1:
                    pct = st.number_input(
                        "Part (%)",
                        min_value=0.0,
                        max_value=100.0,
                        step=1.0,
                        value=float(cur["pct"]),
                        key=f"{key_prefix}_edit_pct_{pid}",
                    )
                with c2:
                    initial = st.number_input(
                        "Investissement initial (€)",
                        min_value=0.0,
                        step=100.0,
                        value=float(cur["initial"]),
                        key=f"{key_prefix}_edit_initial_{pid}",
                    )
                with c3:
                    cca = st.number_input(
                        "Apport CCA (€)",
                        min_value=0.0,
                        step=100.0,
                        value=float(cur["cca"]),
                        key=f"{key_prefix}_edit_cca_{pid}",
                    )

                shares[pid] = {"pct": float(pct), "initial": float(initial), "cca": float(cca)}
                total_pct += float(pct)


            st.caption(f"Total : {total_pct:.2f}%")
            if abs(total_pct - 100.0) > 0.01:
                st.warning("Le total n’est pas à 100%. (Tu peux quand même enregistrer, mais c’est recommandé.)")

            if st.button("Enregistrer les modifications", use_container_width=True, key=f"{key_prefix}_edit_btn"):
                ent_repo.update_enterprise(conn, selected_id, entity_type=entity_type, valuation_eur=valuation, debt_eur=debt, note=note)
                ent_repo.replace_shares(conn, selected_id, shares)
                st.success("Modifications enregistrées ✅ (recharge la page si besoin).")

    # ---------- SECTION B : Répartition & Ma part ----------
    st.markdown("## Répartition & valeur par personne")

    if not selected_id:
        return

    row = ent_repo.get_enterprise(conn, selected_id)
    valo = float(row["valuation_eur"] or 0)
    debt = float(row["debt_eur"] or 0)

    shares_df = ent_repo.list_shares(conn, selected_id)
    if shares_df.empty:
        st.warning("Aucune répartition enregistrée pour cette entreprise.")
        return

    out = []
    total_pct = 0.0
    for _, r in shares_df.iterrows():
        pct = float(r.get("pct", 0) or 0)
        total_pct += pct

        gross = valo * pct / 100.0
        debt_part = debt * pct / 100.0
        net = gross - debt_part

        initial = float(r.get("initial_invest_eur", 0) or 0)
        cca = float(r.get("cca_eur", 0) or 0)

        perf_initial_eur = None
        perf_initial_pct = None
        if initial > 0:
            perf_initial_eur = net - initial
            perf_initial_pct = (perf_initial_eur / initial) * 100.0

        out.append(
            {
                "Personne": r["person_name"],
                "%": pct,
                "Valeur brute (€)": gross,
                "Dette (quote-part) (€)": debt_part,
                "Valeur nette (€)": net,
                "Invest initial (€)": initial,
                "CCA (€)": cca,
                "Perf initial (€)": perf_initial_eur,
                "Perf initial (%)": perf_initial_pct,
            }
        )


    df = pd.DataFrame(out)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(f"Total % : {total_pct:.2f}%")
    if abs(total_pct - 100.0) > 0.01:
        st.warning("⚠️ Total différent de 100% : les montants restent calculés, mais à vérifier.")

    # Ma part
    my_name = people.loc[people["id"] == person_id, "name"].iloc[0]
    my_row = df[df["Personne"] == my_name]
    if not my_row.empty:
        my_net = float(my_row["Valeur nette (€)"].iloc[0])
        st.info(f"**{my_name}** — valeur nette estimée : **{_fmt_eur(my_net)}**")


    # ---------- COURBE : valeur de la participation vs investissement initial ----------
    st.markdown("### Évolution de ma participation")

    # récupère mes infos (pct, initial, date initial)
    me = shares_df[shares_df["person_id"] == person_id]
    pct_me = float(me["pct"].iloc[0] or 0) if not me.empty else 0.0
    my_initial = float(me.get("initial_invest_eur", pd.Series([0])).iloc[0] or 0) if not me.empty else 0.0
    my_initial_date = None
    if not me.empty:
        my_initial_date = me.get("initial_invest_date", pd.Series([None])).iloc[0]

    # ⚠️ IMPORTANT : on définit hist_all AVANT de l'utiliser
    hist_all = ent_repo.list_history(conn, selected_id, limit=500)

    if hist_all is None or hist_all.empty:
        st.info("Pas assez d’historique pour tracer une courbe.")
    else:
        hist_all = hist_all.copy()

        # on utilise effective_date si dispo, sinon fallback changed_at
        if "effective_date" in hist_all.columns:
            hist_all["date"] = pd.to_datetime(hist_all["effective_date"], errors="coerce")
        else:
            hist_all["date"] = pd.to_datetime(hist_all["changed_at"], errors="coerce")

        hist_all = hist_all.dropna(subset=["date"]).sort_values("date")

        if hist_all.empty:
            st.info("Pas assez de dates valides dans l’historique.")
        else:
            hist_all["enterprise_net"] = (hist_all["valuation_eur"].fillna(0) - hist_all["debt_eur"].fillna(0))
            hist_all["my_value"] = hist_all["enterprise_net"] * pct_me / 100.0
            hist_all["initial_line"] = my_initial

            # CAGR : priorité à la date d'invest initial, sinon 1ère valo
            start_dt = None
            if my_initial_date:
                try:
                    start_dt = pd.to_datetime(my_initial_date, errors="coerce")
                except Exception:
                    start_dt = None
            if start_dt is None or pd.isna(start_dt):
                start_dt = hist_all["date"].iloc[0]

            cagr = None
            if my_initial > 0:
                years = (pd.Timestamp.now() - start_dt).days / 365.25
                last_value = float(hist_all["my_value"].iloc[-1])
                if years > 0 and last_value > 0:
                    cagr = (last_value / my_initial) ** (1 / years) - 1

            if cagr is None:
                st.caption("CAGR : — (investissement initial = 0 ou historique insuffisant)")
            else:
                st.caption(f"CAGR depuis {start_dt.date().isoformat()} : **{cagr*100:.1f}% / an**")

            chart_df = hist_all[["date", "my_value", "initial_line"]].rename(
                columns={"my_value": "Valeur de ma participation", "initial_line": "Investissement initial"}
            )
            long = chart_df.melt("date", var_name="Série", value_name="Montant")
            long["date"] = pd.to_datetime(long["date"]).dt.date

            st.line_chart(
            
                data=long.pivot_table(index="date", columns="Série", values="Montant", aggfunc="last"),
                use_container_width=True,
            )

            st.markdown("#### Dates clés")
            keys = hist_all[["date", "valuation_eur", "debt_eur", "note"]].copy()
            keys["Valeur nette entreprise (€)"] = keys["valuation_eur"].fillna(0) - keys["debt_eur"].fillna(0)
            keys = keys.rename(columns={"date": "Date", "note": "Note"})
            st.dataframe(keys, use_container_width=True, hide_index=True)


    # Historique (simple)
    hist = ent_repo.list_history(conn, selected_id, limit=10)
    if not hist.empty:
        st.markdown("### Historique (10 dernières mises à jour)")
        st.dataframe(hist, use_container_width=True, hide_index=True)
