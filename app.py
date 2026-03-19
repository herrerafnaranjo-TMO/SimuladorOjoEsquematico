import streamlit as st
import numpy as np
import plotly.graph_objects as go
from PIL import Image
import requests
from io import BytesIO

# =================================================================
# 1. CONFIGURACIÓN Y ESTILO (Debe ser lo primero)
# =================================================================
st.set_page_config(page_title="TMO UTA: Óptica y Refracción", layout="wide")

# Blindaje CSS contra el Dark Mode y para Consistencia Clínica
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA !important; }
    h1, h2, h3, h4, p, span, label, .stMarkdown { color: #1A202C !important; }
    input { background-color: #FFFFFF !important; color: #1A202C !important; border: 1px solid #CBD5E0 !important; }
    div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #1A202C !important; }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #2D3748 !important; }
    .streamlit-expanderHeader { color: #2D3748 !important; background-color: #EDF2F7 !important; }
    header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# =================================================================
# 2. CABECERA INSTITUCIONAL (Sincronización Logo-Texto)
# =================================================================
url_logo_raw = "https://raw.githubusercontent.com/herrerafnaranjo-TMO/SimuladorOjoEsquematico/main/Logo-UTA-PNG/Logo%20UTA%20PNG/png_alta/Vertical.png"

st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 10px; gap: 20px;">
        <div style="flex: 0 0 110px; text-align: center;">
            <img src="{url_logo_raw}" style="width: 110px; height: auto; display: block;">
        </div>
        <div style="flex: 1; border-left: 2px solid #E2E8F0; padding-left: 20px; line-height: 1.2;">
            <h4 style="margin: 0px; color: #4A5568; font-weight: normal; font-size: 1.0rem; font-family: sans-serif; text-transform: uppercase; letter-spacing: 0.5px;">
                Tecnología Médica en Oftalmología y Optometría
            </h4>
            <h1 style="margin: 0px; margin-top: 5px; color: #003366; font-weight: 800; font-size: 2.1rem; font-family: sans-serif; letter-spacing: -1px;">
                Óptica y Refracción Aplicada
            </h1>
        </div>
    </div>
    <hr style="margin-top: 5px; margin-bottom: 25px; border: 0.5px solid #CBD5E0; opacity: 0.5;">
""", unsafe_allow_html=True)

# =================================================================
# 3. MOTOR DE CÁLCULO Y FÍSICA ÓPTICA (Gullstrand-LeGrand)
# =================================================================
def format_diopter(val): return f"{val:+.2f}"

def calcular_optica(esf, cil, eje):
    n_v, dist_retina = 1.336, 24.385 
    P_ojo = 58.636 
    
    m1_pwr = P_ojo - (esf + cil) 
    m2_pwr = P_ojo - esf        
    cmc_pwr = P_ojo - (esf + (cil / 2))
    
    f1 = (n_v / m1_pwr) * 1000 + 1.602
    f2 = (n_v / m2_pwr) * 1000 + 1.602
    cmc = (n_v / cmc_pwr) * 1000 + 1.602
    
    if cil <= 0:
        f_neg, f_pos = (esf, cil, eje), (esf + cil, -cil, (eje + 90) % 180)
    else:
        f_neg, f_pos = (esf + cil, -cil, (eje + 90) % 180), (esf, cil, eje)
        
    f_bic = {"c1": esf + cil, "e1": eje, "c2": esf, "e2": (eje + 90) % 180}
    
    return {
        "focos": {"f1": f1, "f2": f2, "cmc": cmc, "retina": dist_retina},
        "eje_rad": np.radians(eje),
        "poderes": {"m1": m1_pwr, "m2": m2_pwr},
        "formulas": {"neg": f_neg, "pos": f_pos, "bic": f_bic}
    }

# =================================================================
# 4. RENDERIZADO 3D (Anatomía Completa y Rayos)
# =================================================================
def generar_ojo_3d(res):
    f1, f2, retina, ang = res['focos']['f1'], res['focos']['f2'], res['focos']['retina'], res['eje_rad']
    fig = go.Figure()
    
    # Eje Óptico
    fig.add_trace(go.Scatter3d(x=[0, 26], y=[0, 0], z=[0, 0], mode='lines', 
                               line=dict(color='gray', width=1, dash='dash'), name="Eje Óptico"))

    # A. Córnea y Meridianos
    r_c = 7.7
    t, p = np.linspace(0, 0.8, 25), np.linspace(0, 2*np.pi, 50) 
    T, P = np.meshgrid(t, p)
    Xc, Yc, Zc = r_c - r_c * np.cos(T), r_c * np.sin(T) * np.cos(P), r_c * np.sin(T) * np.sin(P)
    fig.add_trace(go.Surface(x=Xc, y=Yc, z=Zc, colorscale='Blues', opacity=0.15, showscale=False, name="Córnea"))

    t_arco = np.linspace(0, 0.7, 50) 
    # M1 (Cian) y M2 (Magenta)
    for a, c, n in [(ang, 'cyan', 'M1'), (ang + np.pi/2, 'magenta', 'M2')]:
        xm = r_c - r_c * np.cos(t_arco)
        ym, zm = r_c * np.sin(t_arco) * np.sin(a), r_c * np.sin(t_arco) * np.cos(a)
        fig.add_trace(go.Scatter3d(x=xm, y=ym, z=zm, mode='lines', line=dict(color=c, width=10), name=f"Meridiano {n}"))
        fig.add_trace(go.Scatter3d(x=xm, y=-ym, z=-zm, mode='lines', line=dict(color=c, width=10), showlegend=False))

    # B. Cristalino (Caras Anterior y Posterior)
    r_lens, p_lens = np.linspace(0, 4.5, 20), np.linspace(0, 2*np.pi, 40)
    R_L, P_L = np.meshgrid(r_lens, p_lens)
    Y_L, Z_L = R_L * np.cos(P_L), R_L * np.sin(P_L)
    fig.add_trace(go.Surface(x=13.6 - np.sqrt(10.0**2 - R_L**2), y=Y_L, z=Z_L, colorscale='Greens', opacity=0.3, showscale=False, name="Cristalino"))
    fig.add_trace(go.Surface(x=1.2 + np.sqrt(6.0**2 - R_L**2), y=Y_L, z=Z_L, colorscale='Greens', opacity=0.3, showscale=False, showlegend=False))

    # C. Retina (Imagen Real)
    try:
        resp = requests.get("https://github.com/herrerafnaranjo-TMO/SimuladorOjoEsquematico/raw/main/img/FOMACULA.jpg", timeout=5)
        img = Image.open(BytesIO(resp.content)).convert('RGB').resize((150, 150))
        y, z = np.linspace(-4, 4, 150), np.linspace(-4, 4, 150)
        Y, Z = np.meshgrid(y, z)
        fig.add_trace(go.Surface(x=np.full_like(Y, retina), y=Y, z=Z, surfacecolor=np.flipud(np.dot(np.array(img), [0.2989, 0.5870, 0.1140])), showscale=False, opacity=0.9, name="Retina"))
    except:
        fig.add_trace(go.Surface(x=np.full((2,2), retina), y=[[-4,4],[-4,4]], z=[[-4,-4],[4,4]], colorscale=[[0,'red'],[1,'red']], opacity=0.5))

    # D. Focales y Rayos Paraxiales
    fl = 2.0
    # Focal M1 (Cian) y M2 (Magenta)
    fig.add_trace(go.Scatter3d(x=[f1, f1], y=[-fl*np.sin(ang+np.pi/2), fl*np.sin(ang+np.pi/2)], z=[fl*np.cos(ang+np.pi/2), -fl*np.cos(ang+np.pi/2)], mode='lines', line=dict(color='cyan', width=12), name="Línea Focal M1"))
    fig.add_trace(go.Scatter3d(x=[f2, f2], y=[-fl*np.sin(ang), fl*np.sin(ang)], z=[fl*np.cos(ang), -fl*np.cos(ang)], mode='lines', line=dict(color='magenta', width=12), name="Línea Focal M2"))
    fig.add_trace(go.Scatter3d(x=[res['focos']['cmc']], y=[0], z=[0], mode='markers', marker=dict(size=10, color='yellow', symbol='diamond'), name="CMC"))

    # Rayos Paraxiales
    r_p = 3.5
    for a, c, f in [(ang, 'cyan', f1), (ang + np.pi/2, 'magenta', f2)]:
        y_p, z_p = r_p * np.sin(a), r_p * np.cos(a)
        x_c = r_c - np.sqrt(r_c**2 - y_p**2 - z_p**2)
        fig.add_trace(go.Scatter3d(x=[x_c, f], y=[y_p, 0], z=[z_p, 0], mode='lines', line=dict(color=c, width=3, dash='dot'), showlegend=False))
        fig.add_trace(go.Scatter3d(x=[x_c, f], y=[-y_p, 0], z=[-z_p, 0], mode='lines', line=dict(color=c, width=3, dash='dot'), showlegend=False))

    fig.update_layout(
        scene=dict(xaxis=dict(title='ALX (mm)', range=[-1, 26], backgroundcolor="rgb(230, 235, 245)", showbackground=True),
                   yaxis=dict(range=[-8, 8], showbackground=False), zaxis=dict(range=[-8, 8], showbackground=False),
                   aspectratio=dict(x=3, y=1, z=1), camera=dict(eye=dict(x=1.5, y=-2.5, z=0.8))),
        paper_bgcolor="#F8F9FA", plot_bgcolor="#F8F9FA", font=dict(color="#1A202C"), margin=dict(l=0, r=0, b=0, t=0)
    )
    return fig

# =================================================================
# 5. INTERFAZ PRINCIPAL
# =================================================================
st.subheader("Parámetros Clínicos (Refracción del Ojo Desnudo)")
c1, c2, c3 = st.columns(3)
esf = c1.number_input("Esfera (D)", value=0.00, step=0.25)
cil = c2.number_input("Cilindro (D)", value=0.00, step=0.25)
eje = c3.number_input("Eje (°)", 0, 180, 90, 1)

res = calcular_optica(esf, cil, eje)
st.plotly_chart(generar_ojo_3d(res), use_container_width=True)

# Panel de Métricas SBE
st.markdown("---")
st.subheader("Análisis de Semiología Basada en la Evidencia (SBE)")
f, b = res["formulas"], res["formulas"]["bic"]
m1, m2, m3 = st.columns(3)
m1.metric("Cilindro Negativo", f"{format_diopter(f['neg'][0])} / {format_diopter(f['neg'][1])} x {f['neg'][2]}°")
m2.metric("Cilindro Positivo", f"{format_diopter(f['pos'][0])} / {format_diopter(f['pos'][1])} x {f['pos'][2]}°")
m3.metric("Bicilindro (Cruz)", f"{format_diopter(b['c1'])}x{b['e1']}° | {format_diopter(b['c2'])}x{b['e2']}°")

st.latex(r"P_{E} = P_C + P_L - \frac{d}{n_{aq}} P_C P_L")
st.markdown(f"*Poder Equivalente Total ($P_E$):* 58.636 D. | *Retina ($F'$):* {res['focos']['retina']:.3f} mm.")

# =================================================================
# 6. MÓDULO DE EVALUACIÓN CLÍNICA (Lógica Javal)
# =================================================================
st.markdown("---")
st.subheader("🎓 Evaluación de Diagnóstico Refractivo")

def determinar_diagnostico_real(f1, f2, ret, eje, cil):
    tol = 0.05
    en_ret = lambda f: abs(f - ret) < tol
    pre_ret = lambda f: f < (ret - tol)
    post_ret = lambda f: f > (ret + tol)
    eje_eval = eje if cil <= 0 else (eje + 90) % 180
    
    if (0 <= eje_eval <= 30) or (150 <= eje_eval <= 180): regla = "a favor de la regla"
    elif (60 <= eje_eval <= 120): regla = "en contra de la regla"
    else: regla = "oblicuo"

    if en_ret(f1) and en_ret(f2): return "Emetropía"
    if (en_ret(f1) and pre_ret(f2)) or (en_ret(f2) and pre_ret(f1)): return f"Astigmatismo miópico simple {regla}"
    if (en_ret(f1) and post_ret(f2)) or (en_ret(f2) and post_ret(f1)): return f"Astigmatismo hipermetrópico simple {regla}"
    if pre_ret(f1) and pre_ret(f2):
        return "Miopía pura" if abs(f1-f2) < tol else f"Astigmatismo miópico compuesto {regla}"
    if post_ret(f1) and post_ret(f2):
        return "Hipermetropía pura" if abs(f1-f2) < tol else f"Astigmatismo hipermetrópico compuesto {regla}"
    if (pre_ret(f1) and post_ret(f2)) or (pre_ret(f2) and post_ret(f1)): return f"Astigmatismo mixto {regla}"
    return "Astigmatismo complejo"

opciones = ["Emetropía", "Miopía pura", "Hipermetropía pura", "Astigmatismo miópico simple a favor de la regla", "Astigmatismo miópico simple en contra de la regla", "Astigmatismo miópico compuesto a favor de la regla", "Astigmatismo miópico compuesto en contra de la regla", "Astigmatismo hipermetrópico simple a favor de la regla", "Astigmatismo hipermetrópico simple en contra de la regla", "Astigmatismo hipermetrópico compuesto a favor de la regla", "Astigmatismo hipermetrópico compuesto en contra de la regla", "Astigmatismo mixto a favor de la regla", "Astigmatismo mixto en contra de la regla", "Astigmatismo miópico simple oblicuo", "Astigmatismo miópico compuesto oblicuo", "Astigmatismo hipermetrópico simple oblicuo", "Astigmatismo hipermetrópico compuesto oblicuo", "Astigmatismo mixto oblicuo"]

col_ev, col_inf = st.columns([2, 1])
with col_ev:
    seleccion = st.selectbox("Seleccione su diagnóstico clínico:", ["Seleccione una opción..."] + opciones)
    real = determinar_diagnostico_real(res['focos']['f1'], res['focos']['f2'], res['focos']['retina'], eje, cil)
    if seleccion != "Seleccione una opción...":
        if seleccion.lower() == real.lower(): st.success(f"✅ ¡Correcto! Diagnóstico: {real.capitalize()}.")
        else: st.error(f"❌ Incorrecto. Pista: Con eje {eje}°, el diagnóstico es {real}.")
with col_inf:
    with st.expander("Recordatorio de Regla"):
        st.write("* **WTR:** Eje (-) en 180° ± 30°.\n* **ATR:** Eje (-) en 90° ± 30°.\n* **Oblicuo:** 31°-59° o 121°-149°.")

# --- FIRMA FINAL ---
st.markdown("---")
st.markdown(f"<div style='text-align: center; padding: 20px; color: #718096; font-style: italic;'>Diseñador: <strong>TMO Felipe Naranjo H.</strong><br>© 2026 Universidad de Tarapacá - Arica, Chile</div>", unsafe_allow_html=True)
