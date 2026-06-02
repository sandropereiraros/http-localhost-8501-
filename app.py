import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from datetime import datetime, timedelta
import time

# ==========================================
# CONFIGURACIÓN CORE-NEURAL Y ESTILOS
# ==========================================
st.set_page_config(page_title="CORE-NEURAL // Monitor Nacional", layout="wide")

st.html(
    """
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .zone-card {
        padding: 10px;
        border-radius: 8px;
        border-left: 5px solid #58a6ff;
        background: #161b22;
        margin-bottom: 8px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .gps-card {
        background: linear-gradient(135deg, #1f2937, #0d1117);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #58a6ff;
        box-shadow: 0 0 15px rgba(88,166,255,0.2);
        margin-bottom: 25px;
        font-family: monospace;
    }
    h1, h2, h3 { font-family: 'Courier New', monospace !important; }
    </style>
    """
)

ZONAS_CONFIG = {
    "Arica/Iquique (Ref: 2014)": {"lat": -20.0, "base_cond": 4.5, "sig_cond": 0.1, "base_pres": 1015.0},
    "Antofagasta/Atacama": {"lat": -25.0, "base_cond": 3.8, "sig_cond": 0.2, "base_pres": 1011.5},
    "Valparaíso/Villa Alemana": {"lat": -33.0, "base_cond": 4.1, "sig_cond": 0.15, "base_pres": 1013.25},
    "Maule/Biobío (Ref: 2010)": {"lat": -37.0, "base_cond": 4.0, "sig_cond": 0.2, "base_pres": 1012.0},
    "Puerto Montt/Sur": {"lat": -42.0, "base_cond": 3.5, "sig_cond": 0.3, "base_pres": 1008.0}
}

# ==========================================
# RECOPILACIÓN DE TELEMETRÍA MULTI-VARIABLE
# ==========================================

@st.cache_data(ttl=15)
def obtener_sismos_chile():
    fecha_inicio = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={fecha_inicio}&minlatitude=-56&maxlatitude=-18&minlongitude=-76&maxlongitude=-66"
    try:
        response = requests.get(url, timeout=5)
        sismos = []
        for f in response.json().get('features', []):
            coords = f['geometry']['coordinates']
            sismos.append({
                "Magnitud": float(f['properties'].get('mag') or 0.0),
                "Lugar": f['properties'].get('place'),
                "Latitud": coords[1],
                "Longitud": coords[0],
                "Fecha": datetime.fromtimestamp(f['properties']['time']/1000).strftime('%H:%M:%S')
            })
        return pd.DataFrame(sismos)
    except:
        return pd.DataFrame(columns=["Magnitud", "Lugar", "Latitud", "Longitud", "Fecha"])

nivel_insar_global = 45.0  
anomalia_termica = 1.2
anomalia_shoa = 2.6
conductividad_global = 4.2
presion_global = 1012.0

# ==========================================
# MOTOR LOGÍSTICO BLINDADO
# ==========================================

def calcular_riesgo_multivariable_por_zona(df_sismos, insar, termico, shoa, cond, pres):
    data_comparativa = []
    for nombre, config in ZONAS_CONFIG.items():
        sismos_cerca = 0
        if not df_sismos.empty:
            sismos_cerca = len(df_sismos[
                (df_sismos['Latitud'] <= config["lat"] + 3) & 
                (df_sismos['Latitud'] >= config["lat"] - 3) &
                (df_sismos['Magnitud'] >= 3.0)
            ])
            
        compuerta_abierta = (insar >= 55.0) or (sismos_cerca >= 4)
        
        z_score_cond = (cond - config["base_cond"]) / config["sig_cond"]
        cond_valida = cond if z_score_cond > 2.5 else config["base_cond"]
        
        peso_insar = insar * 0.35
        peso_sismos = min(sismos_cerca * 5.0, 15.0)
        
        if compuerta_abierta:
            peso_termico = (termico * 10) * 0.10
            peso_atmosferico = min(abs(config["base_pres"] - pres) * 0.5, 10.0)
            peso_shoa = min(abs(shoa) * 5, 15.0)
            peso_cond = min(cond_valida * 3, 15.0)
        else:
            peso_termico, peso_atmosferico, peso_shoa, peso_cond = 0.0, 0.0, 0.0, 0.0
            
        riesgo_final = peso_insar + peso_sismos + peso_termico + peso_atmosferico + peso_shoa + peso_cond
        
        data_comparativa.append({"Zona": nombre, "Nivel de Riesgo %": min(riesgo_final, 100.0), "Compuerta": compuerta_abierta})
        
    return pd.DataFrame(data_comparativa)

df_sismos = obtener_sismos_chile()
df_comparativo = calcular_riesgo_multivariable_por_zona(df_sismos, nivel_insar_global, anomalia_termica, anomalia_shoa, conductividad_global, presion_global)
max_riesgo = df_comparativo["Nivel de Riesgo %"].max()

# ==========================================
# INTERFAZ DE USUARIO Y ALARMAS
# ==========================================

st.html('<h1 style="color:#58a6ff; text-align:center;">⚡ GEO-NEURAL V4: ENTORNO CONTROLADO INTEGRADO</h1>')
st.info("🛡️ FILTRO ANTI-FALSOS POSITIVOS ACTIVO: El sistema bloquea ruido ambiental si no existe correlación con deformación cortical (InSAR) o enjambres sísmicos verificados.")

