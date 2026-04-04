"""
Panel Vue d'ensemble — remplace ui/vue_ensemble_overview.py
Affiche le patrimoine net, les allocations, l'évolution hebdomadaire.
"""
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from qt_ui.theme import (
    BG_PRIMARY, STYLE_BTN_PRIMARY, STYLE_GROUP, STYLE_SECTION,
    STYLE_STATUS, CHART_GREEN, CHART_RED, plotly_layout,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR, TEXT_MUTED,
)
from qt_ui.widgets import PlotlyView, DataTableWidget, KpiCard, MetricLabel, LoadingOverlay
from utils.format_monnaie import money


def _color_for_rate(rate):
    if rate is None:
        return "#64748b"
    if rate >= 20:
        return COLOR_SUCCESS
    if rate >= 10:
        return "#86efac"
    if rate >= 0:
        return COLOR_WARNING
    return COLOR_ERROR


def _tone_for_rate(rate):
    if rate is None:
        return "neutral"
    if rate >= 20:
        return "success"
    if rate >= 10:
        return "green"
    if rate >= 0:
        return "neutral"
    return "alert"

logger = logging.getLogger(__name__)


class SnapshotRebuildThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, person_id: int):
        super().__init__()
        self._person_id = person_id

    def run(self):
        try:
            from services import snapshots as wk_snap
            from services.db import get_conn
            with get_conn() as local_conn:
                res = wk_snap.rebuild_snapshots_person_from_last(
                    local_conn, person_id=self._person_id,
                    safety_weeks=4, fallback_lookback_days=90
                )
            self.finished.emit(str(res))
        except Exception as e:
            self.error.emit(str(e))


