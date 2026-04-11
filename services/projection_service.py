"""
services/projection_service.py

Point d'entrée unique pour la génération de projections patrimoniales.
Ce service agit comme un routeur (façade) permettant d'appeler de manière transparente 
soit l'ancien moteur (V1 déterministe simple, legacy), soit le nouveau moteur de prévision 
(probabiliste Monte Carlo, ou déterministe avancé).

Il respecte le comportement actuel inchangé et évite une migration massive de l'UI.
"""

import pandas as pd
from typing import Literal, Any, Dict, Optional, Union

# --- Imports Legacy (V1) ---
from services.projections import (
    ScenarioParams,
    get_projection_base_for_scope as legacy_get_base,
    run_projection as legacy_run_projection,
)

# --- Imports Advanced (Prevision) ---
from services.prevision import (
    run_prevision,
    PrevisionConfig,
    PrevisionResult
)


class ProjectionService:
    """
    Service unifiant l'accès aux générateurs de projections et prévisions patrimoniales.
    Il permet une migration incrémentale.
    """

    @staticmethod
    def run_legacy_projection(
        conn: Any,
        scope_type: Literal["family", "person"],
        scope_id: Optional[int],
        params: ScenarioParams,
        exclude_primary_residence: bool = False
    ) -> pd.DataFrame:
        """
        Exécute la projection classique (V1) avec le moteur existant (services.projections).

        Args:
            conn: Connexion à la base de données.
            scope_type: "family" ou "person".
            scope_id: L'identifiant de la personne (ou None pour "family").
            params: Paramètres du scénario de projection.
            exclude_primary_residence: Booléen indiquant si la RP doit être exclue des actifs.

        Returns:
            pd.DataFrame: Un dataframe contenant les données mensuelles de projection.
        """
        base = legacy_get_base(
            conn=conn, 
            scope_type=scope_type, 
            scope_id=scope_id, 
            exclude_primary_residence=exclude_primary_residence
        )
        return legacy_run_projection(base, params)

    @staticmethod
    def run_advanced_prevision(
        conn: Any,
        scope_type: Literal["family", "person"],
        scope_id: int,
        config: PrevisionConfig,
        engine: Literal["deterministic", "monte_carlo"] = "monte_carlo"
    ) -> PrevisionResult:
        """
        Exécute la nouvelle prévision avancée avec services.prevision.

        Args:
            conn: Connexion à la base de données.
            scope_type: "family" ou "person".
            scope_id: L'identifiant cible (pour family, souvent 1).
            config: L'objet complet de configuration des prévisions (PrevisionConfig).
            engine: Le type de moteur spécifique ("monte_carlo" par défaut ou "deterministic").

        Returns:
            PrevisionResult: Les résultats enrichis (séries médianes, percentiles, métriques).
        """
        return run_prevision(
            conn=conn, 
            scope_type=scope_type, 
            scope_id=scope_id, 
            config=config, 
            engine=engine
        )

    @classmethod
    def generate_projection(
        cls,
        conn: Any,
        scope_type: Literal["family", "person"],
        scope_id: Optional[int],
        engine_type: Literal["legacy", "advanced"] = "legacy",
        options: Optional[Dict[str, Any]] = None
    ) -> Union[pd.DataFrame, PrevisionResult]:
        """
        API unique agissant comme routeur principal pour les projections.
        
        Args:
            conn: Connexion à de la base de données.
            scope_type: "family" ou "person".
            scope_id: Identifiant de l'entité (peut être None pour legacy family).
            engine_type: Choisir "legacy" pour l'ancien moteur, "advanced" pour le nouveau.
            options: Dictionnaire avec les clés requises par le type de moteur:
                     - "legacy": "params" (ScenarioParams obligatoire), "exclude_primary_residence" (optionnel).
                     - "advanced": "config" (PrevisionConfig obligatoire), "engine" (optionnel).

        Returns:
            L'objet résultant en fonction du moteur (DataFrame ou PrevisionResult).
        """
        if options is None:
            options = {}

        if engine_type == "legacy":
            params = options.get("params")
            if not isinstance(params, ScenarioParams):
                raise ValueError("L'option 'params' (type ScenarioParams) est requise pour engine_type='legacy'.")
            
            exc_rp = bool(options.get("exclude_primary_residence", False))
            return cls.run_legacy_projection(conn, scope_type, scope_id, params, exc_rp)

        elif engine_type == "advanced":
            config = options.get("config")
            # En duck typing on s'assure juste que ce n'est pas None (pour éviter les soucis d'import circulaires/types complexes)
            if config is None:
                raise ValueError("L'option 'config' (type PrevisionConfig) est requise pour engine_type='advanced'.")
            
            engine = options.get("engine", "monte_carlo")
            # scope_id est souvent 1 pour "family" dans les nouvelles APIs.
            resolved_scope_id = scope_id if scope_id is not None else 1
            
            return cls.run_advanced_prevision(conn, scope_type, resolved_scope_id, config, engine)

        else:
            raise ValueError(f"Type de moteur '{engine_type}' non reconnu. Utilisez 'legacy' ou 'advanced'.")
