"""
Panel Prévision avancée — moteur déterministe, Monte Carlo, stress tests.
Consomme uniquement services.prevision (façade publique).
"""
import logging
import math
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from qt_ui.theme import (
    BG_CARD,
    BG_PRIMARY,
    BORDER_DEFAULT,
    STYLE_BTN_PRIMARY,
    STYLE_BTN_PRIMARY_BORDERED,
    STYLE_BTN_SUCCESS,
    STYLE_GROUP,
    STYLE_INPUT_FOCUS,
    STYLE_SECTION,
    STYLE_STATUS,
    STYLE_STATUS_ERROR,
    STYLE_STATUS_SUCCESS,
    STYLE_STATUS_WARNING,
    STYLE_TITLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    plotly_layout,
)
from qt_ui.widgets import KpiCard, PlotlyView
from utils.format_monnaie import money

logger = logging.getLogger(__name__)


# ─── Thread pour exécuter la simulation hors UI ──────────────────────────

class _PrevisionThread(QThread):
    """Exécute run_prevision dans un thread séparé."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, scope_type: str, scope_id: Optional[int],
                 config, engine: str):
        super().__init__()
        self._scope_type = scope_type
        self._scope_id = scope_id
        self._config = config
        self._engine = engine

    def run(self):
        try:
            from services.db import get_conn
            from services.prevision import run_prevision
            with get_conn() as conn:
                result = run_prevision(
                    conn, self._scope_type, self._scope_id,
                    self._config, engine=self._engine,
                )
            self.finished.emit(result)
        except Exception as exc:
            logger.error("Erreur prevision thread: %s", exc)
            self.error.emit(str(exc))


class _StressThread(QThread):
    """Exécute run_stress_prevision dans un thread séparé."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, scope_type: str, scope_id: Optional[int],
                 config, scenario):
        super().__init__()
        self._scope_type = scope_type
        self._scope_id = scope_id
        self._config = config
        self._scenario = scenario

    def run(self):
        try:
            from services.db import get_conn
            from services.prevision import run_stress_prevision
            with get_conn() as conn:
                result = run_stress_prevision(
                    conn, self._scope_type, self._scope_id,
                    self._config, self._scenario,
                )
            self.finished.emit(result)
        except Exception as exc:
            logger.error("Erreur stress thread: %s", exc)
            self.error.emit(str(exc))


# ─── Helpers ─────────────────────────────────────────────────────────────

def _pct(value: float) -> str:
    """Formate un pourcentage."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{value * 100:.1f} %"


def _pct_signed(value: float) -> str:
    """Formate un pourcentage avec signe."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    v = value * 100
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f} %"


def _months_display(months: Optional[int]) -> str:
    """Affiche une durée en mois/années."""
    if months is None:
        return "—"
    if months < 12:
        return f"{months} mois"
    years = months / 12
    return f"{years:.1f} ans"


# ─── Panel principal ─────────────────────────────────────────────────────

