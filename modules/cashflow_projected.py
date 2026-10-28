"""
Módulo 3: Cash Flow Proyectado
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from utils.auth import get_current_user
from utils.database import (
    get_cashflow_entries,
    create_cashflow_entry,
    delete_cashflow_entry,
    get_products,
    get_cost_items,
    log_usage,
)


def render():
    user = get_current_user()
    company_id = st.session_state.get("company_id")

    st.markdown("## 3️⃣ Cash Flow Proyectado")
    st.caption(
        "Armá tu flujo de fondos proyectado, mirá tus saldos con anticipación "
        "y tomá decisiones antes de llegar a fin de mes con las cuentas en rojo."
    )

    if not company_id:
        st.warning("Seleccioná o creá una empresa en la barra lateral.")
        return

    log_usage(user["id"], "open_tool", tool="cashflow_proyectado", company_id=company_id)

    tab1, tab2, tab3 = st.tabs(
        ["➕ Cargar movimientos", "📅 Proyección 12 meses", "📊 Escenarios"]
    )

    # ─── TAB 1: Cargar movimientos ──────────────────────────────
    with tab1:
        st.subheader("Registrar ingresos y egresos")

        with st.form("add_cashflow"):
            col1, col2 = st.columns(2)
            with col1:
                entry_date = st.date_input("Fecha", value=datetime.today())
                description = st.text_input("Descripción *")
                entry_type = st.selectbox("Tipo", ["ingreso", "egreso"])
            with col2:
                amount = st.number_input("Monto", min_value=0.0, step=100.0)
                category = st.text_input("Categoría (opcional)")
                is_projected = st.checkbox("Es proyectado (futuro)", value=True)
                scenario = st.selectbox(
                    "Escenario",
                    ["realista", "optimista", "pesimista"],
                    index=0,
                )

            if st.form_submit_button("Guardar movimiento"):
                if description.strip() and amount > 0:
                    create_cashflow_entry(
                        company_id,
                        entry_date.isoformat(),
                        description.strip(),
                        entry_type,
                        amount,
                        category,
                        is_projected,
                        scenario,
                    )
                    log_usage(
                        user["id"],
                        "create_cashflow",
                        tool="cashflow_proyectado",
                        company_id=company_id,
                        details=f"{entry_type}: {description}",
                    )
                    st.success("Movimiento guardado")
                    st.rerun()
                else:
                    st.error("Completá descripción y monto")

        # Listado de movimientos
        st.subheader("Movimientos cargados")
        entries = get_cashflow_entries(company_id)
        if entries:
            df = pd.DataFrame(entries)
            df["Monto con signo"] = df.apply(
                lambda r: r["amount"] if r["entry_type"] == "ingreso" else -r["amount"],
                axis=1,
            )
            display = df[
                ["entry_date", "description", "entry_type", "amount", "category", "is_projected", "scenario"]
            ].copy()
            display.columns = [
                "Fecha",
                "Descripción",
                "Tipo",
                "Monto",
                "Categoría",
                "Proyectado",
                "Escenario",
            ]
            display["Proyectado"] = display["Proyectado"].map({1: "Sí", 0: "No"})
            st.dataframe(
                display.style.format({"Monto": "${:,.2f}"}),
                use_container_width=True,
                hide_index=True,
            )

            with st.expander("🗑️ Eliminar movimiento"):
                options = {
                    f"{e['entry_date']} | {e['description']} | ${e['amount']:,.0f}": e["id"]
                    for e in entries
                }
                to_del = st.selectbox("Seleccionar", list(options.keys()))
                if st.button("Eliminar", type="primary"):
                    delete_cashflow_entry(options[to_del])
                    st.rerun()
        else:
            st.info("Todavía no hay movimientos. Cargá el primero arriba.")

        # Generador automático desde productos y costos
        st.divider()
        st.subheader("⚡ Generar proyección automática")
        st.caption(
            "Usa los productos y costos que cargaste en el Analizador para crear "
            "una proyección base de 12 meses (escenario realista)."
        )

        if st.button("Generar proyección desde productos + costos"):
            products = get_products(company_id)
            fixed = get_cost_items(company_id, "fijo")
            variables = get_cost_items(company_id, "variable")

            if not products and not fixed:
                st.warning("No hay productos ni costos cargados en el Analizador.")
            else:
                today = datetime.today().replace(day=1)
                count = 0
                for i in range(12):
                    month_date = (today + relativedelta(months=i)).date().isoformat()

                    # Ingresos por productos
                    for p in products:
                        rev = p["selling_price"] * p["units_sold_monthly"]
                        if rev > 0:
                            create_cashflow_entry(
                                company_id,
                                month_date,
                                f"Ventas - {p['name']}",
                                "ingreso",
                                rev,
                                "Ventas",
                                True,
                                "realista",
                            )
                            count += 1

                    # Costos de productos (COGS)
                    for p in products:
                        cogs = p["unit_cost"] * p["units_sold_monthly"]
                        if cogs > 0:
                            create_cashflow_entry(
                                company_id,
                                month_date,
                                f"Costo - {p['name']}",
                                "egreso",
                                cogs,
                                "Costo de ventas",
                                True,
                                "realista",
                            )
                            count += 1

                    # Costos fijos
                    for item in fixed:
                        create_cashflow_entry(
                            company_id,
                            month_date,
                            item["name"],
                            "egreso",
                            item["amount"],
                            "Fijos",
                            True,
                            "realista",
                        )
                        count += 1

                    # Costos variables extra
                    for item in variables:
                        create_cashflow_entry(
                            company_id,
                            month_date,
                            item["name"],
                            "egreso",
                            item["amount"],
                            "Variables",
                            True,
                            "realista",
                        )
                        count += 1

                log_usage(
                    user["id"],
                    "auto_generate_cashflow",
                    tool="cashflow_proyectado",
                    company_id=company_id,
                    details=f"{count} movimientos",
                )
                st.success(f"Se generaron {count} movimientos para 12 meses.")
                st.rerun()

    # ─── TAB 2: Proyección 12 meses ─────────────────────────────
    with tab2:
        st.subheader("Proyección de saldos")

        scenario = st.selectbox(
            "Escenario a visualizar",
            ["realista", "optimista", "pesimista"],
            key="proj_scenario",
        )

        entries = get_cashflow_entries(company_id, scenario=scenario)

        if not entries:
            st.info("No hay movimientos para este escenario. Cargalos o generá la proyección automática.")
            return

        df = pd.DataFrame(entries)
        df["entry_date"] = pd.to_datetime(df["entry_date"])
        df["signed_amount"] = df.apply(
            lambda r: r["amount"] if r["entry_type"] == "ingreso" else -r["amount"],
            axis=1,
        )

        # Agrupar por mes
        df["month"] = df["entry_date"].dt.to_period("M").astype(str)
        monthly = (
            df.groupby("month")
            .agg(
                ingresos=("signed_amount", lambda x: x[x > 0].sum()),
                egresos=("signed_amount", lambda x: -x[x < 0].sum()),
                neto=("signed_amount", "sum"),
            )
            .reset_index()
        )
        monthly = monthly.sort_values("month")
        monthly["saldo_acumulado"] = monthly["neto"].cumsum()

        # Métricas
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total ingresos (período)", f"${monthly['ingresos'].sum():,.0f}")
        m2.metric("Total egresos (período)", f"${monthly['egresos'].sum():,.0f}")
        m3.metric("Resultado neto", f"${monthly['neto'].sum():,.0f}")
        last_saldo = monthly["saldo_acumulado"].iloc[-1] if len(monthly) > 0 else 0
        m4.metric("Saldo final proyectado", f"${last_saldo:,.0f}")

        # Gráfico de saldo acumulado
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=monthly["month"],
                y=monthly["saldo_acumulado"],
                mode="lines+markers",
                name="Saldo acumulado",
                line=dict(color="#4f46e5", width=3),
            )
        )
        fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Cero")
        fig.update_layout(
            title="Evolución del saldo acumulado",
            xaxis_title="Mes",
            yaxis_title="Saldo ($)",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tabla mensual
        st.subheader("Detalle mensual")
        st.dataframe(
            monthly.style.format(
                {
                    "ingresos": "${:,.0f}",
                    "egresos": "${:,.0f}",
                    "neto": "${:,.0f}",
                    "saldo_acumulado": "${:,.0f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        # Alertas de meses en rojo
        red_months = monthly[monthly["saldo_acumulado"] < 0]
        if not red_months.empty:
            st.error(
                f"⚠️ **Alerta**: hay {len(red_months)} mes(es) con saldo acumulado negativo. "
                f"Primer mes en rojo: **{red_months.iloc[0]['month']}**."
            )
        else:
            st.success("✅ Ningún mes proyectado cierra con saldo acumulado negativo. Buen colchón de liquidez.")

    # ─── TAB 3: Escenarios ──────────────────────────────────────
    with tab3:
        st.subheader("Comparación de escenarios")

        scenarios = ["optimista", "realista", "pesimista"]
        data = {}

        for sc in scenarios:
            entries = get_cashflow_entries(company_id, scenario=sc)
            if entries:
                df = pd.DataFrame(entries)
                df["signed"] = df.apply(
                    lambda r: r["amount"] if r["entry_type"] == "ingreso" else -r["amount"],
                    axis=1,
                )
                data[sc] = df["signed"].sum()
            else:
                data[sc] = None

        if all(v is None for v in data.values()):
            st.info(
                "Todavía no hay datos de escenarios. "
                "Podés generar la proyección realista y luego cargar variantes optimista/pesimista."
            )
            return

        # Mostrar comparación
        cols = st.columns(3)
        for i, sc in enumerate(scenarios):
            val = data[sc]
            if val is not None:
                cols[i].metric(sc.capitalize(), f"${val:,.0f}")
            else:
                cols[i].metric(sc.capitalize(), "Sin datos")

        # Gráfico simple
        available = {k: v for k, v in data.items() if v is not None}
        if available:
            fig = px.bar(
                x=list(available.keys()),
                y=list(available.values()),
                labels={"x": "Escenario", "y": "Resultado neto ($)"},
                title="Resultado neto por escenario",
                color=list(available.keys()),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            """
            **Cómo usar los escenarios**
            - **Realista**: tu proyección base (la que generás automáticamente).
            - **Optimista**: subí un 15-20% los ingresos o bajá costos.
            - **Pesimista**: bajá ingresos 15-20% o aumentá costos.
            
            Cargá los movimientos de cada escenario en la pestaña "Cargar movimientos"
            eligiendo el escenario correspondiente.
            """
        )
