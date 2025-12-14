import streamlit as st

def initialize_session_state():
    """ Initialise les variables de session si elles n'existent pas. """
    if 'wallet_to_copy' not in st.session_state:
        st.session_state.wallet_to_copy = "0x..." 
        st.session_state.user_wallet = "0x..."
        st.session_state.usdc_wallet = "0x..."
        st.session_state.adjustment_percent = 100 
        st.session_state.copy_engine_running = False
        st.session_state.initial_capital = 5000 
        st.session_state.current_capital = 5000 
        st.session_state.private_key_user_wallet = ""

def save_wallet_config(new_wallet_to_copy, new_user_wallet, new_usdc_wallet):
    """ Sauvegarde les adresses des wallets dans l'état de session. """
    st.session_state.wallet_to_copy = new_wallet_to_copy
    st.session_state.user_wallet = new_user_wallet
    st.session_state.usdc_wallet = new_usdc_wallet
    st.toast("💾 Configuration des wallets sauvegardée !")

def save_trading_config(new_adjustment_percent):
    """ Sauvegarde le pourcentage d'ajustement de trading. """
    st.session_state.adjustment_percent = new_adjustment_percent
    st.toast("✅ Paramètres de trading mis à jour !")