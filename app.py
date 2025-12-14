import plotly.express as px
import streamlit as st
import pandas as pd
import random
import numpy as np
from datetime import date, timedelta, datetime 


# Import des modules locaux
import config_manager
import polymarket_api # Import du module renommé
import data_fetcher

# --- Configuration de la Page Streamlit ---
st.set_page_config(
    page_title="Polymarket Copy Trader Pro",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation des variables de session
config_manager.initialize_session_state()

# Ajout de l'état de surveillance dans la session state
if 'last_trade_hash' not in st.session_state:
    st.session_state.last_trade_hash = None # Pour suivre le dernier trade vu
if 'monitoring_status' not in st.session_state:
    st.session_state.monitoring_status = "Initialisation..."


# --- Fonction principale de surveillance (déclenchée à chaque rafraîchissement Streamlit) ---

def run_monitoring_cycle():
    """ Fonction de vérification exécutée périodiquement. """
    if st.session_state.copy_engine_running:
        wallet = st.session_state.wallet_to_copy
        ratio = st.session_state.adjustment_percent
        
        # 1. Vérification des nouveaux trades
        new_trades, new_hash = polymarket_api.monitor_new_trades(wallet, st.session_state.last_trade_hash)
        
        if new_hash and new_hash != st.session_state.last_trade_hash:
             st.session_state.last_trade_hash = new_hash
             st.session_state.monitoring_status = f"Nouveau trade détecté! Hash: {new_hash[:8]}..."
        
        if new_trades:
            st.session_state.monitoring_status = f"🚨 {len(new_trades)} NOUVEAUX TRADES DETECTÉS. Démarrage de la copie..."
            
            # Tenter d'initialiser le client CLOB pour l'exécution
            # NOTE: La gestion des clés privées doit être sécurisée!
            clob_client = polymarket_api.create_clob_client(st.session_state.user_wallet)
            
            if clob_client:
                for trade in new_trades:
                    # 2. Exécution de la copie
                    polymarket_api.execute_copy_trade(clob_client, trade, ratio)
            else:
                 st.session_state.monitoring_status = "⚠️ CLOB Client non initialisé. Impossible d'exécuter les trades."
        
        else:
             st.session_state.monitoring_status = f"✅ Monitoring actif. Dernier check à {datetime.now().strftime('%H:%M:%S')}. (Hash: {st.session_state.last_trade_hash[:8] if st.session_state.last_trade_hash else 'N/A'})"
    else:
         st.session_state.monitoring_status = "🛑 Moteur de Copy Trading Arrêté."


# --- Fonctions de Rendu des Pages ---

def render_wallet_config_page():
    """ Rend la page de configuration des wallets. """
    st.header("⚙️ Configuration des Wallets")
    st.markdown("---")
    
    st.subheader("Adresses des Wallets")
    
    with st.form("wallet_form"):
        new_wallet_to_copy = st.text_input(
            "Adresse du **Wallet à Copier** :", 
            value=st.session_state.wallet_to_copy, 
        )
        new_user_wallet = st.text_input(
            "Adresse du **Wallet Utilisateur** (pour les trades) :", 
            value=st.session_state.user_wallet, 
        )
        new_usdc_wallet = st.text_input(
            "Adresse du **Wallet USDC** (pour le gaz/financement) :", 
            value=st.session_state.usdc_wallet, 
        )
        
        st.subheader("Clé d'Accès pour l'Exécution des Trades")
        st.warning(
            "⚠️ **Avertissement de sécurité** : La clé privée est nécessaire pour signer les transactions. "
            "Ne jamais utiliser une clé contenant des fonds importants."
        )
        new_private_key = st.text_input(
            "Clé Privée du Wallet Utilisateur :", 
            value=st.session_state.get('private_key_user_wallet', 'Votre clé privée...'), 
            type="password", # Masque l'entrée pour plus de sécurité
            key="new_private_key"
        )
        
        if st.form_submit_button("💾 Sauvegarder les Configurations"):
            config_manager.save_wallet_config(new_wallet_to_copy, new_user_wallet, new_usdc_wallet)
            st.session_state.private_key_user_wallet = new_private_key # Sauvegarde la clé
            st.toast("💾 Configuration des wallets sauvegardée !")


def render_target_monitoring_page():
    """ Rend la page dédiée à la surveillance du wallet cible. """
    st.header("👀 Surveillance du Wallet Cible")
    st.markdown("---")
    
    wallet = st.session_state.wallet_to_copy
    if wallet == "0x...":
        st.error("Veuillez configurer l'adresse du Wallet à Copier dans la section 'Configuration des Wallets'.")
        return

    st.info(f"Affichage des 20 dernières activités de type 'TRADE' pour l'adresse : `{wallet}`")
    
    # Récupération des données via le data_fetcher
    df_trades = data_fetcher.get_target_wallet_activity()
    
    if df_trades.empty:
        st.warning("Aucune donnée de trade récente disponible. Vérifiez l'adresse ou le statut de l'API.")
    else:
        st.dataframe(
            df_trades, 
            use_container_width=True,
            hide_index=True
        )


def render_trading_params_page():
    """ Rend la page des paramètres de trading avec la logique de pourcentage direct. """
    st.header("💰 Paramètres de Trading")
    st.markdown("---")
    
    # La valeur dans la session state est un pourcentage entier (ex: 100 pour 100%)
    # On la divise par 100 pour obtenir la valeur réelle (ex: 100 -> 1.00) pour l'affichage initial
    initial_value = st.session_state.adjustment_percent / 100.0 
    
    with st.form("trading_form"):
        
        st.subheader("Ratio de Copie Directe")
        st.markdown(
            """
            Ce paramètre définit la taille de votre mise par rapport à la mise du trader ciblé.
            
            $$\\text{Votre Mise} = \\text{Mise Cible} \\times \\frac{\\text{Ratio Copie}}{100}$$
            """
        )
        
        # --- Champ de saisie numérique (Input Box) ---
        st.markdown("##### ✏️ Saisir le pourcentage de la mise cible à copier (0.10 à 100)")
        
        # Saisie de la valeur (de 0.10 à 100, pour le pourcentage)
        input_ratio = st.number_input(
            "Pourcentage de la Mise Cible (%) :",
            min_value=0.10, 
            max_value=100.00, 
            value=max(0.10, min(100.00, initial_value * 100)), # Assure que la valeur initiale est dans la plage [0.10, 100]
            step=0.10, 
            format="%.2f",
            key="input_ratio"
        )

        st.markdown("---")
        
        # --- Curseur pour la sélection rapide (Slider) ---
        st.markdown("##### 🖱️ Sélectionner rapidement (Pas de 1)")
        
        # Le curseur est basé sur les pourcentages (0 à 100) avec un pas de 1
        slider_ratio = st.slider(
            "Ratio de Copie (%) :",
            min_value=1, # Minimum pratique pour le curseur
            max_value=100, 
            value=int(input_ratio), # Synchronisé avec la valeur saisie
            step=1,
            key="slider_ratio"
        )
        
        # La valeur finale à sauvegarder est celle du champ de saisie (plus précise)
        final_ratio = max(0.10, min(100.00, input_ratio)) 
        
        st.info(
            f"**Ratio actuel : {final_ratio:.2f} %**\n\n"
            f"- Si le trader cible mise 1000 USDC, vous miserez : **{1000 * final_ratio / 100:.2f} USDC**."
        )

        if st.form_submit_button("💾 Mettre à Jour les Paramètres"):
            # Sauvegarde de la valeur en pourcentage (ex: 1 pour 1%, 100 pour 100%)
            # Nous utilisons la valeur du champ de saisie (input_ratio) car elle est plus précise.
            config_manager.save_trading_config(final_ratio)


def render_dashboard_page():
    """ Rend la page principale du tableau de bord. """
    st.header("📊 Tableau de Bord du Copy Trading")
    st.markdown("---")

    # --- Synthèse du Portefeuille (Tableau Supérieur) ---
    st.subheader("Synthèse du Portefeuille")
    
    initial_cap = st.session_state.initial_capital
    
    # Les données de valorisation sont lues ici pour mettre à jour current_capital
    df_valorization = data_fetcher.get_valorization_history()
    current_cap = st.session_state.current_capital # Mis à jour par data_fetcher
    
    # Calcul de la performance
    performance = ((current_cap - initial_cap) / initial_cap) * 100 if initial_cap > 0 else 0
    delta_value = current_cap - initial_cap
        
    col1, col2, col3 = st.columns(3)
    
    col1.metric("Capital Initial (USDC)", f"{initial_cap:,.2f} $")
    col2.metric("Capital Actuel (USDC)", f"{current_cap:,.2f} $", f"{delta_value:,.2f} $")
    col3.metric("Performance (%)", f"{performance:.2f} %", delta=f"{performance:.2f} %")
    
    st.markdown("---")

    # --- Graphique de Valorisation ---
    st.subheader("Valorisation Quotidienne du Portefeuille")
    
    fig = px.line(
        df_valorization, 
        x='Date', 
        y='Capital (USDC)', 
        title='Évolution du Capital de l\'Utilisateur',
        markers=True
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Capital (USDC)",
        plot_bgcolor="#1E1E1E",
        paper_bgcolor="#1E1E1E",
        font=dict(color="white"),
        margin=dict(t=50, b=50, l=50, r=50)
    )
    fig.update_traces(line_color='#4CAF50', line_width=3)
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # --- Tableau des Trades en Cours ---
    st.subheader(f"Historique des Trades COPIÉS (Ratio : {st.session_state.adjustment_percent:.2f}%)")
    
    df_trades_user = data_fetcher.get_user_trades_history()
    
    st.dataframe(
        df_trades_user, 
        use_container_width=True,
        hide_index=True
    )

    if not st.session_state.copy_engine_running:
        st.warning("⚠️ Les données affichées ci-dessus sont des exemples simulés (historique du bot).")


# --- Fonction Principale de l'Application ---

def main():
    run_monitoring_cycle()
    # --- 1. Navbar (Barre de Navigation Supérieure) ---
    st.markdown("""
        <style>
        .header-title { font-size: 1.8em; font-weight: bold; color: #4CAF50; }
        .status-indicator { font-size: 1em; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
        .running { background-color: #28a745; color: white; }
        .stopped { background-color: #dc3545; color: white; }
        </style>
    """, unsafe_allow_html=True)

    if st.session_state.copy_engine_running:
        status_class = "running"
    else:
        status_class = "stopped"

    col_title, col_status, col_control = st.columns([4, 2, 2])
    
    with col_title:
        st.markdown(f"<div class='header-title'>🤖 Polymarket Copy Trader</div>", unsafe_allow_html=True)
    
    with col_status:
        # Affichage du statut de surveillance
        st.markdown(f"<div class='status-indicator {status_class}'>{st.session_state.monitoring_status}</div>", unsafe_allow_html=True)
    
    with col_control:
        # Les fonctions start/stop sont maintenant dans polymarket_api
        if st.session_state.copy_engine_running:
            st.button("🛑 Arrêter le Moteur", on_click=polymarket_api.stop_copy_engine, type="secondary")
        else:
            st.button("🚀 Démarrer le Moteur", on_click=polymarket_api.start_copy_engine, type="primary")

    # --- 2. Sidebar (Menu à Gauche) ---
    st.sidebar.title("Menu de Navigation")

    menu_choice = st.sidebar.radio(
        "Choisissez une section :",
        # *** AJOUT DE LA NOUVELLE SECTION ***
        ("📊 Tableau de Bord", "👀 Surveillance du Wallet Cible", "⚙️ Configuration des Wallets", "💰 Paramètres de Trading")
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Wallet Cible : {st.session_state.wallet_to_copy[:6]}...")
    st.sidebar.caption("Développé avec Streamlit et Python.")

    # --- 3. Routing du Contenu Principal ---
    if menu_choice == "⚙️ Configuration des Wallets":
        render_wallet_config_page()
    elif menu_choice == "💰 Paramètres de Trading":
        render_trading_params_page()
    elif menu_choice == "📊 Tableau de Bord":
        render_dashboard_page()
    # *** AJOUT DU ROUTING ***
    elif menu_choice == "👀 Surveillance du Wallet Cible":
        render_target_monitoring_page()

if __name__ == "__main__":
    main()