"""
Sistema de Rentabilidad - Aplicación principal
Herramientas:
  1. Analizador de Costos y Precios
  2. Estado de Situación de Rentabilidad
  3. Cash Flow Proyectado
"""

import streamlit as st
from pathlib import Path
import sys

# Asegurar que el path del proyecto esté disponible
sys.path.insert(0, str(Path(__file__).parent))

from utils.auth import require_auth, logout, get_current_user, init_session
from utils.database import (
    get_companies_by_user,
    create_company,
    log_usage,
    get_usage_summary,
)

# ─── Configuración de la página ────────────────────────────────
st.set_page_config(
    page_title="Sistema de Rentabilidad",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos mínimos
st.markdown(
    """
    <style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #666;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #4f46e5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def sidebar():
    """Barra lateral con navegación y selección de empresa."""
    user = get_current_user()

    with st.sidebar:
        st.markdown(f"### 👤 {user.get('full_name') or user['username']}")
        st.caption(user["email"])

        st.divider()

        # ── Selección / creación de empresa ─────────────────────
        companies = get_companies_by_user(user["id"])

        if companies:
            company_names = {c["name"]: c["id"] for c in companies}
            selected_name = st.selectbox(
                "Empresa activa",
                options=list(company_names.keys()),
                index=0
                if st.session_state.company_id is None
                else list(company_names.values()).index(st.session_state.company_id)
                if st.session_state.company_id in company_names.values()
                else 0,
            )
            st.session_state.company_id = company_names[selected_name]
            st.session_state.company_name = selected_name
        else:
            st.info("Todavía no tenés ninguna empresa. Creá una abajo.")

        with st.expander("➕ Nueva empresa"):
            with st.form("new_company_form"):
                name = st.text_input("Nombre de la empresa")
                industry = st.text_input("Rubro / Industria (opcional)")
                currency = st.selectbox("Moneda", ["ARS", "USD", "EUR", "BRL"], index=0)
                if st.form_submit_button("Crear empresa"):
                    if name.strip():
                        cid = create_company(user["id"], name.strip(), industry, currency)
                        log_usage(user["id"], "create_company", company_id=cid, details=name)
                        st.session_state.company_id = cid
                        st.session_state.company_name = name.strip()
                        st.success(f"Empresa '{name}' creada")
                        st.rerun()
                    else:
                        st.error("El nombre es obligatorio")

        st.divider()

        # ── Navegación ──────────────────────────────────────────
        st.markdown("### 🛠️ Herramientas")

        page = st.radio(
            "Ir a:",
            options=[
                "🏠 Inicio",
                "1️⃣ Analizador de Costos y Precios",
                "2️⃣ Estado de Situación de Rentabilidad",
                "3️⃣ Cash Flow Proyectado",
                "📈 Informes de Uso del Sistema",
            ],
            label_visibility="collapsed",
        )

        st.divider()
        if st.button("Cerrar sesión", use_container_width=True):
            logout()

        return page


def page_home():
    """Página de inicio / dashboard."""
    user = get_current_user()
    st.markdown('<p class="main-header">Sistema de Rentabilidad</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Herramientas para que tu negocio sea rentable, estable y pueda escalar</p>',
        unsafe_allow_html=True,
    )

    if not st.session_state.company_id:
        st.warning("Seleccioná o creá una empresa en la barra lateral para empezar.")
        return

    st.success(f"Empresa activa: **{st.session_state.company_name}**")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 1️⃣ Analizador de Costos y Precios")
        st.write(
            "Cargá tus costos y mirá el **margen real** de tu producto estrella. "
            "Entendé si ahí se está yendo tu rentabilidad."
        )
        st.info("Ideal para: saber el precio mínimo y el margen real.")

    with col2:
        st.markdown("#### 2️⃣ Estado de Situación de Rentabilidad")
        st.write(
            "Armá la **radiografía** de tu empresa y entendé cuánto ganás realmente. "
            "Respondé la pregunta: *¿Estoy ganando o perdiendo?*"
        )
        st.info("Ideal para: ver el panorama completo de la rentabilidad.")

    with col3:
        st.markdown("#### 3️⃣ Cash Flow Proyectado")
        st.write(
            "Armá tu flujo de fondos proyectado, mirá tus saldos con anticipación "
            "y tomá decisiones antes de llegar a fin de mes en rojo."
        )
        st.info("Ideal para: proyectar estabilidad y anticipar problemas de liquidez.")

    st.divider()
    st.markdown("### 📊 Resumen rápido de uso")
    summary = get_usage_summary(user["id"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Acciones totales", summary["total_actions"])
    m2.metric("Herramientas usadas", len(summary["by_tool"]))
    m3.metric("Días activos (últ. 7)", len(summary["last_7_days"]))


def page_usage_reports():
    """Informes de uso del sistema."""
    from utils.database import get_usage_logs, get_usage_summary
    import pandas as pd
    import plotly.express as px

    user = get_current_user()
    st.markdown("## 📈 Informes de Uso del Sistema")
    st.caption("Registro de todas las acciones realizadas dentro de la plataforma.")

    summary = get_usage_summary(user["id"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de acciones", summary["total_actions"])
    col2.metric("Herramientas distintas", len(summary["by_tool"]))
    col3.metric("Días activos (7 días)", len(summary["last_7_days"]))

    st.divider()

    # Gráfico por herramienta
    if summary["by_tool"]:
        st.subheader("Uso por herramienta")
        df_tool = pd.DataFrame(
            list(summary["by_tool"].items()), columns=["Herramienta", "Cantidad"]
        )
        fig = px.bar(df_tool, x="Herramienta", y="Cantidad", color="Herramienta")
        st.plotly_chart(fig, use_container_width=True)

    # Últimos logs
    st.subheader("Últimas acciones")
    logs = get_usage_logs(user_id=user["id"], limit=50)
    if logs:
        df = pd.DataFrame(logs)
        df = df[["created_at", "action", "tool", "details"]]
        df.columns = ["Fecha", "Acción", "Herramienta", "Detalle"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no hay registros de uso.")


# ─── Punto de entrada ──────────────────────────────────────────
def main():
    init_session()
    require_auth()  # Si no está logueado, muestra login y se detiene

    page = sidebar()

    if page == "🏠 Inicio":
        page_home()
    elif page == "1️⃣ Analizador de Costos y Precios":
        from modules.cost_price_analyzer import render as render_analyzer
        render_analyzer()
    elif page == "2️⃣ Estado de Situación de Rentabilidad":
        from modules.profitability_status import render as render_status
        render_status()
    elif page == "3️⃣ Cash Flow Proyectado":
        from modules.cashflow_projected import render as render_cashflow
        render_cashflow()
    elif page == "📈 Informes de Uso del Sistema":
        page_usage_reports()


if __name__ == "__main__":
    main()
