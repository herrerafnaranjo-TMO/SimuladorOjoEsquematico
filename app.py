import streamlit as st
import numpy as np
import plotly.graph_objects as go
from PIL import Image
import requests
from io import BytesIO

# =================================================================
# 1. CONFIGURACIÓN Y BLINDAJE VISUAL GLOBAL
# =================================================================
st.set_page_config(page_title="TMO UTA: Óptica y Refracción Aplicada", layout="wide")

# Inyección de CSS para forzar legibilidad clínica (Independiente del Tema del Sistema)
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
# 3. MOTOR DE CÁLCULO Y FÍSICA ÓPTICA (Gullstrand)
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
# 4. RENDERIZADO 3D (Textura Real y Leyenda Blindada)
# =================================================================
def generar_ojo_3d(res):
    f1, f2, retina, ang = res['focos']['f1'], res['focos']['f2'], res['focos']['retina'], res['eje_rad']
    fig = go.Figure()
    
    # Eje Óptico
    fig.add_trace(go.Scatter3d(x=[0, 26], y=[0, 0], z=[0, 0], mode='lines', 
                               line=dict(color='white', width=1, dash='dash'), name="Eje Óptico"))

    # A. Córnea y Meridianos
    r_c = 7.7
    t, p = np.linspace(0, 0.8, 25), np.linspace(0, 2*np.pi, 50) 
    T, P = np.meshgrid(t, p)
    Xc = r_c - r_c * np.cos(T)
    Yc, Zc = r_c * np.sin(T) * np.cos(P), r_c * np.sin(T) * np.sin(P)
    fig.add_trace(go.Surface(x=Xc, y=Yc, z=Zc, colorscale='Blues', opacity=0.2, showscale=False, name="Córnea"))

    t_arco = np.linspace(0, 0.7, 50) 
    # M1 (Cian) y M2 (Magenta)
    xm1, ym1, zm1 = r_c - r_c * np.cos(t_arco), r_c * np.sin(t_arco) * np.sin(ang), r_c * np.sin(t_arco) * np.cos(ang)
    fig.add_trace(go.Scatter3d(x=xm1, y=ym1, z=zm1, mode='lines', line=dict(color='cyan', width=10), name="Meridiano M1"))
    fig.add_trace(go.Scatter3d(x=xm1, y=-ym1, z=-zm1, mode='lines', line=dict(color='cyan', width=10), showlegend=False))

    ang2 = ang + np.pi/2
    xm2, ym2, zm2 = r_c - r_c * np.cos(t_arco), r_c * np.sin(t_arco) * np.sin(ang2), r_c * np.sin(t_arco) * np.cos(ang2)
    fig.add_trace(go.Scatter3d(x=xm2, y=ym2, z=zm2, mode='lines', line=dict(color='magenta', width=10), name="Meridiano M2"))
    fig.add_trace(go.Scatter3d(x=xm2, y=-ym2, z=-zm2, mode='lines', line=dict(color='magenta', width=10), showlegend=False))

    # B. Cristalino (Caras Anterior y Posterior)
    r_lens, p_lens = np.linspace(0, 4.5, 20), np.linspace(0, 2*np.pi, 40)
    R_L, P_L = np.meshgrid(r_lens, p_lens)
    Y_L, Z_L = R_L * np.cos(P_L), R_L * np.sin(P_L)
    fig.add_trace(go.Surface(x=13.6 - np.sqrt(10.0**2 - R_L**2), y=Y_L, z=Z_L, colorscale='Greens', opacity=0.35, showscale=False, name="Cristalino"))
    fig.add_trace(go.Surface(x=1.2 + np.sqrt(6.0**2 - R_L**2), y=Y_L, z=Z_L, colorscale='Greens', opacity=0.35, showscale=False, showlegend=False))

    # C. Retina (Textura Real Restaurada)
    img_url = "https://github.com/herrerafnaranjo-TMO/SimuladorOjoEsquematico/raw/main/img/FOMACULA.jpg"
    try:
        resp = requests.get(img_url, timeout=5)
        img = Image.open(BytesIO(resp.content)).convert('RGB').resize((150, 150))
        y, z = np.linspace(-4, 4, 150), np.linspace(-4, 4, 150)
        Y, Z = np.meshgrid(y, z)
        fig.add_trace(go.Surface(
            x=np.full_like(Y, retina), y=Y, z=Z,
            surfacecolor=np.flipud(np.dot(np.array(img), [0.2989, 0.5870, 0.1140])),
            colorscale=[[0, 'rgb(0,0,0)'], [1, 'rgb(255,69,0)']], # Coloración fúndica
            showscale=False, opacity=0.9, name="Retina"
        ))
    except:
        fig.add_trace(go.Surface(x=np.full((2,2), retina), y=[[-4,4],[-4,4]], z=[[-4,-4],[4,4]], colorscale=[[0,'red'],[1,'red']], opacity=0.5))

    # D. Focales y CMC
    fl = 2.0
    af1, af2 = ang + np.pi/2, ang
    fig.add_trace(go.Scatter3d(x=[f1, f1], y=[-fl*np.sin(af1), fl*np.sin(af1)], z=[fl*np.cos(af1), -fl*np.cos(af1)], mode='lines', line=dict(color='cyan', width=12), name="Línea Focal M1"))
    fig.add_trace(go.Scatter3d(x=[f2, f2], y=[-fl*np.sin(af2), fl*np.sin(af2)], z=[fl*np.cos(af2), -fl*np.cos(af2)], mode='lines', line=dict(color='magenta', width=12), name="Línea Focal M2"))
    fig.add_trace(go.Scatter3d(x=[res['focos']['cmc']], y=[0], z=[0], mode='markers', marker=dict(size=10, color='yellow', symbol='diamond'), name="CMC"))

    # E. Trazado de Rayos
    r_pupil = 3.5
    for a, c, f in [(ang, 'cyan', f1), (ang + np.pi/2, 'magenta', f2)]:
        y_p, z_p = r_pupil * np.sin(a), r_pupil * np.cos(a)
        x_c = r_c - np.sqrt(r_c**2 - y_p**2 - z_p**2)
        fig.add_trace(go.Scatter3d(x=[x_c, f], y=[y_p, 0], z=[z_p, 0], mode='lines', line=dict(color=c, width=3, dash='dot'), showlegend=False))
        fig.add_trace(go.Scatter3d(x=[x_c, f], y=[-y_p, 0], z=[-z_p, 0], mode='lines', line=dict(color=c, width=3, dash='dot'), showlegend=False))

    # DISEÑO DE ESCENA CON BLINDAJE DE LEYENDA (TMO UTA)
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='ALX (mm)', range=[-1, 26], backgroundcolor="rgb(230, 235, 245)", showbackground=True, tickfont=dict(color="#2c3e50")),
            yaxis=dict(range=[-8, 8], showbackground=False, tickfont=dict(color="#2c3e50")),
            zaxis=dict(range=[-8, 8], showbackground=False, tickfont=dict(color="#2c3e50")),
            aspectratio=dict(x=3, y=1, z=1), camera=dict(eye=dict(x=1.5, y=-2.5, z=0.8))
        ),
        paper_bgcolor="#F8F9FA", plot_bgcolor="#F8F9FA", font=dict(color="#1A202C", size=12), margin=dict(l=0, r=0, b=0, t=0),
        # --- BLINDAJE EXPLÍCITO DE LA LEYENDA ---
        showlegend=True,
        legend=dict(
            font=dict(color="#000000", size=11), # Texto Negro Absoluto para Contraste
            bgcolor="rgba(255,255,255,0.7)", # Fondo Blanco Semitransparente
            bordercolor="#CBD5E0",borderwidth=1,
            x=0.02, y=0.98, xanchor='left', yanchor='top' # Posición esquina superior izquierda
        )
    )
    return fig

