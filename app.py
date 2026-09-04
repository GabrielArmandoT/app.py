import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Dashboard Capacitaciones DGA", layout="wide")
st.title("📊 Dashboard Capacitaciones DGA — 1er Semestre 2026")

# ------------------------------------------------------------------
# Datos fijos: se cargan desde un CSV ya limpio y anonimizado que vive
# en el mismo repositorio (data/data_capacitaciones_clean.csv).
# No contiene DNI, correo, celular, nombres ni apellidos.
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "data_capacitaciones_clean.csv")

# Nombres reales de columnas en el archivo
COL = {
    "Género": "Género",
    "Edad": "Edad",
    "Nivel de Gobierno": "Nivel de Gobierno (de la entidad)",
    "Departamento": "Departamento (donde se ubica la entidad - UE)",
    "Sector": "¿A qué sector pertenece su entidad?",
    "Área": "Área donde labora en la entidad",
    "Puesto": "Puesto que ocupa en la entidad",
    "Funciones": "Las funciones / actividades principales que desarrolla en el puesto están relacionadas a:",
    "Estudios": "Estudios",
    "Modalidad Laboral": "¿CUÁL ES SU MODALIDAD DE CONTRATACIÓN EN LA ENTIDAD?",
    "Trimestre": "Trimestre",
    "Tipo de Capacitación": "TIPO CAPACITACIÓN (CURSO, TALLER)",
    "Modalidad": "MODALIDAD (PRESENCIAL, VIRTUAL)",
    "Temática": "TEMÁTICA DEL CURSO O TALLER",
    "Componente": "COMPONENTE SNA",
}


@st.cache_data(show_spinner="Cargando datos...")
def cargar_datos():
    if not os.path.exists(DATA_PATH):
        st.error(
            f"No se encontró el archivo de datos en: `{DATA_PATH}`.\n\n"
            "Verifica que en tu repositorio de GitHub exista la carpeta `data/` "
            "con el archivo `data_capacitaciones_clean.csv` dentro, al mismo "
            "nivel que `app.py`."
        )
        st.stop()
    # utf-8-sig maneja automáticamente un posible BOM al inicio del archivo
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

    columnas_esperadas = set(COL.values())
    columnas_encontradas = set(df.columns)
    faltantes = columnas_esperadas - columnas_encontradas
    if faltantes:
        st.error(
            "⚠️ El archivo de datos no tiene las columnas esperadas. "
            "Es muy probable que el CSV se haya subido a GitHub por copiar/pegar "
            "y los acentos se hayan corrompido en el proceso.\n\n"
            f"**Columnas que faltan:** {sorted(faltantes)}\n\n"
            f"**Columnas encontradas en el archivo:** {sorted(columnas_encontradas)}\n\n"
            "**Solución:** vuelve a subir el CSV usando 'Add file → Upload files' "
            "(arrastrando el archivo, sin copiar/pegar texto) para conservar los "
            "acentos correctamente."
        )
        st.stop()

    df["FECHA DE REALIZACIÓN"] = pd.to_datetime(df["FECHA DE REALIZACIÓN"], errors="coerce")
    return df


df = cargar_datos()

# ------------------------------------------------------------------
# Filtros (sidebar) — agrupados en 3 bloques para no saturar
# ------------------------------------------------------------------
st.sidebar.header("🔎 Filtros")

grupos = {
    "👤 Persona": ["Género", "Edad", "Estudios", "Área", "Puesto", "Funciones", "Modalidad Laboral"],
    "🏢 Entidad": ["Nivel de Gobierno", "Departamento", "Sector"],
    "📚 Capacitación": ["Trimestre", "Tipo de Capacitación", "Modalidad", "Temática", "Componente"],
}

seleccion = {}
for titulo_grupo, campos in grupos.items():
    with st.sidebar.expander(titulo_grupo, expanded=(titulo_grupo == "👤 Persona")):
        for campo in campos:
            col_real = COL[campo]
            opciones = ["Todos"] + sorted(df[col_real].dropna().unique().tolist())
            seleccion[campo] = st.selectbox(campo, opciones, key=f"filtro_{campo}")

if st.sidebar.button("🔄 Limpiar todos los filtros"):
    for campo in seleccion:
        st.session_state[f"filtro_{campo}"] = "Todos"
    st.rerun()

d = df.copy()
for campo, valor in seleccion.items():
    if valor != "Todos":
        d = d[d[COL[campo]] == valor]

if len(d) == 0:
    st.warning("No hay registros para esta combinación de filtros.")
    st.stop()

# ------------------------------------------------------------------
# KPIs
# ------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Participaciones", f"{len(d):,}")
col2.metric("Personas únicas", f"{d['persona_id'].nunique():,}")
col3.metric("Entidades alcanzadas", f"{d['Nombre de la entidad (Unidad Ejecutora)'].nunique():,}")
pct_virtual = (d[COL["Modalidad"]] == "VIRTUAL").mean() * 100
col4.metric("% Virtual", f"{pct_virtual:.0f}%")

st.divider()

# ------------------------------------------------------------------
# Listado de entidades (Nombre + Código UE) según filtros aplicados
# ------------------------------------------------------------------
st.subheader("🏢 Entidades que cumplen los filtros seleccionados")
tabla_entidades = (
    d.groupby(["Nombre de la entidad (Unidad Ejecutora)", "Codigo UE"])
    .size()
    .reset_index(name="Participaciones")
    .sort_values("Participaciones", ascending=False)
)
st.caption(f"{len(tabla_entidades):,} entidades encontradas")
st.dataframe(tabla_entidades, use_container_width=True, hide_index=True, height=300)

csv_export = tabla_entidades.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Descargar listado de entidades (CSV)",
    data=csv_export,
    file_name="entidades_filtradas.csv",
    mime="text/csv",
)

st.divider()

# ------------------------------------------------------------------
# Tendencia mensual
# ------------------------------------------------------------------
serie_mes = d.groupby("Mes").size().reset_index(name="Participaciones").sort_values("Mes")
st.plotly_chart(
    px.line(serie_mes, x="Mes", y="Participaciones", markers=True, title="Participaciones por mes"),
    use_container_width=True,
)

# ------------------------------------------------------------------
# Gráficos: un chart por cada dimensión filtrable
# ------------------------------------------------------------------
st.subheader("📈 Distribuciones")

pie_fields = ["Género", "Nivel de Gobierno", "Trimestre", "Tipo de Capacitación", "Modalidad", "Estudios"]
bar_top10_fields = ["Departamento", "Sector", "Área", "Puesto", "Componente", "Temática", "Funciones", "Edad", "Modalidad Laboral"]

def truncar(texto, n=55):
    texto = str(texto)
    return texto[:n] + "..." if len(texto) > n else texto

cols_cycle = None
for i, campo in enumerate(pie_fields):
    if i % 2 == 0:
        cols_cycle = st.columns(2)
    col_real = COL[campo]
    fig = px.pie(d, names=col_real, title=f"Distribución por {campo}", hole=0.4)
    cols_cycle[i % 2].plotly_chart(fig, use_container_width=True)

for i, campo in enumerate(bar_top10_fields):
    if i % 2 == 0:
        cols_cycle = st.columns(2)
    col_real = COL[campo]
    top = d[col_real].value_counts().head(10).sort_values()
    top.index = [truncar(x) for x in top.index]
    fig = px.bar(
        top, x=top.values, y=top.index, orientation="h",
        title=f"Top 10 — {campo}", labels={"x": "Participaciones", "y": ""},
    )
    fig.update_layout(height=400)
    cols_cycle[i % 2].plotly_chart(fig, use_container_width=True)