class VueEnsemblePanel(QWidget):
    def __init__(self, conn, person_id: int, parent=None):
        super().__init__(parent)
        self._conn = conn
        self._person_id = person_id
        self._thread = None

        self.setStyleSheet(f"background: {BG_PRIMARY};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header + Rebuild
        top_row = QHBoxLayout()
        self._btn_rebuild = QPushButton("📸  Rebuild snapshots (90j)")
        self._btn_rebuild.setStyleSheet(STYLE_BTN_PRIMARY)
        self._btn_rebuild.clicked.connect(self._on_rebuild)
        top_row.addWidget(self._btn_rebuild)
        self._rebuild_status = QLabel()
        self._rebuild_status.setStyleSheet(STYLE_STATUS)
        top_row.addWidget(self._rebuild_status)
        top_row.addStretch()
        layout.addLayout(top_row)

        # KPI cards row 1
        kpi_row1 = QHBoxLayout()
        self._kpi_net = KpiCard("Patrimoine net", "—", tone="blue")
        self._kpi_brut = KpiCard("Patrimoine brut", "—", tone="green")
        self._kpi_liq = KpiCard("Liquidités", "—", tone="primary")
        self._kpi_bourse = KpiCard("Holdings bourse", "—", tone="broker")
        self._kpi_credits = KpiCard("Crédits restants", "—", tone="red")
        for k in [self._kpi_net, self._kpi_brut, self._kpi_liq, self._kpi_bourse, self._kpi_credits]:
            kpi_row1.addWidget(k)
        layout.addLayout(kpi_row1)

        # KPI perfs
        kpi_row2 = QHBoxLayout()
        self._kpi_3m = MetricLabel("Évolution 3 mois", "—")
        self._kpi_12m = MetricLabel("Évolution 12 mois", "—")
        self._kpi_cagr = MetricLabel("Rendement annualisé", "—")
        kpi_row2.addWidget(self._kpi_3m)
        kpi_row2.addWidget(self._kpi_12m)
        kpi_row2.addWidget(self._kpi_cagr)
        kpi_row2.addStretch()
        layout.addLayout(kpi_row2)

        # Graphique évolution
        lbl_ev = QLabel("📈 Évolution du patrimoine net (weekly)")
        lbl_ev.setStyleSheet(STYLE_SECTION)
        layout.addWidget(lbl_ev)
        self._chart_line = PlotlyView(min_height=300)
        layout.addWidget(self._chart_line)

        # Graphiques de répartition (côte à côte)
        pie_row = QHBoxLayout()

        left_box = QGroupBox("Répartition par catégorie")
        left_box.setStyleSheet(STYLE_GROUP)
        left_v = QVBoxLayout(left_box)
        self._chart_alloc = PlotlyView(min_height=260)
        left_v.addWidget(self._chart_alloc)

        right_box = QGroupBox("Dépenses vs Revenus (12 mois)")
        right_box.setStyleSheet(STYLE_GROUP)
        right_v = QVBoxLayout(right_box)
        self._chart_cashflow = PlotlyView(min_height=260)
        right_v.addWidget(self._chart_cashflow)

        pie_row.addWidget(left_box)
        pie_row.addWidget(right_box)
        layout.addLayout(pie_row)

        # ── Section Taux d'épargne ─────────────────────────────────────────
        kpi_row3 = QHBoxLayout()
        self._kpi_avg12 = KpiCard("Taux moy. épargne 12 mois", "—", tone="neutral")
        self._kpi_avg12_ep = KpiCard("Épargne moy. 12 mois", "—", tone="neutral")
        kpi_row3.addWidget(self._kpi_avg12)
        kpi_row3.addWidget(self._kpi_avg12_ep)
        kpi_row3.addStretch()
        layout.addLayout(kpi_row3)

        epargne_box = QGroupBox("Taux d'épargne (24 derniers mois)")
        epargne_box.setStyleSheet(STYLE_GROUP)
        epargne_box_v = QVBoxLayout(epargne_box)
        self._chart_epargne = PlotlyView(min_height=280)
        epargne_box_v.addWidget(self._chart_epargne)
        layout.addWidget(epargne_box)

        # Semaine info
        self._semaine_label = QLabel()
        self._semaine_label.setStyleSheet(STYLE_STATUS)
        layout.addWidget(self._semaine_label)

        layout.addStretch()

        # ── Overlay de chargement ──────────────────────────────────────────
        self._overlay = LoadingOverlay(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlay.resize(self.size())

    def refresh(self) -> None:
        self._load_data()

    def set_person(self, person_id: int) -> None:
        self._person_id = person_id
        self._load_data()

    def _on_rebuild(self) -> None:
        self._btn_rebuild.setEnabled(False)
        self._rebuild_status.setText("Rebuild en cours...")
        self._thread = SnapshotRebuildThread(self._person_id)
        self._thread.finished.connect(self._on_rebuild_done)
        self._thread.error.connect(lambda e: self._rebuild_status.setText(f"Erreur : {e}"))
        self._thread.start()

    def _on_rebuild_done(self, result: str) -> None:
        self._btn_rebuild.setEnabled(True)
        self._rebuild_status.setText(f"Rebuild terminé ✅")
        self._load_data()

    def _load_data(self) -> None:
        self._overlay.start("Chargement des snapshots…")
        try:
            rows = self._conn.execute(
                "SELECT * FROM patrimoine_snapshots_weekly WHERE person_id = ? ORDER BY week_date",
                (self._person_id,)
            ).fetchall()
            df_snap = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()

            if df_snap is None or df_snap.empty:
                self._semaine_label.setText("Aucune donnée weekly — lancez un rebuild.")
                return

            # Dernière semaine
            last = df_snap.iloc[-1]
            net = float(last.get("patrimoine_net", 0))
            brut = float(last.get("patrimoine_brut", 0))
            liq = float(last.get("liquidites_total", 0))
            bourse = float(last.get("bourse_holdings", 0))
            credits = float(last.get("credits_remaining", 0))
            week_date = str(last.get("week_date", "—"))

            self._semaine_label.setText(f"Données au : {week_date}")
            self._kpi_net.set_content("Patrimoine net", money(net), tone="blue")
            self._kpi_brut.set_content("Patrimoine brut", money(brut), tone="green")
            self._kpi_liq.set_content("Liquidités", money(liq), tone="primary")
            self._kpi_bourse.set_content("Holdings bourse", money(bourse), tone="broker")
            self._kpi_credits.set_content("Crédits restants", money(credits), tone="red")

            # Perfs
            try:
                df_snap["week_date"] = pd.to_datetime(df_snap["week_date"], errors="coerce")
                df_snap = df_snap.dropna(subset=["week_date"]).sort_values("week_date")
                today = pd.Timestamp.today()

                def perf_pct(weeks_back):
                    target = today - pd.Timedelta(weeks=weeks_back)
                    past = df_snap[df_snap["week_date"] <= target]
                    if past.empty:
                        return None
                    val_past = float(past.iloc[-1]["patrimoine_net"])
                    if abs(val_past) < 1:
                        return None
                    return (net - val_past) / abs(val_past) * 100

                p3m = perf_pct(13)
                p12m = perf_pct(52)
                self._kpi_3m.set_content("Évolution 3 mois", f"{p3m:.1f}%" if p3m is not None else "—",
                                          delta=f"{p3m:.1f}%" if p3m is not None else None, delta_positive=(p3m or 0) >= 0)
                self._kpi_12m.set_content("Évolution 12 mois", f"{p12m:.1f}%" if p12m is not None else "—",
                                           delta=f"{p12m:.1f}%" if p12m is not None else None, delta_positive=(p12m or 0) >= 0)

                # CAGR
                if len(df_snap) >= 2:
                    first = df_snap.iloc[0]
                    val_first = float(first["patrimoine_net"])
                    n_years = (today - df_snap.iloc[0]["week_date"]).days / 365.25
                    if abs(val_first) > 1 and n_years > 0.1:
                        ratio = net / val_first
                        if ratio > 0:
                            cagr = (ratio ** (1 / n_years) - 1) * 100
                            self._kpi_cagr.set_content("Rendement annualisé", f"{cagr:.1f}%",
                                                        delta=f"{cagr:.1f}%", delta_positive=cagr >= 0)
                        else:
                            self._kpi_cagr.set_content("Rendement annualisé", "—")
            except Exception as e:
                logger.warning("Calcul des performances échoué : %s", e)

            # Graphique ligne
            fig_line = px.line(df_snap, x="week_date", y="patrimoine_net",
                               template="plotly_dark",
                               labels={"week_date": "Semaine", "patrimoine_net": "Patrimoine net (€)"})
            fig_line.update_layout(**plotly_layout())
            self._chart_line.set_figure(fig_line)

            # Répartition
            alloc_data = [
                {"Catégorie": "Liquidités", "Valeur": max(0, liq)},
                {"Catégorie": "Holdings bourse", "Valeur": max(0, bourse)},
                {"Catégorie": "PE", "Valeur": max(0, float(last.get("pe_value", 0)))},
                {"Catégorie": "Entreprises", "Valeur": max(0, float(last.get("ent_value", 0)))},
            ]
            alloc_df = pd.DataFrame([a for a in alloc_data if a["Valeur"] > 0])
            if not alloc_df.empty:
                fig_alloc = px.pie(alloc_df, names="Catégorie", values="Valeur", hole=0.45,
                                   template="plotly_dark")
                fig_alloc.update_layout(**plotly_layout())
                self._chart_alloc.set_figure(fig_alloc)

            # Cashflow
            try:
                self._load_cashflow_chart()
            except Exception as e:
                logger.warning("Chargement du graphique cashflow échoué : %s", e)

            # Taux d'épargne
            try:
                self._load_epargne_section()
            except Exception as e:
                logger.warning("Chargement de la section taux d'épargne échoué : %s", e)

        except Exception as e:
            self._semaine_label.setText(f"Erreur : {e}")
        finally:
            self._overlay.stop()

    def _load_epargne_section(self) -> None:
        from services.revenus_repository import compute_taux_epargne_mensuel

        df = compute_taux_epargne_mensuel(self._conn, self._person_id, n_mois=24)
        if df is None or df.empty:
            self._kpi_avg12.set_content("Taux moy. épargne 12 mois", "—", tone="neutral")
            self._kpi_avg12_ep.set_content("Épargne moy. 12 mois", "—", tone="neutral")
            return

        # KPI moyenne 12 mois
        last12 = df.tail(12)
        valid_rates = last12["taux_epargne"].dropna()
        if not valid_rates.empty:
            avg_rate = round(float(valid_rates.mean()), 1)
            self._kpi_avg12.set_content(
                "Taux moy. épargne 12 mois", f"{avg_rate} %",
                subtitle="Taux moyen d'épargne", tone=_tone_for_rate(avg_rate),
            )
        else:
            self._kpi_avg12.set_content("Taux moy. épargne 12 mois", "—", tone="neutral")

        avg_ep = float(last12["epargne"].mean()) if not last12.empty else 0.0
        self._kpi_avg12_ep.set_content(
            "Épargne moy. 12 mois",
            f"{avg_ep:+,.0f} €".replace(",", " "),
            subtitle="Revenus − Dépenses / mois",
            tone="success" if avg_ep >= 0 else "alert",
        )

        # Graphique
        self._build_epargne_chart(df)

    def _build_epargne_chart(self, df: pd.DataFrame) -> None:
        try:
            df = df.copy()
            df["mois_label"] = pd.to_datetime(df["mois"], errors="coerce").dt.strftime("%b %Y")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["mois_label"], y=df["revenus"],
                name="Revenus", marker_color="rgba(96,165,250,0.25)",
                hovertemplate="<b>%{x}</b><br>Revenus : %{y:,.0f} €<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                x=df["mois_label"], y=df["depenses"],
                name="Dépenses", marker_color="rgba(239,68,68,0.35)",
                hovertemplate="<b>%{x}</b><br>Dépenses : %{y:,.0f} €<extra></extra>",
            ))
            df_valid = df.dropna(subset=["taux_epargne"])
            if not df_valid.empty:
                fig.add_trace(go.Scatter(
                    x=df_valid["mois_label"], y=df_valid["taux_epargne"],
                    name="Taux d'épargne", yaxis="y2",
                    mode="lines+markers",
                    line=dict(color=COLOR_SUCCESS, width=2.5),
                    marker=dict(size=7, color=df_valid["taux_epargne"].apply(_color_for_rate)),
                    hovertemplate="<b>%{x}</b><br>Taux : %{y:.1f} %<extra></extra>",
                ))
            if len(df) > 0:
                fig.add_hline(
                    y=20, yref="y2",
                    line=dict(color="#4ade80", width=1.5, dash="dot"),
                    annotation_text="Objectif 20 %",
                    annotation_font_color="#4ade80",
                    annotation_position="top right",
                )
            fig.add_hline(
                y=0, yref="y2",
                line=dict(color="#64748b", width=1, dash="solid"),
            )
            fig.update_layout(
                **plotly_layout(barmode="group", margin=dict(l=10, r=10, t=10, b=10)),
                xaxis=dict(title="", showgrid=False, tickangle=-35),
                yaxis=dict(
                    title="Montant (€)", showgrid=True, gridcolor="#1e2538",
                    tickformat=",.0f", ticksuffix=" €",
                ),
                yaxis2=dict(
                    title="Taux (%)", overlaying="y", side="right",
                    showgrid=False, ticksuffix=" %",
                    zeroline=True, zerolinecolor="#334155", zerolinewidth=1,
                ),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=11),
                ),
                hovermode="x unified",
            )
            self._chart_epargne.set_figure(fig)
        except Exception as e:
            logger.warning("VueEnsemblePanel._build_epargne_chart error: %s", e)

    def _load_cashflow_chart(self) -> None:
        try:
            from services.depenses_repository import depenses_par_mois
            from services.revenus_repository import revenus_par_mois

            df_dep = depenses_par_mois(self._conn, self._person_id)
            df_rev = revenus_par_mois(self._conn, self._person_id)

            if (df_dep is None or df_dep.empty) and (df_rev is None or df_rev.empty):
                return

            rows = []
            mois_set = set()
            if df_dep is not None and not df_dep.empty and "mois" in df_dep.columns:
                dep_cols = [c for c in df_dep.columns if c not in ("mois", "person_id", "person_name")]
                df_dep["total"] = df_dep[dep_cols].sum(axis=1) if dep_cols else 0
                for _, r in df_dep.iterrows():
                    mois_set.add(str(r["mois"]))

            if df_rev is not None and not df_rev.empty and "mois" in df_rev.columns:
                rev_cols = [c for c in df_rev.columns if c not in ("mois", "person_id", "person_name")]
                df_rev["total"] = df_rev[rev_cols].sum(axis=1) if rev_cols else 0

            for m in sorted(mois_set)[-12:]:
                d = 0.0
                r_val = 0.0
                if df_dep is not None and not df_dep.empty:
                    row_d = df_dep[df_dep["mois"] == m]
                    if not row_d.empty:
                        d = float(row_d.iloc[0].get("total", 0))
                if df_rev is not None and not df_rev.empty:
                    row_r = df_rev[df_rev["mois"] == m]
                    if not row_r.empty:
                        r_val = float(row_r.iloc[0].get("total", 0))
                rows.append({"Mois": m, "Revenus": r_val, "Dépenses": d})

            if rows:
                df_cf = pd.DataFrame(rows)
                fig = go.Figure()
                fig.add_trace(go.Bar(x=df_cf["Mois"], y=df_cf["Revenus"], name="Revenus", marker_color=CHART_GREEN))
                fig.add_trace(go.Bar(x=df_cf["Mois"], y=df_cf["Dépenses"], name="Dépenses", marker_color=CHART_RED))
                fig.update_layout(**plotly_layout(barmode="group",
                                  xaxis_title="Mois", yaxis_title="Montant (€)"))
                self._chart_cashflow.set_figure(fig)
        except Exception as e:
            logger.error("Erreur chargement graphique cashflow : %s", e)
