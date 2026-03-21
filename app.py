# --- IMPORTS ---
import io
import re
from pathlib import Path
from supabase import create_client, Client

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# =========================
# SUPABASE CONNECTION
# =========================
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

# =========================
# LOAD DATA
# =========================
def load_monitoring():
    supabase = get_supabase()
    res = supabase.table("monitoring").select("*").execute()
    data = res.data if res.data else []
    return pd.DataFrame(data)

# =========================
# SAVE DATA
# =========================
def upsert_monitoring(df):
    supabase = get_supabase()
    rows = df.to_dict(orient="records")
    supabase.table("monitoring").upsert(rows, on_conflict="Fecha,Jugador").execute()

# =========================
# UI
# =========================
st.title("Carga de datos MD-1")

uploaded = st.file_uploader("Sube archivo", type=["csv","xlsx"])

if uploaded:
    df = pd.read_excel(uploaded)
    st.dataframe(df)

    if st.button("Guardar en base de datos"):
        try:
            upsert_monitoring(df)
            st.success("Guardado en Supabase")
        except Exception as e:
            st.error(e)
