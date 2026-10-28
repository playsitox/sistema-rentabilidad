"""
Módulo 1: Analizador de Costos y Precios
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.auth import get_current_user
from utils.database import (
    get_products,
    create_product,
    update_product,
    delete_product,
    get_cost_items,
    create_cost_item,
    delete_cost_item,
    log_usage,
)


def render():
    user = get_current_user()
    company_id = st.session_state.get("company_id")

    st.markdown("## 1️⃣ Analizador de Costos y Precios")
    st.caption(
        "Cargá tus costos en una tarde y mirá el margen real de tu producto estrella, "
        "para entender si ahí se está yendo tu rentabilidad."
    )

    if not company_id:
        st.warning("Seleccioná o creá una empresa en la barra lateral.")
        return

    log_usage(user["id"], "open_tool", tool="analizador_costos", company_id=company_id)

    tab1, tab2, tab3 = st.tabs(
        ["📦 Productos", "💰 Costos Fijos / Variables", "📊 Análisis de Margen"]
    )

    # ─── TAB 1: Productos ───────────────────────────────────────
    with tab1:
        st.subheader("Productos / Servicios")

        with st.expander("➕ Agregar producto", expanded=False):
            with st.form("add_product"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Nombre del producto *")
                    category = st.text_input("Categoría")
                    sku = st.text_input("SKU / Código")
                with col2:
                    unit_cost = st.number_input("Costo unitario", min_value=0.0, step=10.0)
                    selling_price = st.number_input("Precio de venta", min_value=0.0, step=10.0)
                    units = st.number_input("Unidades vendidas/mes (est.)", min_value=0.0, step=1.0)

                if st.form_submit_button("Guardar producto"):
                    if name.strip():
                        create_product(
                            company_id,
                            name.strip(),
                            unit_cost,
                            selling_price,
                            units,
                            category,
                            sku,
                        )
                        log_usage(
                            user["id"],
                            "create_product",
                            tool="analizador_costos",
                            company_id=company_id,
                            details=name,
                        )
                        st.success(f"Producto '{name}' agregado")
                        st.rerun()
                    else:
                        st.error("El nombre es obligatorio")

        products = get_products(company_id)
        if products:
            df = pd.DataFrame(products)
            df["margen_unitario"] = df["selling_price"] - df["unit_cost"]
            df["margen_%"] = df.apply(
                lambda r: ((r["selling_price"] - r["unit_cost"]) / r["selling_price"] * 100)
                if r["selling_price"] > 0
                else 0,
                axis=1,
            )
            df["ingreso_mensual"] = df["selling_price"] * df["units_sold_monthly"]
            df["contribucion_mensual"] = df["margen_unitario"] * df["units_sold_monthly"]

            display_df = df[
                [
                    "name",
                    "category",
                    "unit_cost",
                    "selling_price",
                    "margen_unitario",
                    "margen_%",
                    "units_sold_monthly",
                    "contribucion_mensual",
                ]
            ].copy()
            display_df.columns = [
                "Producto",
                "Categoría",
                "Costo unit.",
                "Precio venta",
                "Margen $",
                "Margen %",
                "Unid./mes",
                "Contribución mens.",
            ]
            st.dataframe(
                display_df.style.format(
                    {
                        "Costo unit.": "${:,.2f}",
                        "Precio venta": "${:,.2f}",
                        "Margen $": "${:,.2f}",
                        "Margen %": "{:.1f}%",
                        "Contribución mens.": "${:,.2f}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            # Eliminar producto
            with st.expander("🗑️ Eliminar producto"):
                prod_names = {p["name"]: p["id"] for p in products}
                to_delete = st.selectbox("Seleccionar producto", list(prod_names.keys()))
                if st.button("Eliminar", type="primary"):
                    delete_product(prod_names[to_delete])
                    log_usage(
                        user["id"],
                        "delete_product",
                        tool="analizador_costos",
                        company_id=company_id,
                        details=to_delete,
                    )
                    st.rerun()
        else:
            st.info("Todavía no cargaste productos. Agregá el primero arriba.")

    # ─── TAB 2: Costos ──────────────────────────────────────────
    with tab2:
        st.subheader("Costos de la empresa")

        col_fijo, col_var = st.columns(2)

        with col_fijo:
            st.markdown("#### Costos Fijos")
            with st.form("add_fixed_cost"):
                name = st.text_input("Nombre (ej: Alquiler, Sueldos)")
                amount = st.number_input("Monto mensual", min_value=0.0, step=100.0, key="fixed_amt")
                category = st.text_input("Categoría", key="fixed_cat")
                if st.form_submit_button("Agregar costo fijo"):
                    if name.strip() and amount > 0:
                        create_cost_item(company_id, name.strip(), "fijo", amount, "mensual", category)
                        log_usage(
                            user["id"],
                            "create_cost",
                            tool="analizador_costos",
                            company_id=company_id,
                            details=f"fijo: {name}",
                        )
                        st.success("Costo fijo agregado")
                        st.rerun()

            fixed = get_cost_items(company_id, "fijo")
            if fixed:
                for item in fixed:
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"**{item['name']}**: ${item['amount']:,.2f}/mes")
                    if c2.button("✕", key=f"del_f_{item['id']}"):
                        delete_cost_item(item["id"])
                        st.rerun()
                total_fixed = sum(i["amount"] for i in fixed)
                st.metric("Total costos fijos mensuales", f"${total_fixed:,.2f}")

        with col_var:
            st.markdown("#### Costos Variables (no asociados a producto)")
            with st.form("add_var_cost"):
                name = st.text_input("Nombre (ej: Comisiones, Packaging extra)")
                amount = st.number_input("Monto mensual estimado", min_value=0.0, step=50.0, key="var_amt")
                category = st.text_input("Categoría", key="var_cat")
                if st.form_submit_button("Agregar costo variable"):
                    if name.strip() and amount > 0:
                        create_cost_item(company_id, name.strip(), "variable", amount, "mensual", category)
                        log_usage(
                            user["id"],
                            "create_cost",
                            tool="analizador_costos",
                            company_id=company_id,
                            details=f"variable: {name}",
                        )
                        st.success("Costo variable agregado")
                        st.rerun()

            variables = get_cost_items(company_id, "variable")
            if variables:
                for item in variables:
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"**{item['name']}**: ${item['amount']:,.2f}/mes")
                    if c2.button("✕", key=f"del_v_{item['id']}"):
                        delete_cost_item(item["id"])
                        st.rerun()
                total_var = sum(i["amount"] for i in variables)
                st.metric("Total costos variables mensuales", f"${total_var:,.2f}")

    # ─── TAB 3: Análisis ────────────────────────────────────────
    with tab3:
        st.subheader("Análisis de margen y punto de equilibrio")

        products = get_products(company_id)
        fixed = get_cost_items(company_id, "fijo")
        variables = get_cost_items(company_id, "variable")

        if not products:
            st.info("Cargá al menos un producto para ver el análisis.")
            return

        total_fixed = sum(i["amount"] for i in fixed) if fixed else 0
        total_var_extra = sum(i["amount"] for i in variables) if variables else 0

        # Datos por producto
        rows = []
        for p in products:
            margin = p["selling_price"] - p["unit_cost"]
            margin_pct = (margin / p["selling_price"] * 100) if p["selling_price"] > 0 else 0
            contrib = margin * p["units_sold_monthly"]
            rows.append(
                {
                    "Producto": p["name"],
                    "Precio": p["selling_price"],
                    "Costo unit.": p["unit_cost"],
                    "Margen $": margin,
                    "Margen %": margin_pct,
                    "Unid./mes": p["units_sold_monthly"],
                    "Contribución": contrib,
                }
            )

        df = pd.DataFrame(rows)
        total_contrib = df["Contribución"].sum()
        total_revenue = (df["Precio"] * df["Unid./mes"]).sum()

        # Punto de equilibrio (en unidades, aproximado por margen promedio)
        avg_margin = df["Margen $"].mean() if len(df) > 0 else 0
        break_even_units = (total_fixed / avg_margin) if avg_margin > 0 else 0

        # Métricas principales
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ingresos mensuales est.", f"${total_revenue:,.0f}")
        m2.metric("Contribución total", f"${total_contrib:,.0f}")
        m3.metric("Costos fijos mensuales", f"${total_fixed:,.0f}")
        resultado = total_contrib - total_fixed - total_var_extra
        m4.metric(
            "Resultado estimado",
            f"${resultado:,.0f}",
            delta="Positivo" if resultado >= 0 else "Negativo",
        )

        st.divider()

        # Gráfico de márgenes
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            fig = px.bar(
                df,
                x="Producto",
                y="Margen %",
                title="Margen % por producto",
                color="Margen %",
                color_continuous_scale="RdYlGn",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_g2:
            fig2 = px.pie(
                df,
                values="Contribución",
                names="Producto",
                title="Aporte a la contribución total",
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Tabla de análisis
        st.dataframe(
            df.style.format(
                {
                    "Precio": "${:,.2f}",
                    "Costo unit.": "${:,.2f}",
                    "Margen $": "${:,.2f}",
                    "Margen %": "{:.1f}%",
                    "Contribución": "${:,.2f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.info(
            f"**Punto de equilibrio aproximado**: {break_even_units:,.0f} unidades/mes "
            f"(usando margen promedio de ${avg_margin:,.2f}). "
            f"Esto cubre solo los costos fijos de ${total_fixed:,.0f}."
        )

        # Simulador simple
        st.subheader("🧪 Simulador rápido")
        st.caption("¿Qué pasa si cambio el precio o el volumen?")

        selected = st.selectbox("Producto a simular", df["Producto"].tolist())
        prod = next(p for p in products if p["name"] == selected)

        c1, c2, c3 = st.columns(3)
        new_price = c1.number_input("Nuevo precio", value=float(prod["selling_price"]), step=10.0)
        new_units = c2.number_input("Nuevas unidades/mes", value=float(prod["units_sold_monthly"]), step=1.0)
        new_cost = c3.number_input("Nuevo costo unitario", value=float(prod["unit_cost"]), step=5.0)

        new_margin = new_price - new_cost
        new_contrib = new_margin * new_units
        old_contrib = (prod["selling_price"] - prod["unit_cost"]) * prod["units_sold_monthly"]
        delta = new_contrib - old_contrib

        st.metric(
            "Nueva contribución mensual de este producto",
            f"${new_contrib:,.2f}",
            delta=f"${delta:,.2f}",
        )
