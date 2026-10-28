"""
Gestión de sesión de usuario en Streamlit.
"""

import streamlit as st
from utils.database import authenticate_user, create_user, log_usage, get_user_by_id


def init_session():
    """Inicializa las variables de sesión necesarias."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "company_id" not in st.session_state:
        st.session_state.company_id = None
    if "company_name" not in st.session_state:
        st.session_state.company_name = None


def login_form():
    """Muestra el formulario de login / registro."""
    st.markdown("## 🔐 Acceso al Sistema de Rentabilidad")

    tab_login, tab_register = st.tabs(["Iniciar sesión", "Crear cuenta"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Completá usuario y contraseña")
                else:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = dict(user)
                        log_usage(user["id"], "login", tool="auth")
                        st.success(f"¡Bienvenido/a, {user['full_name'] or user['username']}!")
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos")

    with tab_register:
        with st.form("register_form"):
            full_name = st.text_input("Nombre completo")
            username = st.text_input("Usuario (único)")
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            password2 = st.text_input("Repetir contraseña", type="password")
            submitted = st.form_submit_button("Crear cuenta", use_container_width=True)

            if submitted:
                if not all([username, email, password, password2]):
                    st.error("Completá todos los campos")
                elif password != password2:
                    st.error("Las contraseñas no coinciden")
                elif len(password) < 6:
                    st.error("La contraseña debe tener al menos 6 caracteres")
                else:
                    user_id = create_user(username, email, password, full_name)
                    if user_id:
                        st.success("Cuenta creada correctamente. Ahora iniciá sesión.")
                        log_usage(user_id, "register", tool="auth")
                    else:
                        st.error("Ese usuario o email ya existe")


def require_auth():
    """
    Debe llamarse al inicio de cada página.
    Si no está autenticado, muestra el login y detiene la ejecución.
    """
    init_session()
    if not st.session_state.authenticated:
        login_form()
        st.stop()


def logout():
    """Cierra la sesión."""
    if st.session_state.user:
        log_usage(st.session_state.user["id"], "logout", tool="auth")
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.company_id = None
    st.session_state.company_name = None
    st.rerun()


def get_current_user():
    return st.session_state.get("user")


def get_current_company_id():
    return st.session_state.get("company_id")
