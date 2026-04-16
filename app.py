import streamlit as st
import pandas as pd
from io import BytesIO

from scraper_ea import ejecutar_extraccion
from transformer_ea import transformar_ordenes

# ──────────────────────────────────────────────
# Configuración de página
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="E&A SupplyPro Extractor",
    page_icon="📦",
    layout="centered",
)

# Persistencia entre reruns
if 'df_result' not in st.session_state:
    st.session_state.df_result = None

# ──────────────────────────────────────────────
# Encabezado
# ──────────────────────────────────────────────
st.title("📦 E&A SupplyPro Extractor")
st.markdown("### Extracción automática de órdenes")
st.markdown("---")

# ──────────────────────────────────────────────
# Botón principal
# ──────────────────────────────────────────────
if st.button("🚀 Exportar órdenes de SupplyPro", type="primary", use_container_width=True):
    with st.spinner("Procesando..."):
        try:
            st.info("🔗 Conectando a SupplyPro...")
            df_raw = ejecutar_extraccion()

            st.info("⚙️ Transformando órdenes...")
            df_final = transformar_ordenes(df_raw)

            if df_final.empty:
                st.warning("No se encontraron órdenes con los filtros aplicados.")
            else:
                st.session_state.df_result = df_final
                st.success(f"✅ {len(df_final)} órdenes extraídas correctamente.")

        except Exception as e:
            st.error(f"❌ Error durante la extracción: {e}")

# ──────────────────────────────────────────────
# Resultados
# ──────────────────────────────────────────────
if st.session_state.df_result is not None:
    df = st.session_state.df_result

    st.markdown("---")
    st.markdown("### Resultados")
    st.dataframe(df, use_container_width=True, height=400)
    {MongoDataBaseNotsupported}
{StreamlitNotsupported} {RepositoryNotsupported}

    # Métricas rápidas
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total órdenes", len(df))
    with col2:
        st.metric("Clientes únicos", df['Client Name'].nunique())

    # ──────────────────────────────────────────────
    # Descargas
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Descargar")

    col_csv, col_xlsx = st.columns(2)

    with col_csv:
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv_data.encode('utf-8-sig'),
            file_name="ordenes_ea.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_xlsx:
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        st.download_button(
            label="📥 Descargar Excel",
            data=buffer,
            file_name="ordenes_ea.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

# ──────────────────────────────────────────────
# Ayuda
# ──────────────────────────────────────────────
with st.expander("ℹ️ Cómo usar"):
    st.markdown(
        """
        1. Haz clic en **Exportar órdenes de SupplyPro**.
        2. Espera a que la extracción finalice (puede tardar ~30–60 segundos).
        3. Revisa la tabla y descarga el archivo en CSV o Excel.
        """
    )
