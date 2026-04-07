import logging
from .prevision_models import PrevisionBase

logger = logging.getLogger(__name__)

def build_prevision_base_for_scope(conn, scope_type: str, scope_id: int) -> PrevisionBase:
    """
    Construit la base patrimoniale de départ pour une projection.
    
    TODO: Actuellement, ceci utilise des hypothèses très simples pour le squelette.
    Il faudra brancher les vrais services (liquidites.get_liquidites_summary, etc.)
    pour lire les valeurs réelles depuis la DB sans refaire les calculs.
    """
    logger.info(f"Construction de la base de prévision pour {scope_type}={scope_id}")
    
    # HYPOTHESES PROVISOIRES
    # Dans la V2, on intégrera de manière agnostique l'existant :
    # liquidites = services.liquidites.get_liquidites_summary(conn, ...)
    # Ce fonctionnement assure qu'on respecte la règle UI -> Services -> DB
    
    # Base bouchonnée pour la V1
    base = PrevisionBase(
        current_net_worth=100000.0,
        current_cash=20000.0,
        current_equity=80000.0,
        current_real_estate=0.0
    )
    
    return base