class PrevisionAvanceePanel(QWidget):
    """
    Panel dédié à la prévision avancée (déterministe, Monte Carlo, stress).
    Consomme uniquement la façade services.prevision.
    """

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self._conn = conn
        self._scope_type: str = "family"
        self._scope_id: Optional[int] = None
        self._thread: Optional[QThread] = None
        self._result = None          # PrevisionResult
        self._stress_result = None   # StressResult
        self._build_ui()

    # ── Construction UI ──────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet(f"background: {BG_PRIMARY};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Titre
        title = QLabel("Prévision avancée")
        title.setStyleSheet(STYLE_TITLE)
        layout.addWidget(title)

        subtitle = QLabel(
            "Moteur de projection avancé : déterministe, Monte Carlo, stress tests."
        )
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        layout.addWidget(subtitle)

        # ── Bloc hypothèses ──────────────────────────────────────────────
        layout.addWidget(self._build_hypotheses_box())

        # ── Boutons d'action ─────────────────────────────────────────────
        layout.addLayout(self._build_action_buttons())

        # ── Statut ───────────────────────────────────────────────────────
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(STYLE_STATUS)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # ── Bloc KPI résultats ───────────────────────────────────────────
        layout.addLayout(self._build_kpi_section())

        # ── Bloc diagnostics ─────────────────────────────────────────────
        self._diagnostics_label = QLabel("")
        self._diagnostics_label.setWordWrap(True)
        self._diagnostics_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; line-height: 1.5;"
        )
        layout.addWidget(self._diagnostics_label)

        # ── Graphiques ───────────────────────────────────────────────────
        lbl_chart_main = QLabel("Trajectoire de projection")
        lbl_chart_main.setStyleSheet(STYLE_SECTION)
        layout.addWidget(lbl_chart_main)
        self._chart_trajectory = PlotlyView(min_height=340)
        layout.addWidget(self._chart_trajectory)

        lbl_chart_histo = QLabel("Distribution du patrimoine final")
        lbl_chart_histo.setStyleSheet(STYLE_SECTION)
        layout.addWidget(lbl_chart_histo)
        self._chart_histogram = PlotlyView(min_height=260)
        layout.addWidget(self._chart_histogram)

        # ── Bloc stress (conditionnel) ───────────────────────────────────
        self._stress_section_title = QLabel("Comparaison baseline vs stress")
        self._stress_section_title.setStyleSheet(STYLE_SECTION)
        self._stress_section_title.setVisible(False)
        layout.addWidget(self._stress_section_title)

        self._chart_stress = PlotlyView(min_height=300)
        self._chart_stress.setVisible(False)
        layout.addWidget(self._chart_stress)

        layout.addLayout(self._build_stress_kpi_section())

        layout.addStretch()

        # État initial vide
        self._set_empty_state()

    def _build_hypotheses_box(self) -> QGroupBox:
        """Construit le bloc des hypothèses de simulation."""
        box = QGroupBox("Hypothèses de simulation")
        box.setStyleSheet(STYLE_GROUP)
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        # Horizon
        self._spin_horizon = QSpinBox()
        self._spin_horizon.setRange(1, 50)
        self._spin_horizon.setValue(20)
        self._spin_horizon.setSuffix(" ans")
        self._spin_horizon.setStyleSheet(STYLE_INPUT_FOCUS)
        form.addRow("Horizon :", self._spin_horizon)

        # Simulations
        self._spin_simulations = QSpinBox()
        self._spin_simulations.setRange(100, 10000)
        self._spin_simulations.setValue(1000)
        self._spin_simulations.setSingleStep(100)
        self._spin_simulations.setStyleSheet(STYLE_INPUT_FOCUS)
        form.addRow("Simulations :", self._spin_simulations)

        # Objectif patrimonial
        self._spin_goal = QDoubleSpinBox()
        self._spin_goal.setRange(0, 100_000_000)
        self._spin_goal.setDecimals(0)
        self._spin_goal.setSuffix(" €")
        self._spin_goal.setValue(500_000)
        self._spin_goal.setSingleStep(10_000)
        self._spin_goal.setStyleSheet(STYLE_INPUT_FOCUS)
        form.addRow("Objectif patrimonial :", self._spin_goal)

        # Mode (déterministe / Monte Carlo)
        self._combo_engine = QComboBox()
        self._combo_engine.addItem("Monte Carlo", "monte_carlo")
        self._combo_engine.addItem("Déterministe", "deterministic")
        self._combo_engine.setStyleSheet(self._combo_style())
        self._combo_engine.currentIndexChanged.connect(self._on_engine_changed)
        form.addRow("Moteur :", self._combo_engine)

        # Scénario de stress
        self._combo_stress = QComboBox()
        self._combo_stress.addItem("Aucun (baseline)", None)
        self._combo_stress.setStyleSheet(self._combo_style())
        self._load_stress_scenarios()
        form.addRow("Stress test :", self._combo_stress)

        return box

    def _build_action_buttons(self) -> QHBoxLayout:
        """Boutons Lancer / Réinitialiser."""
        row = QHBoxLayout()

        self._btn_run = QPushButton("Lancer la simulation")
        self._btn_run.setStyleSheet(STYLE_BTN_SUCCESS)
        self._btn_run.clicked.connect(self._on_run_clicked)
        row.addWidget(self._btn_run)

        self._btn_reset = QPushButton("Réinitialiser")
        self._btn_reset.setStyleSheet(STYLE_BTN_PRIMARY_BORDERED)
        self._btn_reset.clicked.connect(self._on_reset_clicked)
        row.addWidget(self._btn_reset)

        row.addStretch()
        return row

    def _build_kpi_section(self) -> QHBoxLayout:
        """KPI cards pour les résultats principaux."""
        row = QHBoxLayout()

        self._kpi_final = KpiCard(tone="blue")
        self._kpi_median = KpiCard(tone="green")
        self._kpi_p10 = KpiCard(tone="neutral")
        self._kpi_p90 = KpiCard(tone="purple")

        for card in (self._kpi_final, self._kpi_median, self._kpi_p10, self._kpi_p90):
            row.addWidget(card)

        row2 = QHBoxLayout()
        self._kpi_proba = KpiCard(tone="primary")
        self._kpi_drawdown = KpiCard(tone="neutral")
        self._kpi_var = KpiCard(tone="neutral")

        for card in (self._kpi_proba, self._kpi_drawdown, self._kpi_var):
            row2.addWidget(card)

        # On retourne un layout vertical contenant les 2 lignes
        container = QVBoxLayout()
        container.setSpacing(8)
        container.addLayout(row)
        container.addLayout(row2)
        return container

    def _build_stress_kpi_section(self) -> QHBoxLayout:
        """KPI cards pour les résultats de stress."""
        row = QHBoxLayout()

        self._kpi_stress_delta = KpiCard(tone="neutral")
        self._kpi_stress_drawdown = KpiCard(tone="neutral")
        self._kpi_stress_recovery = KpiCard(tone="neutral")

        for card in (self._kpi_stress_delta, self._kpi_stress_drawdown,
                     self._kpi_stress_recovery):
            card.setVisible(False)
            row.addWidget(card)

        return row

    def _combo_style(self) -> str:
        return f"""
            QComboBox {{
                background: {BG_CARD}; color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_DEFAULT}; border-radius: 4px;
                padding: 6px 10px; font-size: 13px; min-width: 200px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """

    # ── Chargement des scénarios de stress ───────────────────────────────

    def _load_stress_scenarios(self):
        """Charge les scénarios standard depuis le service."""
        try:
            from services.prevision_stress import list_standard_scenarios
            scenarios = list_standard_scenarios()
            for key, scenario in scenarios.items():
                self._combo_stress.addItem(scenario.description, key)
        except Exception as exc:
            logger.error("Impossible de charger les scénarios de stress: %s", exc)

    # ── API publique ─────────────────────────────────────────────────────

    def set_scope(self, scope_type: str, scope_id: Optional[int]):
        """Appelé par la page parente quand le scope change."""
        self._scope_type = scope_type
        self._scope_id = scope_id

    def refresh(self):
        """Rafraîchit le panel (appelé quand l'onglet devient visible)."""
        # On ne lance pas automatiquement une simulation coûteuse.
        # L'utilisateur doit cliquer sur "Lancer".
        pass

    # ── Gestion des événements ───────────────────────────────────────────

    def _on_engine_changed(self, _index: int):
        """Active/désactive le champ simulations selon le moteur."""
        is_mc = self._combo_engine.currentData() == "monte_carlo"
        self._spin_simulations.setEnabled(is_mc)

    def _on_run_clicked(self):
        """Lance la simulation."""
        if self._thread and self._thread.isRunning():
            return

        self._set_loading_state()

        config = self._build_config()
        engine = self._combo_engine.currentData()
        stress_key = self._combo_stress.currentData()

        if stress_key:
            self._run_stress(config, stress_key)
        else:
            self._run_prevision(config, engine)

    def _on_reset_clicked(self):
        """Réinitialise les paramètres par défaut."""
        self._spin_horizon.setValue(20)
        self._spin_simulations.setValue(1000)
        self._spin_goal.setValue(500_000)
        self._combo_engine.setCurrentIndex(0)
        self._combo_stress.setCurrentIndex(0)
        self._set_empty_state()

    # ── Construction du config ───────────────────────────────────────────

    def _build_config(self):
        """Construit un PrevisionConfig depuis les widgets."""
        from services.prevision_models import PrevisionConfig

        goal_value = self._spin_goal.value()
        return PrevisionConfig(
            horizon_years=self._spin_horizon.value(),
            num_simulations=self._spin_simulations.value(),
            target_goal_amount=goal_value if goal_value > 0 else None,
        )

    # ── Exécution des simulations ────────────────────────────────────────

    def _run_prevision(self, config, engine: str):
        """Lance run_prevision dans un thread."""
        self._thread = _PrevisionThread(
            self._scope_type, self._scope_id, config, engine,
        )
        self._thread.finished.connect(self._on_prevision_finished)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _run_stress(self, config, stress_key: str):
        """Lance run_stress_prevision dans un thread."""
        from services.prevision_stress import list_standard_scenarios
        scenarios = list_standard_scenarios()
        scenario = scenarios.get(stress_key)
        if not scenario:
            self._set_error_state(f"Scénario inconnu : {stress_key}")
            return

        self._thread = _StressThread(
            self._scope_type, self._scope_id, config, scenario,
        )
        self._thread.finished.connect(self._on_stress_finished)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    # ── Callbacks résultats ──────────────────────────────────────────────

    def _on_prevision_finished(self, result):
        """Affiche les résultats d'une simulation standard."""
        self._result = result
        self._stress_result = None
        self._update_kpis(result)
        self._update_charts(result)
        self._update_diagnostics(result)
        self._hide_stress_section()

        engine_label = self._combo_engine.currentText()
        self._status_label.setStyleSheet(STYLE_STATUS_SUCCESS)
        self._status_label.setText(
            f"Simulation terminée — {engine_label}, "
            f"horizon {result.config.horizon_years} ans."
        )
        self._btn_run.setEnabled(True)

    def _on_stress_finished(self, stress_result):
        """Affiche les résultats d'un stress test."""
        self._stress_result = stress_result
        self._result = stress_result.baseline_result
        self._update_kpis(stress_result.baseline_result)
        self._update_charts(stress_result.baseline_result)
        self._update_diagnostics(stress_result.baseline_result)
        self._show_stress_section(stress_result)

        self._status_label.setStyleSheet(STYLE_STATUS_SUCCESS)
        self._status_label.setText(
            f"Stress test terminé — {stress_result.scenario.description}"
        )
        self._btn_run.setEnabled(True)

    def _on_error(self, error_msg: str):
        """Gère les erreurs de simulation."""
        self._set_error_state(error_msg)
        self._btn_run.setEnabled(True)

    # ── Mise à jour des KPIs ─────────────────────────────────────────────

    def _update_kpis(self, result):
        """Met à jour les KPI cards depuis un PrevisionResult."""
        # Patrimoine final médian
        self._kpi_final.set_content(
            "Patrimoine final (médiane)",
            money(result.final_net_worth_median),
            subtitle=f"Horizon {result.config.horizon_years} ans",
            tone="blue",
        )

        # Patrimoine actuel
        self._kpi_median.set_content(
            "Patrimoine actuel",
            money(result.base.current_net_worth),
            subtitle="Base de départ",
            tone="green",
        )

        # P10 / P90
        if result.percentile_10_series is not None:
            p10_final = result.percentile_10_series.iloc[-1]
            self._kpi_p10.set_content(
                "P10 (scénario défavorable)",
                money(p10_final),
                tone="neutral",
            )
        else:
            self._kpi_p10.set_content("P10", "—", subtitle="Déterministe", tone="neutral")

        if result.percentile_90_series is not None:
            p90_final = result.percentile_90_series.iloc[-1]
            self._kpi_p90.set_content(
                "P90 (scénario favorable)",
                money(p90_final),
                tone="purple",
            )
        else:
            self._kpi_p90.set_content("P90", "—", subtitle="Déterministe", tone="neutral")

        # Probabilité d'atteinte
        if result.goal_metrics:
            proba = result.goal_metrics.probability_of_success
            tone = "success" if proba >= 0.7 else ("primary" if proba >= 0.4 else "alert")
            self._kpi_proba.set_content(
                "Probabilité d'atteinte",
                _pct(proba),
                subtitle=f"Objectif {money(result.config.target_goal_amount or 0)}",
                tone=tone,
            )
        else:
            self._kpi_proba.set_content("Probabilité", "—", tone="neutral")

        # Max drawdown
        if result.risk_metrics:
            self._kpi_drawdown.set_content(
                "Max drawdown",
                _pct(result.risk_metrics.max_drawdown),
                tone="neutral",
            )
            self._kpi_var.set_content(
                "VaR 95%",
                money(result.risk_metrics.var_95),
                tone="neutral",
            )
        else:
            self._kpi_drawdown.set_content("Max drawdown", "—", tone="neutral")
            self._kpi_var.set_content("VaR 95%", "—", tone="neutral")

    # ── Mise à jour des graphiques ───────────────────────────────────────

    def _update_charts(self, result):
        """Met à jour les graphiques principaux."""
        self._chart_trajectory.set_figure(self._build_trajectory_chart(result))
        self._chart_histogram.set_figure(self._build_histogram_chart(result))

    def _build_trajectory_chart(self, result) -> go.Figure:
        """Courbe déterministe ou fan chart Monte Carlo."""
        fig = go.Figure()

        median = result.median_series
        x_vals = list(range(len(median)))
        x_years = [v / 12.0 for v in x_vals]

        # Bande P10-P90 (Monte Carlo)
        if result.percentile_10_series is not None and result.percentile_90_series is not None:
            p10 = result.percentile_10_series
            p90 = result.percentile_90_series
            fig.add_trace(go.Scatter(
                x=x_years, y=p90.values,
                mode="lines", line=dict(width=0),
                showlegend=False, name="P90",
            ))
            fig.add_trace(go.Scatter(
                x=x_years, y=p10.values,
                mode="lines", line=dict(width=0),
                fill="tonexty", fillcolor="rgba(96,165,250,0.15)",
                showlegend=True, name="Intervalle P10–P90",
            ))

        # Médiane
        fig.add_trace(go.Scatter(
            x=x_years, y=median.values,
            mode="lines", line=dict(color="#60a5fa", width=3),
            name="Médiane",
        ))

        # Objectif
        goal = result.config.target_goal_amount
        if goal and goal > 0:
            fig.add_trace(go.Scatter(
                x=x_years, y=[goal] * len(x_years),
                mode="lines", line=dict(color="#f59e0b", width=2, dash="dash"),
                name=f"Objectif ({money(goal)})",
            ))

        fig.update_layout(**plotly_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        ))
        fig.update_xaxes(title="Années")
        fig.update_yaxes(title="Patrimoine net (€)")
        return fig

    def _build_histogram_chart(self, result) -> go.Figure:
        """Histogramme de la distribution du patrimoine final (Monte Carlo)."""
        fig = go.Figure()

        if result.trajectories_df is None or result.trajectories_df.empty:
            # Mode déterministe : pas d'histogramme
            fig.add_annotation(
                text="Histogramme disponible en mode Monte Carlo",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color=TEXT_MUTED),
            )
            fig.update_layout(**plotly_layout(
                margin=dict(l=10, r=10, t=20, b=10),
            ))
            return fig

        final_values = result.trajectories_df.iloc[-1].values

        fig.add_trace(go.Histogram(
            x=final_values,
            nbinsx=50,
            marker_color="rgba(96,165,250,0.6)",
            marker_line=dict(color="#60a5fa", width=1),
            name="Distribution finale",
        ))

        # Ligne médiane
        median_val = result.final_net_worth_median
        fig.add_vline(
            x=median_val, line_dash="dash", line_color="#60a5fa",
            annotation_text=f"Médiane: {money(median_val)}",
        )

        # Ligne objectif
        goal = result.config.target_goal_amount
        if goal and goal > 0:
            fig.add_vline(
                x=goal, line_dash="dot", line_color="#f59e0b",
                annotation_text=f"Objectif: {money(goal)}",
            )

        fig.update_layout(**plotly_layout(
            margin=dict(l=10, r=10, t=20, b=10),
        ))
        fig.update_xaxes(title="Patrimoine final (€)")
        fig.update_yaxes(title="Nombre de simulations")
        return fig

    # ── Section stress ───────────────────────────────────────────────────

    def _show_stress_section(self, stress_result):
        """Affiche la section stress avec comparaison baseline vs stress."""
        self._stress_section_title.setVisible(True)
        self._chart_stress.setVisible(True)
        self._kpi_stress_delta.setVisible(True)
        self._kpi_stress_drawdown.setVisible(True)
        self._kpi_stress_recovery.setVisible(True)

        # KPIs stress
        self._kpi_stress_delta.set_content(
            "Impact sur patrimoine final",
            _pct_signed(stress_result.delta_final_pct),
            subtitle=f"Delta: {money(stress_result.delta_final_net_worth)}",
            tone="alert" if stress_result.delta_final_pct < -0.1 else "neutral",
        )
        self._kpi_stress_drawdown.set_content(
            "Drawdown max (stress)",
            _pct(stress_result.max_drawdown_pct),
            subtitle=f"Point bas: {money(stress_result.lowest_net_worth)}",
            tone="neutral",
        )
        self._kpi_stress_recovery.set_content(
            "Recovery (pré-choc)",
            _months_display(stress_result.months_to_recover_pre_shock),
            subtitle=f"Baseline: {_months_display(stress_result.months_to_recover_baseline)}",
            tone="neutral",
        )

        # Chart comparatif
        self._chart_stress.set_figure(self._build_stress_chart(stress_result))

    def _hide_stress_section(self):
        """Cache la section stress."""
        self._stress_section_title.setVisible(False)
        self._chart_stress.setVisible(False)
        self._kpi_stress_delta.setVisible(False)
        self._kpi_stress_drawdown.setVisible(False)
        self._kpi_stress_recovery.setVisible(False)

    def _build_stress_chart(self, stress_result) -> go.Figure:
        """Graphique comparatif baseline vs stress."""
        fig = go.Figure()

        baseline = stress_result.baseline_result.median_series
        stressed = stress_result.stressed_result.median_series

        x_base = [i / 12.0 for i in range(len(baseline))]
        x_stress = [i / 12.0 for i in range(len(stressed))]

        fig.add_trace(go.Scatter(
            x=x_base, y=baseline.values,
            mode="lines", line=dict(color="#60a5fa", width=2.5),
            name="Baseline",
        ))
        fig.add_trace(go.Scatter(
            x=x_stress, y=stressed.values,
            mode="lines", line=dict(color="#ef4444", width=2.5),
            name=f"Stress: {stress_result.scenario.name}",
        ))

        fig.update_layout(**plotly_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        ))
        fig.update_xaxes(title="Années")
        fig.update_yaxes(title="Patrimoine net (€)")
        return fig

    # ── Diagnostics ──────────────────────────────────────────────────────

    def _update_diagnostics(self, result):
        """Affiche les diagnostics textuels."""
        if not result.diagnostics:
            self._diagnostics_label.setText("")
            return

        lines = ["Diagnostics :"]
        for diag in result.diagnostics:
            lines.append(f"  • {diag}")
        self._diagnostics_label.setText("\n".join(lines))

    # ── États d'affichage ────────────────────────────────────────────────

    def _set_empty_state(self):
        """État initial : aucune simulation lancée."""
        self._status_label.setStyleSheet(STYLE_STATUS)
        self._status_label.setText(
            "Configurez vos hypothèses puis cliquez sur « Lancer la simulation »."
        )
        self._kpi_final.set_content("Patrimoine final", "—", tone="neutral")
        self._kpi_median.set_content("Patrimoine actuel", "—", tone="neutral")
        self._kpi_p10.set_content("P10", "—", tone="neutral")
        self._kpi_p90.set_content("P90", "—", tone="neutral")
        self._kpi_proba.set_content("Probabilité", "—", tone="neutral")
        self._kpi_drawdown.set_content("Max drawdown", "—", tone="neutral")
        self._kpi_var.set_content("VaR 95%", "—", tone="neutral")
        self._diagnostics_label.setText("")
        self._hide_stress_section()

        # Charts vides
        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text="Aucune simulation lancée",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color=TEXT_MUTED),
        )
        empty_fig.update_layout(**plotly_layout(
            margin=dict(l=10, r=10, t=20, b=10),
        ))
        self._chart_trajectory.set_figure(empty_fig)
        self._chart_histogram.set_figure(empty_fig)

    def _set_loading_state(self):
        """État chargement."""
        self._btn_run.setEnabled(False)
        self._status_label.setStyleSheet(STYLE_STATUS_WARNING)
        self._status_label.setText("Simulation en cours…")

    def _set_error_state(self, message: str):
        """État erreur."""
        self._status_label.setStyleSheet(STYLE_STATUS_ERROR)
        self._status_label.setText(f"Erreur : {message}")

        logger.warning("Prevision avancée — erreur: %s", message)
