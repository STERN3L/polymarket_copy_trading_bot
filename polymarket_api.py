# Fichier : polymarket_api.py
import streamlit as st
import requests
import time
import json
from datetime import datetime
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType
from py_clob_client.constants import POLYGON
import pandas as pd

# URL de l'API de données de Polymarket
DATA_API_URL = "https://data-api.polymarket.com"
CLOB_HOST = "https://clob.polymarket.com"


def start_copy_engine():
    """ Démarre le moteur de copy trading. """
    st.session_state.copy_engine_running = True
    st.session_state.monitoring_status = "✅ Démarré. Connexion CLOB en attente..."
    st.toast("🚀 Moteur de Copy Trading DÉMARRÉ.")
    st.rerun()

def stop_copy_engine():
    """ Arrête le moteur de copy trading. """
    st.session_state.copy_engine_running = False
    st.session_state.monitoring_status = "🛑 Moteur de Copy Trading Arrêté."
    st.toast("🛑 Moteur de Copy Trading ARRÊTÉ.")
    st.rerun()

# --- Fonctions API de Polymarket (Inspirées de nice_funcs.py) ---

def fetch_wallet_activity(user_address: str, limit: int = 10) -> list[dict] | None:
    """ Récupère les N dernières activités (trades) d'un wallet. """
    url = f"{DATA_API_URL}/activity?user={user_address}&limit={limit}&offset=0"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status() # Lève une exception pour les codes 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération de l'activité du wallet {user_address}: {e}")
        return None

def fetch_current_trades(wallet_to_copy: str) -> pd.DataFrame:
    """ Récupère les trades en cours (positions) du wallet cible. """
    # L'API /positions renvoie les positions ouvertes
    url = f"{DATA_API_URL}/positions?user={wallet_to_copy}&limit=1000&offset=0"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Convertir en DataFrame pour un traitement facile
        df = pd.DataFrame(data)
        
        # Filtrer potentiellement pour seulement les positions 'actives' si l'API ne le fait pas nativement
        if not df.empty:
            df['endDate'] = pd.to_datetime(df['endDate'])
            today = datetime.now()
            df = df[df['endDate'] >= today]
            
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération des positions: {e}")
        return pd.DataFrame()


# --- Logique de Surveillance et de Trading (Moteur du Copy Trading) ---

def create_clob_client(funder_address: str) -> ClobClient:
    """ Crée et configure le client CLOB de Polymarket pour l'exécution d'ordres. 
        ATTENTION: Nécessite les vraies clés privées/API dans les variables d'environnement.
    """
    # Remplacez ceci par la lecture de vos variables d'environnement (.env)
    key = st.session_state.private_key_user_wallet # Vous devrez ajouter ce champ dans la configuration
    creds = ApiCreds(
        api_key='VOTRE_CLOB_API_KEY', # A récupérer manuellement
        api_secret='VOTRE_CLOB_SECRET',
        api_passphrase='VOTRE_CLOB_PASS_PHRASE',
    )
    chain_id = POLYGON
    
    # Utilisation de signature_type=2 si c'est un Metamask (comme dans l'exemple doc)
    # ou signature_type=1 si c'est Magic/Email. On suppose EOA/Metamask direct (signature_type=2)
    try:
        client = ClobClient(CLOB_HOST, key=key, chain_id=chain_id, creds=creds, signature_type=2, funder=funder_address)
        client.set_api_creds(client.create_or_derive_api_creds())
        return client
    except Exception as e:
        st.error(f"Erreur d'initialisation du client CLOB : {e}")
        return None


def execute_copy_trade(client: ClobClient, target_trade: dict, ratio_percentage: float):
    """ Exécute un ordre en fonction du trade cible et du ratio de copie. """
    
    # Assurez-vous que l'actif est bien le Token ID Polymarket (asset/token_id)
    token_id = target_trade.get('asset')
    target_usdc_size = target_trade.get('usdcSize', 0.0) # Taille du trade cible en USDC
    target_price = target_trade.get('price', 0.50)      # Prix de la position (Ex: 0.50 $)
    side = target_trade.get('side')                     # BUY ou SELL
    
    if not token_id or not side:
        print("Données de trade invalides pour l'exécution.")
        return

    # 1. Calculer la taille de la mise en USDC (Ratio de copie direct)
    user_usdc_size = target_usdc_size * (ratio_percentage / 100.0)

    # 2. Calculer la 'size' (nombre de tokens) à acheter/vendre
    # size = montant_en_USDC / prix_du_token
    # Exemple : 50 USDC / 0.50$ = 100 tokens
    if target_price > 0:
        size_tokens = user_usdc_size / target_price
    else:
        print("Prix du token invalide.")
        return

    # On utilise le prix actuel du marché (ou le prix du trade cible pour un Limit Order)
    order_args = OrderArgs(
        price=target_price,
        size=size_tokens,
        side=side, # BUY ou SELL
        token_id=token_id
    )

    try:
        signed_order = client.create_order(order_args)
        resp = client.post_order(signed_order, OrderType.GTC)
        
        st.session_state.last_trade_executed = {
            "market": target_trade.get('title', 'N/A'),
            "amount": user_usdc_size,
            "side": side,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.success(f"✅ Trade copié avec succès : {side} {user_usdc_size:.2f} USDC sur {target_trade.get('title')}")
        print(resp)
        return True
    
    except Exception as e:
        st.error(f"❌ Erreur lors de l'exécution du trade : {e}")
        return False
        
        
def monitor_new_trades(wallet_to_copy: str, last_trade_hash: str | None) -> tuple[list[dict], str | None]:
    """ 
    Vérifie l'activité récente du wallet cible et identifie les NOUVEAUX trades.
    Retourne la liste des nouveaux trades et le hash du tout dernier trade.
    """
    if not wallet_to_copy or wallet_to_copy == "0x...":
        return [], last_trade_hash

    recent_activity = fetch_wallet_activity(wallet_to_copy, limit=5)
    
    if not recent_activity:
        return [], last_trade_hash
        
    new_trades = []
    
    # Le hash du trade le plus récent (le premier dans la liste)
    latest_hash = recent_activity[0].get('transactionHash') 

    # S'il n'y a pas de hash précédent ou si le dernier hash est différent
    if not last_trade_hash or latest_hash != last_trade_hash:
        
        for trade in recent_activity:
            trade_hash = trade.get('transactionHash')
            # L'API renvoie les trades dans l'ordre chronologique inverse
            if trade_hash == last_trade_hash: 
                break # On a atteint le dernier trade connu
            
            # Filtre : on ne veut que les événements de type 'TRADE'
            if trade.get('type') == 'TRADE':
                # Ajoutez le trade en début de liste pour conserver l'ordre chronologique
                new_trades.append(trade) 
        
        # Inverser la liste pour avoir l'ordre chronologique
        new_trades.reverse()
        
    return new_trades, latest_hash