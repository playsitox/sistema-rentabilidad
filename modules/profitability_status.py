"""
Módulo 2: Estado de Situación de Rentabilidad
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.auth import get_current_user
from utils.database import (
    get_products,
    get_cost_items,
    log_usage,
)


def render():
    user = get_current_user()
    company_id = st.session_state.get("company_id")

    st.markdown("## 2️⃣ Estado de Situación de Rentabilidad")
    st.caption(
        "Armá la radiografía de tu empresa y entendé cuánto ganás realmente. "
        "Respondé: *“No sé si estoy ganando o perdiendo”*."
    )

    if not company_id:
        st.warning("Seleccioná o creá una empresa en la barra lateral.")
        return

    log_usage(user["id"], "open_tool", tool="estado_rentabilidad", company_id=company_id)

    products = get_products(company_id)
    fixed = get_cost_items(company_id, "fijo")
    variables = get_cost_items(company_id, "variable")

    if not products and not fixed and not variables:
        st.info(
            "Todavía no hay datos. Andá al **Analizador de Costos y Precios** "
            "y cargá productos + costos para ver la radiografía acá."
        )
        return

    # ─── Cálculos ───────────────────────────────────────────────
    total_revenue = sum(p["selling_price"] * p["units_sold_monthly"] for p in products)
    total_cogs = sum(p["unit_cost"] * p["units_sold_monthly"] for p in products)  # costo de mercadería
    gross_profit = total_revenue - total_cogs

    total_fixed = sum(i["amount"] for i in fixed) if fixed else 0
    total_variable_extra = sum(i["amount"] for i in variables) if variables else 0
    total_opex = total_fixed + total_variable_extra

    operating_result = gross_profit - total_opex
    gross_margin_pct = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    net_margin_pct = (operating_result / total_revenue * 100) if total_revenue > 0 else 0

    # ─── Semáforo principal ─────────────────────────────────────
    st.subheader("Radiografía general")

    if operating_result > 0:
        st.success(f"✅ **Estás ganando**. Resultado operativo estimado: **${operating_result:,.0f}/mes**")
    elif operating_result == 0:
        st.warning("⚠️ Estás en el punto de equilibrio.")
    else:
        st.error(f"❌ **Estás perdiendo**. Resultado operativo estimado: **${operating_result:,.0f}/mes**")

    # Métricas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingresos mensuales", f"${total_revenue:,.0f}")
    c2.metric("Costo de ventas (COGS)", f"${total_cogs:,.0f}")
    c3.metric("Margen bruto", f"${gross_profit:,.0f}", f"{gross_margin_pct:.1f}%")
    c4.metric(
        "Resultado operativo",
        f"${operating_result:,.0f}",
        f"{net_margin_pct:.1f}%",
        delta_color="normal" if operating_result >= 0 else "inverse",
    )

    st.divider()

    # ─── Estructura de resultados ────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Estructura de resultados")
        structure = pd.DataFrame(
            {
                "Concepto": [
                    "Ingresos",
                    "(-) Costo de ventas",
                    "Margen bruto",
                    "(-) Costos fijos",
                    "(-) Costos variables extra",
                    "Resultado operativo",
                ],
                "Monto": [
                    total_revenue,
                    -total_cogs,
                    gross_profit,
                    -total_fixed,
                    -total_variable_extra,
                    operating_result,
                ],
            }
        )
        st.dataframe(
            structure.style.format({"Monto": "${:,.0f}"}),
            use_container_width=True,
            hide_index=True,
        )

    with col2:
        st.subheader("Composición de costos")
        cost_data = []
        if total_cogs > 0:
            cost_data.append({"Tipo": "Costo de ventas (productos)", "Monto": total_cogs})
        if total_fixed > 0:
            cost_data.append({"Tipo": "Costos fijos", "Monto": total_fixed})
        if total_variable_extra > 0:
            cost_data.append({"Tipo": "Costos variables extra", "Monto": total_variable_extra})

        if cost_data:
            df_cost = pd.DataFrame(cost_data)
            fig = px.pie(df_cost, values="Monto", names="Tipo", title="Distribución de costos")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin costos cargados.")

    # ─── Rentabilidad por producto ──────────────────────────────
    if products:
        st.subheader("Rentabilidad por producto")

        rows = []
        for p in products:
            rev = p["selling_price"] * p["units_sold_monthly"]
            cost = p["unit_cost"] * p["units_sold_monthly"]
            contrib = rev - cost
            margin = (contrib / rev * 100) if rev > 0 else 0
            rows.append(
                {
                    "Producto": p["name"],
                    "Ingresos": rev,
                    "Costo": cost,
                    "Contribución": contrib,
                    "Margen %": margin,
                    "Unidades": p["units_sold_monthly"],
                }
            )

        df_prod = pd.DataFrame(rows).sort_values("Contribución", ascending=False)

        fig_bar = px.bar(
            df_prod,
            x="Producto",
            y="Contribución",
            color="Margen %",
            color_continuous_scale="RdYlGn",
            title="Contribución por producto (ordenado)",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.dataframe(
            df_prod.style.format(
                {
                    "Ingresos": "${:,.0f}",
                    "Costo": "${:,.0f}",
                    "Contribución": "${:,.0f}",
                    "Margen %": "{:.1f}%",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        # Productos que más aportan vs los que menos
        if len(df_prod) >= 2:
            best = df_prod.iloc[0]
            worst = df_prod.iloc[-1]
            st.info(
                f"🏆 **Producto estrella**: {best['Producto']} (contribuye ${best['Contribución']:,.0f}/mes). "
                f"⚠️ **El de menor aporte**: {worst['Producto']} (${worst['Contribución']:,.0f}/mes)."
            )

    # ─── Interpretación automática ──────────────────────────────
    st.subheader("Interpretación rápida")

    if total_revenue == 0:
        st.warning("No hay ingresos cargados. Empezá por cargar productos y volúmenes de venta.")
    else:
        if gross_margin_pct < 30:
            st.warning(
                f"Tu margen bruto es del {gross_margin_pct:.1f}%. "
                "Es bajo. Revisá costos de productos o precios de venta."
            )
        elif gross_margin_pct < 50:
            st.info(f"Margen bruto del {gross_margin_pct:.1f}%. Está en un rango aceptable para muchos rubros.")
        else:
            st.success(f"Buen margen bruto: {gross_margin_pct:.1f}%.")

        if operating_result < 0:
            st.error(
                "El resultado operativo es negativo. "
                "Opciones: aumentar precios, bajar costos fijos, o subir volumen de los productos con mejor margen."
            )
        elif operating_result < total_fixed * 0.2:
            st.warning(
                "Estás ganando, pero el colchón es chico respecto a los costos fijos. "
                "Cualquier caída de ventas te puede poner en rojo."
            )
        else:
            st.success(
                "Tenés un resultado operativo saludable. "
                "Ahora el siguiente paso es proyectar el cash flow para asegurar liquidez."
            )