# =================================================================
# 5. UI Y EVALUACIÓN SBE
# =================================================================
st.subheader("Ingrese aquí la fórmula esferocilíndrica")
c1, c2, c3 = st.columns(3)
esf = c1.number_input("Esfera (D)", value=0.00, step=0.25)
cil = c2.number_input("Cilindro (D)", value=0.00, step=0.25)
eje = c3.number_input("Eje (°)", 0, 180, 90, 1)

res = calcular_optica(esf, cil, eje)
st.plotly_chart(generar_ojo_3d(res), use_container_width=True)

# Panel de Métricas SBE
st.markdown("---")
st.subheader("Análisis de Transposición y Bicilindro")
f, b = res["formulas"], res["formulas"]["bic"]
m1, m2, m3 = st.columns(3)
m1.metric("Cilindro Negativo", f"{format_diopter(f['neg'][0])} / {format_diopter(f['neg'][1])} x {f['neg'][2]}°")
m2.metric("Cilindro Positivo", f"{format_diopter(f['pos'][0])} / {format_diopter(f['pos'][1])} x {f['pos'][2]}°")
m3.metric("Bicilindro", f"{format_diopter(b['c1'])}x{b['e1']}° | {format_diopter(b['c2'])}x{b['e2']}°")

# Evaluación
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
    if pre_ret(f1) and pre_ret(f2): return "Miopía pura" if abs(f1-f2) < tol else f"Astigmatismo miópico compuesto {regla}"
    if post_ret(f1) and post_ret(f2): return "Hipermetropía pura" if abs(f1-f2) < tol else f"Astigmatismo hipermetrópico compuesto {regla}"
    if (pre_ret(f1) and post_ret(f2)) or (pre_ret(f2) and post_ret(f1)): return f"Astigmatismo mixto {regla}"
    return "Astigmatismo complejo"

opciones = ["Emetropía", "Miopía pura", "Hipermetropía pura", "Astigmatismo miópico simple a favor de la regla", "Astigmatismo miópico simple en contra de la regla", "Astigmatismo miópico compuesto a favor de la regla", "Astigmatismo miópico compuesto en contra de la regla", "Astigmatismo hipermetrópico simple a favor de la regla", "Astigmatismo hipermetrópico simple en contra de la regla", "Astigmatismo hipermetrópico compuesto a favor de la regla", "Astigmatismo hipermetrópico compuesto en contra de la regla", "Astigmatismo mixto a favor de la regla", "Astigmatismo mixto en contra de la regla", "Astigmatismo miópico simple oblicuo", "Astigmatismo miópico compuesto oblicuo", "Astigmatismo hipermetrópico simple oblicuo", "Astigmatismo hipermetrópico compuesto oblicuo", "Astigmatismo mixto oblicuo"]

seleccion = st.selectbox("Seleccione su diagnóstico clínico:", ["Seleccione una opción..."] + opciones)
real = determinar_diagnostico_real(res['focos']['f1'], res['focos']['f2'], res['focos']['retina'], eje, cil)

if seleccion != "Seleccione una opción...":
    if seleccion.lower() == real.lower(): st.success(f"✅ ¡Correcto! Diagnóstico: {real.capitalize()}.")
    else: st.error(f"❌ Incorrecto. El diagnóstico real es: {real}.")

# FIRMA
st.markdown(f"<div style='text-align: center; padding: 20px; color: #718096; font-style: italic;'>Diseñador: <strong>TMO Felipe Naranjo H.</strong><br>© 2026 Universidad de Tarapacá - Arica, Chile</div>", unsafe_allow_html=True)
