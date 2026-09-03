import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Capacitaciones DGA", layout="wide")

st.title("📊 Dashboard Capacitaciones DGA — 1er Semestre 2026")

# ------------------------------------------------------------------
# Datos fijos: se cargan desde un CSV ya limpio y anonimizado que vive
# en el mismo repositorio (data/data_capacitaciones_clean.csv).
# Ese archivo NO contiene DNI, correo, celular, nombres ni apellidos:
# la columna "persona_id" es un hash irreversible, solo sirve para
# contar personas únicas, no identifica a nadie.
# ------------------------------------------------------------------
DATA_PATH = "data/data_capacitaciones_clean.csv"


@st.cache_data(show_spinner="Cargando datos...")
def cargar_datos():
    df = pd.read_csv(DATA_PATH)
    df["FECHA DE REALIZACIÓN"] = pd.to_datetime(df["FECHA DE REALIZACIÓN"], errors="coerce")
    return df


df = cargar_datos()

# ------------------------------------------------------------------
# Filtros (sidebar)
# ------------------------------------------------------------------
st.sidebar.header("Filtros")
trimestre_sel = st.sidebar.selectbox("Trimestre", ["Todos"] + sorted(df["Trimestre"].dropna().unique().tolist()))
modalidad_sel = st.sidebar.selectbox(
    "Modalidad", ["Todas"] + sorted(df["MODALIDAD (PRESENCIAL, VIRTUAL)"].dropna().unique().tolist())
)
depto_sel = st.sidebar.selectbox(
    "Departamento", ["Todos"] + sorted(df["Departamento (donde se ubica la entidad - UE)"].dropna().unique().tolist())
)
sector_sel = st.sidebar.selectbox(
    "Sector", ["Todos"] + sorted(df["¿A qué sector pertenece su entidad?"].dropna().unique().tolist())
)

d = df.copy()
if trimestre_sel != "Todos":
    d = d[d["Trimestre"] == trimestre_sel]
if modalidad_sel != "Todas":
    d = d[d["MODALIDAD (PRESENCIAL, VIRTUAL)"] == modalidad_sel]
if depto_sel != "Todos":
    d = d[d["Departamento (donde se ubica la entidad - UE)"] == depto_sel]
if sector_sel != "Todos":
    d = d[d["¿A qué sector pertenece su entidad?"] == sector_sel]

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
pct_virtual = (d["MODALIDAD (PRESENCIAL, VIRTUAL)"] == "VIRTUAL").mean() * 100
col4.metric("% Virtual", f"{pct_virtual:.0f}%")

st.divider()

# ------------------------------------------------------------------
# Gráficos
# ------------------------------------------------------------------
serie_mes = d.groupby("Mes").size().reset_index(name="Participaciones").sort_values("Mes")
st.plotly_chart(
    px.line(serie_mes, x="Mes", y="Participaciones", markers=True, title="Participaciones por mes"),
    use_container_width=True,
)

c1, c2 = st.columns(2)

top_dep = d["Departamento (donde se ubica la entidad - UE)"].value_counts().head(10).sort_values()
c1.plotly_chart(
    px.bar(top_dep, x=top_dep.values, y=top_dep.index, orientation="h",
           title="Top 10 departamentos", labels={"x": "Participaciones", "y": ""}),
    use_container_width=True,
)

c2.plotly_chart(
    px.pie(d, names="MODALIDAD (PRESENCIAL, VIRTUAL)", title="Distribución por modalidad", hole=0.4),
    use_container_width=True,
)

c3, c4 = st.columns(2)

top_sector = d["¿A qué sector pertenece su entidad?"].value_counts().head(10).sort_values()
c3.plotly_chart(
    px.bar(top_sector, x=top_sector.values, y=top_sector.index, orientation="h",
           title="Participaciones por sector (top 10)", labels={"x": "Participaciones", "y": ""}),
    use_container_width=True,
)

c4.plotly_chart(
    px.pie(d, names="Nivel de Gobierno (de la entidad)", title="Distribución por nivel de gobierno", hole=0.4),
    use_container_width=True,
)

c5, c6 = st.columns(2)

c5.plotly_chart(
    px.pie(d, names="Género", title="Distribución por género", hole=0.4),
    use_container_width=True,
)

top_tema = d["TEMÁTICA DEL CURSO O TALLER"].value_counts().head(10).sort_values()
top_tema.index = [t[:60] + "..." if len(t) > 60 else t for t in top_tema.index]
c6.plotly_chart(
    px.bar(top_tema, x=top_tema.values, y=top_tema.index, orientation="h",
           title="Top 10 temáticas más dictadas", labels={"x": "Participaciones", "y": ""}),
    use_container_width=True,
)