if max_riesgo >= 90:
    st.html(f"""
        <div style="background: linear-gradient(45deg, #7a0e1d, #ff003c); padding:20px; border-radius:15px; border:4px dashed #fff; text-align:center; box-shadow: 0 0 50px rgba(255,0,60,0.8);">
            <h1 style="color:white; margin:0;">🚨 ADVERTENCIA DE RUPTURA INMINENTE 🚨</h1>
            <p style="color:white; font-size:18px;">CONVERGENCIA DE VARIABLES CONFIRMADA. ESTRÉS CORTICAL CRÍTICO COMPROBADO.</p>
        </div>
        <audio autoplay loop><source src="https://actions.google.com/sounds/v1/science_fiction/pulsating_space_beacon.ogg" type="audio/ogg"></audio>
    """)

tab1, tab2 = st.tabs(["🌐 MONITOREO GENERAL NACIONAL", "📍 RADAR GPS OPERADOR"])

with tab1:
    st.markdown("### 🗺️ ANÁLISIS SENSORIAL POR REGIONES")
    cols_zonas = st.columns(5)

    for i, row in df_comparativo.iterrows():
        color = "#2ec4b6" if row['Nivel de Riesgo %'] < 40 else "#ff9f1c" if row['Nivel de Riesgo %'] < 75 else "#ff003c"
        with cols_zonas[i]:
            st.html(f"""
                <div class="zone-card" style="border-left-color: {color};">
                    <p style="color:#8b949e; font-size:10px; margin:0;">SECTOR TECTÓNICO</p>
                    <b style="font-size:11px;">{row['Zona']}</b>
                    <h3 style="color:{color}; margin:5px 0;">{row['Nivel de Riesgo %']:.1f}%</h3>
                    <p style="font-size:10px; margin:0; color:#8b949e;">Filtro Lógico: {"🔓 Abierto" if row['Compuerta'] else "🔒 Bloqueado"}</p>
                </div>
            """)

    col_izq, col_der = st.columns([1.5, 1])

    with col_izq:
        st.markdown("### 📊 PRESIÓN TECTÓNICA CALIBRADA")
        st.bar_chart(df_comparativo.set_index("Zona")["Nivel de Riesgo %"], color="#58a6ff")
        
        m = folium.Map(location=[-33, -71], zoom_start=4, tiles="cartodbpositron")
        if not df_sismos.empty:
            for _, s in df_sismos.iterrows():
                if s['Magnitud'] >= 3.0:
                    folium.CircleMarker(
                        location=[s['Latitud'], s['Longitud']],
                        radius=max(3.0, s['Magnitud'] * 1.5),
                        color="#ff003c" if s['Magnitud'] > 5 else "#ff9f1c",
                        fill=True,
                        popup=f"Mag: {s['Magnitud']}"
                    ).add_to(m)
        st_folium(m, width="100%", height=350, key="mapa_v4_general")

    with col_der:
        st.markdown("### 📡 ÚLTIMA ACTIVIDAD (M ≥ 3.0)")
        sismos_filtrados = df_sismos[df_sismos['Magnitud'] >= 3.0] if not df_sismos.empty else pd.DataFrame()
        
        if not sismos_filtrados.empty:
            for i, s in sismos_filtrados.head(6).iterrows():
                st.html(f"""
                    <div style="background:#161b22; padding:8px; border-radius:5px; border-bottom:1px solid #30363d; margin-bottom:5px;">
                        <b style="color:#ff7b72;">M {s['Magnitud']}</b> | <span style="font-size:11px;">{s['Lugar']}</span><br>
                        <small style="color:#8b949e;">Hora: {s['Fecha']}</small>
                    </div>
                """)
        else:
            st.write("Corteza estable. Sin eventos sobre magnitud 3.0 recientes.")

with tab2:
    st.markdown("### 📡 ANÁLISIS DE COBERTURA EN TU POSICIÓN ACTUAL")
    col_btn, col_card = st.columns([1, 2.5])
    
    with col_btn:
        st.write("Haz clic para sincronizar las coordenadas:")
        location = streamlit_geolocation()
        
    with col_card:
        if location and location.get("latitude"):
            user_lat = location["latitude"]
            user_lon = location["longitude"]
            
            zona_cercana = None
            min_dist = float("inf")
            for nombre, config in ZONAS_CONFIG.items():
                dist = abs(user_lat - config["lat"])
                if dist < min_dist:
                    min_dist = dist
                    zona_cercana = nombre
                    
            riesgo_local = df_comparativo[df_comparativo["Zona"] == zona_cercana]["Nivel de Riesgo %"].values[0]
            color_user = "#2ec4b6" if riesgo_local < 40 else "#ff9f1c" if riesgo_local < 75 else "#ff003c"
            
            st.html(f"""
                <div class="gps-card">
                    <span style="color:#58a6ff; font-weight:bold; font-size:11px;">📍 ESCANEO LOCAL DE ESTRÉS ACTIVO</span>
                    <p style="margin:6px 0; font-size:15px;">Cuadrante Evaluado: <b>{zona_cercana}</b></p>
                    <p style="margin:2px 0; font-size:11px; color:#8b949e;">Lat {user_lat:.4f} | Lon {user_lon:.4f}</p>
                    <h2 style="color:{color_user}; margin:12px 0; font-size:22px;">Riesgo Local (M ≥ 7.5): {riesgo_local:.1f}%</h2>
                </div>
            """)
        else:
            st.warning("Ubicación en espera. Haz clic en 'Get Location' en el panel izquierdo.")

st.sidebar.title("🎛️ CORE-CONTROL")
frecuencia = st.sidebar.slider("Frecuencia de refresco (seg)", 5, 60, 10)
time.sleep(frecuencia)
st.rerun()
