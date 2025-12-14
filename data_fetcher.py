import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import random
import polymarket_api 
import numpy as np

def get_live_trades_data() -> pd.DataFrame:
    """ 
    Récupère les positions actives du wallet cible et construit le tableau pour l'affichage. 
    """
    wallet_to_copy = st.session_state.wallet_to_copy
    ratio_percentage = st.session_state.adjustment_percent
    
    # Utilisation du nouveau module pour récupérer les positions actives
    df_positions = polymarket_api.fetch_current_trades(wallet_to_copy)
    
    if df_positions.empty:
        return pd.DataFrame({
            'Nom du Trade': ['Aucun trade en cours'],
            'Montant Utilisateur (USDC)': [0],
            'Ajustement (%)': [f"{ratio_percentage:.2f}"],
            'Montant Copié (USDC)': [0],
            'Date d\'Ouverture': ['-'],
            'Type': ['-']
        })

    # Traitement des données pour l'affichage :
    df_positions['Montant Copié (USDC)'] = df_positions['initialValue'] 
    
    # Calcul de la mise de l'utilisateur
    df_positions['Montant Utilisateur (USDC)'] = df_positions['Montant Copié (USDC)'] * (ratio_percentage / 100.0)

    # Renommage des colonnes (à ajuster selon la réponse réelle de l'API /positions)
    df_positions = df_positions.rename(columns={
        'title': 'Nom du Trade',
        'side': 'Type', # Note: 'side' est peut-être absent des positions, utilisez 'outcome' ou 'asset'
        'timestamp': 'Date d\'Ouverture',
    })
    
    # Sélection des colonnes finales
    df_positions['Ajustement (%)'] = f"{ratio_percentage:.2f}"
    
    return df_positions[[
        'Nom du Trade', 
        'Montant Utilisateur (USDC)', 
        'Ajustement (%)', 
        'Montant Copié (USDC)', 
        # Remplacer 'Date d\'Ouverture' par la colonne correcte de l'API
        'endDate' # En l'absence de la date d'ouverture, on garde la date de fin
    ]].head(10) # Limiter à 10 trades pour la lisibilité




def get_valorization_history():
    """ Récupère l'historique de valorisation quotidienne (simulé ou DB locale). """
    days = 30
    dates = [date.today() - timedelta(days=i) for i in range(days)]
    
    # Simuler une croissance légère et aléatoire
    values = [st.session_state.initial_capital * (1 + 0.005 * i + random.uniform(-0.01, 0.01)) for i in range(days)]
    values.sort() 
    
    # Mise à jour du capital actuel pour la simulation
    st.session_state.current_capital = values[-1] 
    
    return pd.DataFrame({
        'Date': dates,
        'Capital (USDC)': values
    }).sort_values('Date')



def get_user_trades_history() -> pd.DataFrame:
    """ 
    Récupère l'historique des trades EXÉCUTÉS par le bot de l'utilisateur.
    (Actuellement simulé car nous n'avons pas de DB).
    """
    
    # Données simulées pour votre portefeuille (doit être remplacé par une lecture DB)
    data = {
        'Nom du Trade': ['ETH vs BTC', 'Taux FED', 'Inflation US'],
        'Montant Utilisateur (USDC)': [350.50, 1500.00, 75.25],
        'Ratio Copié (%)': [st.session_state.adjustment_percent, 50.0, 10.0],
        'Montant Cible (USDC)': [350.50 * 100/st.session_state.adjustment_percent, 3000.00, 752.50],
        'Date d\'Exécution': [datetime.now() - timedelta(hours=2), datetime.now() - timedelta(days=1), datetime.now() - timedelta(days=5)],
        'Type': ['Achat (OUI)', 'Vente (NON)', 'Achat (OUI)'],
    }
    df = pd.DataFrame(data)
    df['Date d\'Exécution'] = pd.to_datetime(df['Date d\'Exécution'])
    return df.sort_values(by='Date d\'Exécution', ascending=False)


def get_target_wallet_activity() -> pd.DataFrame:
    """ 
    Récupère l'historique récent d'activité (trades) du wallet cible via l'API.
    """
    wallet_to_copy = st.session_state.wallet_to_copy
    
    # Limite de 20 activités récentes pour l'affichage
    activity_data = polymarket_api.fetch_wallet_activity(wallet_to_copy, limit=20)
    
    if not activity_data:
        return pd.DataFrame({
            'Statut': ['Aucune activité trouvée ou erreur API.']
        })

    # Conversion en DataFrame
    df = pd.DataFrame(activity_data)
    
    # Filtrer uniquement les vrais trades si possible (l'API renvoie des 'TRADE', 'ADD_LIQUIDITY', etc.)
    df_trades = df[df['type'] == 'TRADE'].copy()

    if df_trades.empty:
         return pd.DataFrame({
            'Statut': ['Aucun trade récent trouvé pour ce wallet.']
        })

    # Traitement des colonnes pour l'affichage
    # L'API utilise le timestamp UNIX ('timestamp')
    df_trades['Date/Heure'] = pd.to_datetime(df_trades['timestamp'], unit='s')
    
    # Sélection des colonnes pertinentes (celles-ci dépendent de la réponse réelle de l'API)
    df_trades = df_trades.rename(columns={
        'title': 'Nom du Marché',
        'usdcSize': 'Montant (USDC)',
        'side': 'Type de Trade (BUY/SELL)',
        'price': 'Prix Token'
    })
    
    return df_trades[[
        'Date/Heure', 
        'Nom du Marché', 
        'Montant (USDC)', 
        'Type de Trade (BUY/SELL)', 
        'Prix Token', 
        'outcome' # Résultat ciblé (YES/NO)
    ]].sort_values(by='Date/Heure', ascending=False)