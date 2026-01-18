import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import tempfile
import json
import os
from datetime import date
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 0. KONFIGURATION & CSS (THE SAAS LOOK - FIXED)
# ==========================================
st.set_page_config(
    page_title="ImmoAsset Pro", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="🏢"
)

# --- CUSTOM CSS (JETZT MIT TEXT-FARB-ZWANG) ---
st.markdown("""
<style>
    /* 1. GRUNDGERÜST: Erzwinge hellen Hintergrund & dunkle Schrift */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Alle Standard-Texte dunkel machen (gegen Dark-Mode-Bug) */
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, li, span {
        color: #0f172a !important; /* Dunkles Slate */
    }

    /* 2. SIDEBAR (Dunkel bleiben, Schrift hell) */
    section[data-testid="stSidebar"] {
        background-color: #1e293b;
    }
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span {
        color: #f1f5f9 !important; /* Helles Weiß/Grau */
    }
    
    /* 3. METRIC CARDS (Das war das Problem!) */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }
    /* Label der Metrik (klein oben) */
    div[data-testid="stMetricLabel"] p {
        color: #64748b !important; /* Mittelgrau */
        font-size: 0.9rem;
    }
    /* Wert der Metrik (groß) */
    div[data-testid="stMetricValue"] div {
        color: #0f172a !important; /* Tiefschwarz/Blau */
        font-weight: 700;
    }
    /* Delta Wert (klein unten) */
    div[data-testid="stMetricDelta"] div {
        color: #10b981 !important; /* Grün als Standard, wird von Streamlit teils überschrieben */
    }

    /* 4. TABELLEN */
    div[data-testid="stDataFrame"] {
        background-color: white;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    /* Tabellen-Text erzwingen */
    div[data-testid="stDataFrame"] div {
        color: #334155 !important;
    }

    /* 5. TABS */
    button[data-baseweb="tab"] {
        color: #64748b;
        font-weight: 500;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #2563eb !important; /* Blau für aktiven Tab */
        border-bottom-color: #2563eb !important;
    }

    /* 6. BUTTONS */
    .stButton button {
        background-color: #2563eb;
        color: white !important;
        border-radius: 6px;
        border: none;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton button:hover {
        background-color: #1d4ed8;
    }

    /* 7. STATUS BADGES & ALERTS */
    div[data-testid="stAlert"] {
        padding: 10px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 0.1 LOGIN & DATA
# ==========================================
def check_password():
    try:
        correct_password = st.secrets["password"]
    except:
        correct_password = "123"

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.markdown("### 🔒 Login")
            pwd = st.text_input("Passwort eingeben:", type="password")
            if pwd == correct_password:
                st.session_state["password_correct"] = True
                st.rerun()
        return False
    return True

if not check_password(): st.stop()

START_JAHR = 2026
DATA_FILE = "portfolio_data_v6_saas.json"
MEDIA_DIR = "expose_files"
if not os.path.exists(MEDIA_DIR): os.makedirs(MEDIA_DIR)

# --- DEFAULT DATEN ---
DEFAULT_OBJEKTE = {
    "Meckelfeld (Ziel-Preis 160k)": {
        "Adresse": "Am Bach, 21217 Seevetal", "qm": 59, "zimmer": 2.0, "bj": 1965, "Kaufpreis": 160000, "Nebenkosten_Quote": 0.07, 
        "Renovierung": 0, "Heizung_Puffer": 2000, "AfA_Satz": 0.03, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 632.50, "Hausgeld_Gesamt": 368, "Kosten_n_uml": 130, "Marktmiete_m2": 13.45, "Energie_Info": "Gas (2022 neu), F",
        "Status": "Vermietet (Treppe)", "Link": "", "Bild_URLs": [], "PDF_Path": "", "Archiviert": False, 
        "Basis_Info": "Zielpreis 160k. Miet-Treppe fix.", "Summary_Case": "Cashflow-King mit Steuer-Hebel.", "Summary_Pros": "Provisionsfrei, Heizung neu.", "Summary_Cons": "Energie F."
    },
    "Neu Wulmstorf (Neubau-Anker)": {
        "Adresse": "Hauptstraße 43, 21629 Neu Wulmstorf", "qm": 65.79, "zimmer": 2.0, "bj": 2016, "Kaufpreis": 249000, "Nebenkosten_Quote": 0.07, 
        "Renovierung": 0, "Heizung_Puffer": 0, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 920, "Hausgeld_Gesamt": 260, "Kosten_n_uml": 60, "Marktmiete_m2": 14.50, "Energie_Info": "Gas+Solar (Bj 2016), B",
        "Status": "Leer ab 02/2026", "Link": "", "Bild_URLs": [], "PDF_Path": "", "Archiviert": False, 
        "Basis_Info": "Neubau 2016. Provisionsfrei.", "Summary_Case": "Sicherheits-Anker. Wertsicherung.", "Summary_Pros": "Provisionsfrei, Technik top.", "Summary_Cons": "Lage B73."
    },
    "Elmshorn (Terrasse & Staffel)": {
        "Adresse": "Johannesstr. 24-28, 25335 Elmshorn", "qm": 75.67, "zimmer": 2.0, "bj": 1994, "Kaufpreis": 229000, "Nebenkosten_Quote": 0.1207, 
        "Renovierung": 0, "Heizung_Puffer": 1000, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 665, "Hausgeld_Gesamt": 370, "Kosten_n_uml": 165, "Marktmiete_m2": 11.00, "Energie_Info": "Gas Bj 2012 (C)",
        "Status": "Vermietet (Staffel)", "Link": "", "Bild_URLs": [], "PDF_Path": "", "Archiviert": False, 
        "Basis_Info": "Mietstaffel (26/27). Heizung 2012.", "Summary_Case": "Aufsteiger mit Rendite-Turbo.", "Summary_Pros": "Mietstaffel fix, Terrasse.", "Summary_Cons": "Hohes Hausgeld."
    },
    "Harburg (Maisonette/Lifestyle)": {
        "Adresse": "Marienstr. 52, 21073 Hamburg", "qm": 71, "zimmer": 2.0, "bj": 1954, "Kaufpreis": 230000, "Nebenkosten_Quote": 0.1107, 
        "Renovierung": 0, "Heizung_Puffer": 5000, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 720, "Hausgeld_Gesamt": 204, "Kosten_n_uml": 84, "Marktmiete_m2": 12.00, "Energie_Info": "Gas-Etage (D)",
        "Status": "Vermietet", "Link": "", "Bild_URLs": [], "PDF_Path": "", "Archiviert": False, 
        "Basis_Info": "Liebhaber-Objekt. Negativer CF.", "Summary_Case": "Trophy Asset / Spekulation.", "Summary_Pros": "Galerie, Uninähe.", "Summary_Cons": "CF negativ, WEG-Themen."
    },
    "Buxtehude (5-Zi Volumen)": {
        "Adresse": "Stader Str., Buxtehude", "qm": 109.07, "zimmer": 5.0, "bj": 1972, "Kaufpreis": 236000, "Nebenkosten_Quote": 0.1057, "Miete_Start": 925, "Kosten_n_uml": 120, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02, "Renovierung": 0, "Heizung_Puffer": 2000, "Hausgeld_Gesamt": 380, "Status": "Vermietet", "Link": "", "Bild_URLs": [], "PDF_Path": "", "Energie_Info": "F", "Marktmiete_m2": 10, "Archiviert": True, "Basis_Info": "Viel Fläche, aber Energie F.", "Summary_Case": "Substanz-Deal.", "Summary_Pros": "Günstiger qm-Preis.", "Summary_Cons": "Energie F."
    },
    "Stade (Altbau-Schnapper)": {
        "Adresse": "Zentrum, Stade", "qm": 67.0, "zimmer": 2.0, "bj": 1905, "Kaufpreis": 159500, "Nebenkosten_Quote": 0.1057, "Miete_Start": 575, "Kosten_n_uml": 69, "AfA_Satz": 0.025, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02, "Renovierung": 2000, "Heizung_Puffer": 5000, "Hausgeld_Gesamt": 170, "Status": "Vermietet", "Link": "", "Bild_URLs": [], "PDF_Path": "", "Energie_Info": "Gas-Etage", "Marktmiete_m2": 10, "Archiviert": True, "Basis_Info": "Heizung muss neu. Hohe AfA.", "Summary_Case": "Günstiger Einkauf.", "Summary_Pros": "Hohe AfA.", "Summary_Cons": "Heizungstausch."
    }
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = data.copy()
            for k, v in DEFAULT_OBJEKTE.items():
                if k not in merged: merged[k] = v
            return merged
    return DEFAULT_OBJEKTE

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

OBJEKTE = load_data()

# ==========================================
# 1. BERECHNUNG (CORE LOGIC)
# ==========================================
def clean_text(text):
    if not text: return ""
    return text.replace("€", "EUR").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")

def create_pdf_expose(obj_name, data, res):
    # Einfacher PDF Generator
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.set_text_color(100)
            self.cell(0, 10, 'ImmoAsset Pro Summary', 0, 1, 'R')
            self.ln(5)
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"{clean_text(obj_name)}", 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, f"Kaufpreis: {res['KP']:,.0f} EUR", 0, 1)
    pdf.cell(0, 8, f"Rendite (Start): {res['Rendite']:.2f}% | EKR (10J): {res['CAGR']:.2f}%", 0, 1)
    pdf.ln(5)
    pdf.multi_cell(0, 6, f"Strategie: {clean_text(data.get('Summary_Case'))}")
    return pdf.output(dest='S').encode('latin-1', 'replace')

def calculate_investment(obj_name, params, global_zins, global_tilgung, global_steuer):
    kp = params["Kaufpreis"]
    zins = params.get("Zins_Indiv", global_zins)
    miet_st = params.get("Mietsteigerung", 0.02)
    wert_st = params.get("Wertsteigerung_Immo", 0.02)
    afa_rate = params.get("AfA_Satz", 0.02)
    
    nk = kp * params["Nebenkosten_Quote"]
    invest = nk + params.get("Renovierung",0) + params.get("Heizung_Puffer",0)
    loan = kp
    rate_pa = loan * (zins + global_tilgung)
    
    rent_start = params["Miete_Start"] * 12
    
    is_meckelfeld = "Meckelfeld" in obj_name
    is_elmshorn = "Elmshorn" in obj_name and "Terrasse" in obj_name
    
    data = []
    restschuld = loan
    immo_wert = kp
    
    for i in range(21):
        jahr = START_JAHR + i
        
        # Miete Logik
        if is_meckelfeld:
            if jahr < 2027: m = params["Miete_Start"] 
            elif jahr < 2029: m = 690.00
            elif jahr < 2032: m = 727.38
            else: m = 793.50 * (1 + miet_st)**(jahr - 2032)
            rent_yr = m * 12
        elif is_elmshorn:
            if jahr == 2026: rent_yr = 9180 
            elif jahr == 2027: rent_yr = 9780 
            elif jahr > 2027: rent_yr = 9780 * (1 + miet_st)**(i - 2) 
            else: rent_yr = rent_start
        else:
            rent_yr = rent_start * (1 + miet_st)**i
            
        immo_wert *= (1 + wert_st)
        zinsen = restschuld * zins
        tilgung = rate_pa - zinsen
        costs = params["Kosten_n_uml"] * 12
        
        cf_pre_tax = rent_yr - rate_pa - costs
        tax_base = rent_yr - zinsen - (kp*0.8*afa_rate) - costs
        tax = tax_base * global_steuer * -1
        cf_post_tax = cf_pre_tax + tax
        
        restschuld -= tilgung
        
        data.append({
            "Jahr": jahr,
            "Laufzeit": f"Jahr {i+1}",
            "Miete (p.a.)": rent_yr,
            "Miete (mtl.)": rent_yr / 12,
            "CF (vor Steuer)": cf_pre_tax,
            "CF (nach Steuer)": cf_post_tax,
            "Restschuld": restschuld,
            "Immo-Wert": immo_wert,
            "Equity": immo_wert - restschuld
        })

    res_10 = data[9] 
    equity_10 = res_10["Equity"] + sum([d["CF (nach Steuer)"] for d in data[:10]])
    cagr = ((equity_10 / invest)**(0.1) - 1) * 100 if invest > 0 else 0
    avg_cf = sum([d["CF (nach Steuer)"] for d in data[:10]]) / 120
    
    return {
        "Name": obj_name, "Invest": invest, "KP": kp, "Rendite": (rent_start/kp)*100,
        "CAGR": cagr, "Avg_CF": avg_cf, "Gewinn_10J": equity_10 - invest,
        "Detail": data, "Params": params,
        "Used_Zins": zins, "Archiviert": params.get("Archiviert", False)
    }

# ==========================================
# 2. APP LAYOUT (THE SAAS UI)
# ==========================================

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ImmoAsset **Pro**")
    st.caption("v6.1 - SaaS Edition")
    st.markdown("---")
    
    menu = st.radio(
        "Hauptmenü", 
        ["Dashboard", "Objekt-Details", "Einstellungen"], 
        index=0
    )
    
    st.markdown("---")
    st.caption("Globale Annahmen:")
    g_zins = st.number_input("Ø Zins (%)", 1.0, 6.0, 3.80, 0.1) / 100
    g_tilg = st.number_input("Ø Tilgung (%)", 0.0, 10.0, 1.50, 0.1) / 100
    g_steuer = st.number_input("Steuer (%)", 20.0, 50.0, 42.00, 0.5) / 100

# --- DATA PREP ---
results = [calculate_investment(k, v, g_zins, g_tilg, g_steuer) for k, v in OBJEKTE.items()]
active_results = [r for r in results if not r["Archiviert"]]
archive_results = [r for r in results if r["Archiviert"]]

# --- PAGE: DASHBOARD ---
if menu == "Dashboard":
    st.title("👋 Willkommen zurück!")
    st.markdown("Hier ist der aktuelle Status deines Portfolios.")
    
    # 1. KPI ROW (Cards)
    tot_invest = sum(r["Invest"] for r in active_results)
    tot_cf = sum(r["Avg_CF"] for r in active_results)
    avg_ekr = np.mean([r["CAGR"] for r in active_results]) if active_results else 0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Invest (Active)", f"{tot_invest/1000:,.0f}k €", delta=f"{len(active_results)} Units")
    with c2: st.metric("Ø Cashflow / Monat", f"{tot_cf:,.0f} €", delta_color="normal")
    with c3: st.metric("Ø EKR (10J)", f"{avg_ekr:.1f} %", delta="Ziel: >8%")
    with c4: st.metric("Watchlist", f"{len(archive_results)}", delta_color="off")
    
    st.markdown("---")

    # 2. CHARTS (Modern)
    c_chart1, c_chart2 = st.columns([2, 1])
    
    with c_chart1:
        st.subheader("📈 Vermögens-Entwicklung (20 Jahre)")
        years = list(range(START_JAHR, START_JAHR + 21))
        agg_equity = {y: 0 for y in years}
        agg_debt = {y: 0 for y in years}
        for r in active_results:
            for row in r["Detail"]:
                agg_equity[row["Jahr"]] += (row["Immo-Wert"] - row["Restschuld"])
                agg_debt[row["Jahr"]] += row["Restschuld"]
        
        df_wealth = pd.DataFrame({"Jahr": years, "Netto-Vermögen": list(agg_equity.values()), "Bank-Schulden": list(agg_debt.values())})
        
        # Plotly Area Chart Custom
        fig_w = go.Figure()
        fig_w.add_trace(go.Scatter(x=df_wealth["Jahr"], y=df_wealth["Netto-Vermögen"], stackgroup='one', name='Netto-Vermögen', line=dict(color='#10b981', width=0)))
        fig_w.add_trace(go.Scatter(x=df_wealth["Jahr"], y=df_wealth["Bank-Schulden"], stackgroup='one', name='Bank-Schulden', line=dict(color='#ef4444', width=0)))
        fig_w.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=0, b=0), height=300, legend=dict(orientation="h", y=1.1, font=dict(color="#0f172a")), xaxis=dict(color="#334155"), yaxis=dict(color="#334155"))
        st.plotly_chart(fig_w, use_container_width=True)

    with c_chart2:
        st.subheader("🎯 Deal Matrix")
        if active_results:
            bubble_df = pd.DataFrame([{
                "Objekt": r["Name"], "KP": r["KP"], "Rendite": r["Rendite"], 
                "CF": r["Avg_CF"], "Size": r["Invest"]
            } for r in active_results])
            
            fig_b = px.scatter(bubble_df, x="KP", y="Rendite", size="Size", color="CF", 
                               color_continuous_scale=["#ef4444", "#10b981"], hover_name="Objekt")
            fig_b.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(240,242,246,0.5)', height=300, xaxis=dict(color="#334155"), yaxis=dict(color="#334155"))
            st.plotly_chart(fig_b, use_container_width=True)
        else:
            st.info("Keine aktiven Deals.")

    # 3. PORTFOLIO TABLE (Styled)
    st.subheader("📋 Dein Portfolio")
    
    # Create nice DataFrame
    table_data = []
    for r in results:
        status = "🟢 Aktiv" if not r["Archiviert"] else "🔴 Archiv"
        table_data.append({
            "Status": status,
            "Objekt": r["Name"],
            "Preis": r["KP"],
            "Rendite": r["Rendite"],
            "Cashflow": r["Avg_CF"],
            "EKR 10J": r["CAGR"]
        })
    
    df_tab = pd.DataFrame(table_data)
    
    st.dataframe(
        df_tab,
        column_config={
            "Preis": st.column_config.NumberColumn("Kaufpreis", format="%d €"),
            "Rendite": st.column_config.NumberColumn("Brutto-Rendite", format="%.2f %%"),
            "Cashflow": st.column_config.NumberColumn("Ø CF (mtl.)", format="%d €"),
            "EKR 10J": st.column_config.NumberColumn("EK-Rendite", format="%.2f %%"),
            "Status": st.column_config.TextColumn("Status"),
        },
        use_container_width=True,
        hide_index=True
    )

# --- PAGE: DETAIL VIEW ---
elif menu == "Objekt-Details":
    # Selection mit schöner Formatierung im Dropdown
    sorted_keys = sorted(OBJEKTE.keys(), key=lambda x: OBJEKTE[x].get("Archiviert", False))
    sel = st.selectbox("Objekt auswählen:", sorted_keys)
    obj = OBJEKTE[sel]
    res = calculate_investment(sel, obj, g_zins, g_tilg, g_steuer)

    # Header Area
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title(sel)
        st.caption(f"📍 {obj.get('Adresse', 'Keine Adresse')} | 📏 {obj['qm']} m²")
    with col_head2:
        if obj.get("Archiviert"):
            st.error("ARCHIVIERT")
        else:
            st.success("AKTIV")
    
    # TABS LAYOUT (UX IMPROVEMENT)
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Übersicht", "💰 Finanzen & Plan", "📝 Daten & Docs", "⚙️ Bearbeiten"])
    
    with tab1:
        # High Level KPIs
        c1, c2, c3 = st.columns(3)
        c1.metric("Invest (EK)", f"{res['Invest']:,.0f} €")
        c2.metric("Cashflow (Nach Steuer)", f"{res['Avg_CF']:,.0f} €")
        c3.metric("Gewinn nach 10J", f"{res['Gewinn_10J']:,.0f} €")
        
        st.markdown("### Investment Case")
        st.info(obj.get("Summary_Case", "Keine Strategie definiert."))
        
        cc1, cc2 = st.columns(2)
        with cc1: 
            st.markdown("**✅ Pro:**")
            st.markdown(obj.get("Summary_Pros", "-"))
        with cc2:
            st.markdown("**⚠️ Contra:**")
            st.markdown(obj.get("Summary_Cons", "-"))

    with tab2:
        st.markdown("### 10-Jahres-Planung")
        df_detail = pd.DataFrame(res["Detail"])
        st.dataframe(
            df_detail.head(10)[["Laufzeit", "Miete (mtl.)", "CF (vor Steuer)", "CF (nach Steuer)", "Restschuld"]],
            use_container_width=True,
            hide_index=True,
            column_config={"Miete (mtl.)": st.column_config.NumberColumn(format="%.2f €"), "Restschuld": st.column_config.NumberColumn(format="%d €")}
        )
        
        st.markdown("### Langzeit-Ausblick")
        c15, c20 = st.columns(2)
        d15 = res["Detail"][14]
        d20 = res["Detail"][19]
        
        c15.metric("Jahr 15 (Equity)", f"{d15['Equity']:,.0f} €", delta=f"Restschuld: {d15['Restschuld']:,.0f}")
        c20.metric("Jahr 20 (Equity)", f"{d20['Equity']:,.0f} €", delta=f"Restschuld: {d20['Restschuld']:,.0f}")

    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Stammdaten")
            st.write(f"**Baujahr:** {obj['bj']}")
            st.write(f"**Hausgeld:** {obj.get('Hausgeld_Gesamt',0)} €")
            st.write(f"**Energie:** {obj.get('Energie_Info', '-')}")
            if obj.get("Link"): st.markdown(f"[Zum Inserat]({obj['Link']})")
        
        with c2:
            st.markdown("### Dokumente")
            if obj.get("PDF_Path") and os.path.exists(obj["PDF_Path"]):
                with open(obj["PDF_Path"], "rb") as f:
                    st.download_button("📄 Exposé herunterladen", f, "Expose.pdf")
            else:
                st.write("Keine PDF hinterlegt.")
                
            st.markdown("### Bilder")
            if obj.get("Bild_URLs"):
                st.image(obj["Bild_URLs"][0], caption="Titelbild")

    with tab4:
        st.markdown("### Objekt bearbeiten")
        with st.form("edit_form"):
            col_e1, col_e2 = st.columns(2)
            n_kp = col_e1.number_input("Kaufpreis", value=float(obj["Kaufpreis"]))
            n_status = col_e2.checkbox("Archiviert?", value=obj.get("Archiviert", False))
            
            n_case = st.text_area("Investment Case", value=obj.get("Summary_Case", ""))
            
            if st.form_submit_button("Speichern"):
                OBJEKTE[sel]["Kaufpreis"] = n_kp
                OBJEKTE[sel]["Archiviert"] = n_status
                OBJEKTE[sel]["Summary_Case"] = n_case
                save_data(OBJEKTE)
                st.success("Gespeichert!")
                st.rerun()
        
        st.markdown("### Upload")
        up = st.file_uploader("Exposé PDF hochladen", type="pdf")
        if up:
            path = os.path.join(MEDIA_DIR, f"{sel}_expose.pdf")
            with open(path, "wb") as f: f.write(up.getbuffer())
            OBJEKTE[sel]["PDF_Path"] = path
            save_data(OBJEKTE)
            st.success("Hochgeladen!")

# --- PAGE: SETTINGS ---
elif menu == "Einstellungen":
    st.header("⚙️ App Einstellungen")
    st.info("Hier könnten Account-Einstellungen oder API-Keys für Bankanbindungen stehen.")
    st.button("Cache leeren / Neu laden")
