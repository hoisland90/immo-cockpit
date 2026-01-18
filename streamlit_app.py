import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import tempfile
import json
import os
import shutil
from datetime import date
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 0. KONFIGURATION & SETUP
# ==========================================
st.set_page_config(page_title="Immo-Cockpit Master", layout="wide", initial_sidebar_state="expanded")

# CSS für saubere Darstellung
st.markdown("""<style>div[data-baseweb="select"] > div {border-color: #808495 !important; border-width: 1px !important;}</style>""", unsafe_allow_html=True)

# SICHERHEITS-LOGIN
def check_password():
    try:
        correct_password = st.secrets["password"]
    except:
        correct_password = "DeinGeheimesPasswort123"

    def password_entered():
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 Passwort:", type="password", key="pwd_input")
        if st.session_state.get("pwd_input") == correct_password:
            st.session_state["password_correct"] = True
            st.rerun()
        return False
    return True

if not check_password(): st.stop()

START_JAHR = 2026
DATA_FILE = "portfolio_data_master_v1.json" 
MEDIA_DIR = "expose_files"

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# ==========================================
# 0. DATEN (ALLE OBJEKTE)
# ==========================================
DEFAULT_OBJEKTE = {
    # --- DIE AKTIVEN ---
"Buxtehude (Dachterrasse & Lift)": {
        "Adresse": "Buxtehude Süd (Stader Str. Umgebung)", 
        "qm": 66.26, "zimmer": 2.0, "bj": 1992, 
        "Kaufpreis": 172000, "Nebenkosten_Quote": 0.07, # Provisionsfrei!
        "Renovierung": 1000, "Heizung_Puffer": 0, 
        "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 695, # Schätzung (da im Exposé nicht genannt)
        "Hausgeld_Gesamt": 398, "Kosten_n_uml": 140, # Hohes Hausgeld beachten!
        "Marktmiete_m2": 11.50, "Energie_Info": "Gas (1992), 106 kWh (D)",
        "Status": "Vermietet", "Link": "https://www.kleinanzeigen.de/s-anzeige/3302562867", 
        "Bild_URLs": [], "PDF_Path": "", 
        "Archiviert": False, 
        "Basis_Info": "Provisionsfrei! 4. OG mit Lift. Aber: Sehr hohes Hausgeld (398€).", 
        "Summary_Case": "Substanz-Deal. Wenn Miete steigerbar, sehr gut. Achtung bei den BK.", 
        "Summary_Pros": "Provisionsfrei, Fahrstuhl, Dachterrasse.", 
        "Summary_Cons": "Hausgeld frisst Rendite."
    },
    "Harsefeld (1-Zi Einsteiger)": {
        "Adresse": "Zentrum, 21698 Harsefeld", 
        "qm": 36.0, "zimmer": 1.0, "bj": 1985, 
        "Kaufpreis": 84500, "Nebenkosten_Quote": 0.1057, # Mit Makler
        "Renovierung": 500, "Heizung_Puffer": 0, 
        "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 325, # Ist-Miete
        "Hausgeld_Gesamt": 180, "Kosten_n_uml": 60, # Schätzung (fehlt im Exposé)
        "Marktmiete_m2": 10.00, "Energie_Info": "Gas, 105 kWh (D)",
        "Status": "Vermietet seit 2008", "Link": "https://www.kleinanzeigen.de/s-anzeige/3221819015", 
        "Bild_URLs": [], "PDF_Path": "", 
        "Archiviert": False, 
        "Basis_Info": "Kleines Invest, solider Mieter (seit 2008).", 
        "Summary_Case": "Langweiliger, aber solider Cashflow-Anker.", 
        "Summary_Pros": "Günstiger Einstieg (<100k), 4,6% Rendite.", 
        "Summary_Cons": "Mieterhöhung bei Altvertrag schwierig."
    },
    
    "Meckelfeld (Ziel-Preis 160k)": {
        "Adresse": "Am Bach, 21217 Seevetal", "qm": 59, "zimmer": 2.0, "bj": 1965, "Kaufpreis": 160000, "Nebenkosten_Quote": 0.07, 
        "Renovierung": 0, "Heizung_Puffer": 2000, "AfA_Satz": 0.03, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 632.50, "Hausgeld_Gesamt": 368, "Kosten_n_uml": 130, "Marktmiete_m2": 13.45, "Energie_Info": "Gas (2022 neu), F",
        "Status": "Vermietet (Treppe)", "Link": "", "Bild_URLs": [], "PDF_Path": "", 
        "Archiviert": False, "Basis_Info": "Zielpreis 160k. Miet-Treppe fix.", "Summary_Case": "Cashflow-King mit Steuer-Hebel.", "Summary_Pros": "Provisionsfrei, Heizung neu.", "Summary_Cons": "Energie F."
    },
    "Winsen (Optimierter Deal)": {
        "Adresse": "21423 Winsen (Luhe)", "qm": 55.0, "zimmer": 2.0, "bj": 1985, "Kaufpreis": 160080, "Nebenkosten_Quote": 0.1057, 
        "Renovierung": 0, "Heizung_Puffer": 1000, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 633.65, "Hausgeld_Gesamt": 262, "Kosten_n_uml": 80, "Marktmiete_m2": 11.52, "Energie_Info": "Gas-Zentral, Bj 1985",
        "Status": "Vermietet (Top-Miete)", "Link": "", "Bild_URLs": [], "PDF_Path": "", 
        "Archiviert": False, "Basis_Info": "Kaufpreis fiktiv verhandelt.", "Summary_Case": "Solide Substanz, fast neutraler CF.", "Summary_Pros": "Guter Zustand.", "Summary_Cons": "Makler."
    },
    "Neu Wulmstorf (Neubau-Anker)": {
        "Adresse": "Hauptstraße 43, 21629 Neu Wulmstorf", "qm": 65.79, "zimmer": 2.0, "bj": 2016, "Kaufpreis": 249000, "Nebenkosten_Quote": 0.07, 
        "Renovierung": 0, "Heizung_Puffer": 0, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 920, "Hausgeld_Gesamt": 260, "Kosten_n_uml": 60, "Marktmiete_m2": 14.50, "Energie_Info": "Gas+Solar (Bj 2016), B",
        "Status": "Leer ab 02/2026", "Link": "", "Bild_URLs": [], "PDF_Path": "", 
        "Archiviert": False, "Basis_Info": "Neubau 2016. Provisionsfrei.", "Summary_Case": "Sicherheits-Anker. Wertsicherung.", "Summary_Pros": "Provisionsfrei, Technik top.", "Summary_Cons": "Lage B73."
    },
    "Elmshorn (Terrasse & Staffel)": {
        "Adresse": "Johannesstr. 24-28, 25335 Elmshorn", "qm": 75.67, "zimmer": 2.0, "bj": 1994, "Kaufpreis": 229000, "Nebenkosten_Quote": 0.1207, 
        "Renovierung": 0, "Heizung_Puffer": 1000, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 665, "Hausgeld_Gesamt": 370, "Kosten_n_uml": 165, "Marktmiete_m2": 11.00, "Energie_Info": "Gas Bj 2012 (C)",
        "Status": "Vermietet (Staffel)", "Link": "", "Bild_URLs": [], "PDF_Path": "", 
        "Archiviert": False, "Basis_Info": "Mietstaffel (26/27). Heizung 2012.", "Summary_Case": "Aufsteiger mit Rendite-Turbo.", "Summary_Pros": "Mietstaffel fix, Terrasse.", "Summary_Cons": "Hohes Hausgeld."
    },
    
    # --- DIE ARCHIVIERTEN ---
    "Harburg (Maisonette/Lifestyle)": {
        "Adresse": "Marienstr. 52, Hamburg", "qm": 71, "zimmer": 2.0, "bj": 1954, "Kaufpreis": 230000, "Nebenkosten_Quote": 0.1107, 
        "Renovierung": 0, "Heizung_Puffer": 5000, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02, "Miete_Start": 720, "Hausgeld_Gesamt": 204, "Kosten_n_uml": 84, "Marktmiete_m2": 12.00, "Energie_Info": "Gas-Etage (D)", "Status": "Vermietet", "Link": "", "Bild_URLs": [], "PDF_Path": "", 
        "Archiviert": True, "Basis_Info": "Liebhaber-Objekt. Negativer CF.", "Summary_Case": "Spekulation.", "Summary_Pros": "Galerie.", "Summary_Cons": "CF negativ."
    },
    "Buxtehude (5-Zi Volumen)": {
        "Adresse": "Stader Str., Buxtehude", "qm": 109.07, "zimmer": 5.0, "bj": 1972, "Kaufpreis": 236000, "Nebenkosten_Quote": 0.1057, "Miete_Start": 925, "Kosten_n_uml": 120, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02, "Renovierung": 0, "Heizung_Puffer": 2000, "Hausgeld_Gesamt": 380, "Status": "Vermietet", "Link": "", "Bild_URLs": [], "PDF_Path": "", "Energie_Info": "F", "Marktmiete_m2": 10, 
        "Archiviert": True, "Basis_Info": "Viel Fläche, aber Energie F.", "Summary_Case": "Substanz-Deal.", "Summary_Pros": "Günstiger qm-Preis.", "Summary_Cons": "Energie F."
    },
    "Pinneberg-Thesdorf (2-Zi)": {
        "Adresse": "Thesdorf, Pinneberg", "qm": 59.0, "zimmer": 2.0, "bj": 1976, "Kaufpreis": 174000, "Nebenkosten_Quote": 0.085, "Miete_Start": 650, "Kosten_n_uml": 85, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02, "Renovierung": 1500, "Heizung_Puffer": 0, "Hausgeld_Gesamt": 245, "Status": "Offen", "Link": "", "Bild_URLs": [], "PDF_Path": "", "Energie_Info": "D/E", "Marktmiete_m2": 11.50, 
        "Archiviert": True, "Basis_Info": "Provisionsfrei.", "Summary_Case": "Solider Cashflow.", "Summary_Pros": "Provisionsfrei.", "Summary_Cons": "Beton-Charme."
    },
    "Stade (4-Zi Leerstand)": {
        "Adresse": "Köhnshöhe, Stade", "qm": 87.0, "zimmer": 3.5, "bj": 1972, "Kaufpreis": 239000, "Nebenkosten_Quote": 0.07, "Miete_Start": 950, "Kosten_n_uml": 105, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02, "Renovierung": 0, "Heizung_Puffer": 0, "Hausgeld_Gesamt": 286, "Status": "Leerstand", "Link": "", "Bild_URLs": [], "PDF_Path": "", "Energie_Info": "E", "Marktmiete_m2": 11.50, 
        "Archiviert": True, "Basis_Info": "Leerstand = Marktmiete sofort.", "Summary_Case": "Cashflow-Case.", "Summary_Pros": "Leerstand.", "Summary_Cons": "Lage Hochhaus."
    },
    "Stade (Altbau-Schnapper)": {
        "Adresse": "Zentrum, Stade", "qm": 67.0, "zimmer": 2.0, "bj": 1905, "Kaufpreis": 159500, "Nebenkosten_Quote": 0.1057, "Miete_Start": 575, "Kosten_n_uml": 69, "AfA_Satz": 0.025, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02, "Renovierung": 2000, "Heizung_Puffer": 5000, "Hausgeld_Gesamt": 170, "Status": "Vermietet", "Link": "", "Bild_URLs": [], "PDF_Path": "", "Energie_Info": "Gas-Etage", "Marktmiete_m2": 10, 
        "Archiviert": True, "Basis_Info": "Heizung muss neu.", "Summary_Case": "Günstiger Einkauf.", "Summary_Pros": "Hohe AfA.", "Summary_Cons": "Heizungstausch."
    }
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = data.copy()
            for k, v in DEFAULT_OBJEKTE.items():
                if k not in merged:
                    merged[k] = v
                else:
                    for sub_k, sub_v in v.items():
                        if sub_k not in merged[k]:
                            merged[k][sub_k] = sub_v
            return merged
    return DEFAULT_OBJEKTE

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

OBJEKTE = load_data()

# ==========================================
# 1. HELPER
# ==========================================
def clean_text(text):
    if not text: return ""
    return text.replace("€", "EUR").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")

def create_pdf_expose(obj_name, data, res):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.set_text_color(100)
            self.cell(0, 10, 'Investment Summary', 0, 1, 'R')
            self.ln(5)
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"{clean_text(obj_name)}", 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, f"Kaufpreis: {res['KP']:,.0f} EUR | Invest: {res['Invest']:,.0f} EUR", 0, 1)
    pdf.cell(0, 8, f"Rendite (Start): {res['Rendite']:.2f}% | EKR (10J): {res['CAGR']:.2f}%", 0, 1)
    pdf.ln(5)
    pdf.multi_cell(0, 6, f"Strategie: {clean_text(data.get('Summary_Case'))}")
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ==========================================
# 2. BERECHNUNGSKERN
# ==========================================
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio("Menü:", ["📊 Portfolio Übersicht", "🔍 Detail-Ansicht & Bearbeiten"])
st.sidebar.markdown("---")

st.sidebar.header("🏦 Global-Parameter")
global_zins = st.sidebar.number_input("Zins Bank (%)", 1.0, 6.0, 3.80, 0.1) / 100
global_tilgung = st.sidebar.number_input("Tilgung (%)", 0.0, 10.0, 1.50, 0.1) / 100
global_steuer = st.sidebar.number_input("Steuersatz (%)", 20.0, 50.0, 42.00, 0.5) / 100

def calculate_investment(obj_name, params):
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
    avg_cf_pre = sum([d["CF (vor Steuer)"] for d in data[:10]]) / 120
    
    return {
        "Name": obj_name, "Invest": invest, "KP": kp, "Rendite": (rent_start/kp)*100,
        "CAGR": cagr, "Avg_CF": avg_cf, "Avg_CF_Pre": avg_cf_pre,
        "Gewinn_10J": equity_10 - invest,
        "Detail": data, "Params": params,
        "Used_Zins": zins, "Archiviert": params.get("Archiviert", False),
        "Marktmiete": params.get("Marktmiete_m2", 0)
    }

# ==========================================
# 3. UI
# ==========================================
if page == "📊 Portfolio Übersicht":
    st.title("📊 Immobilien-Portfolio Dashboard")
    
    show_mode = st.radio("Ansicht:", ["Nur Aktive (Top-Liste)", "Alle (inkl. Archiv/Vergleich)"], horizontal=True)
    
    all_results = [calculate_investment(k, v) for k, v in OBJEKTE.items()]
    
    if "Nur Aktive" in show_mode:
        display_results = [r for r in all_results if not r["Archiviert"]]
    else:
        display_results = all_results
    
    tot_invest = sum(r["Invest"] for r in display_results)
    tot_cf = sum(r["Avg_CF"] for r in display_results)
    tot_gewinn = sum(r["Gewinn_10J"] for r in display_results)
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Gesamt-Invest (Auswahl)", f"{tot_invest:,.0f} €")
        c2.metric("Ø Cashflow (Auswahl)", f"{tot_cf:,.0f} €", delta_color="normal")
        c3.metric("Gewinn nach 10J (Gesamt)", f"{tot_gewinn:,.0f} €")
    
    if len(display_results) > 0:
        st.markdown("---")
        t1, t2 = st.tabs(["📈 Portfolio-Matrix", "💰 Vermögens-Maschine"])
        
        with t1:
            bubble_data = []
            for r in display_results:
                bubble_data.append({
                    "Objekt": r["Name"], "Kaufpreis": r["KP"], "Rendite (%)": round(r["Rendite"], 2),
                    "Invest (Größe)": r["Invest"], "Status": "Archiv" if r["Archiviert"] else "Aktiv"
                })
            fig = px.scatter(pd.DataFrame(bubble_data), x="Kaufpreis", y="Rendite (%)", size="Invest (Größe)", color="Status", 
                             hover_name="Objekt", size_max=60, color_discrete_map={"Aktiv": "green", "Archiv": "red"})
            st.plotly_chart(fig, use_container_width=True)
        
        with t2:
            years = list(range(START_JAHR, START_JAHR + 21))
            agg_equity = {y: 0 for y in years}
            agg_debt = {y: 0 for y in years}
            for r in display_results:
                for row in r["Detail"]:
                    agg_equity[row["Jahr"]] += (row["Immo-Wert"] - row["Restschuld"])
                    agg_debt[row["Jahr"]] += row["Restschuld"]
            
            df_wealth = pd.DataFrame({"Jahr": years, "Netto-Vermögen": list(agg_equity.values()), "Bank-Schulden": list(agg_debt.values())})
            
            fig_w = go.Figure()
            fig_w.add_trace(go.Scatter(x=df_wealth["Jahr"], y=df_wealth["Netto-Vermögen"], stackgroup='one', name='Netto-Vermögen', line=dict(color='#2E7D32', width=0)))
            fig_w.add_trace(go.Scatter(x=df_wealth["Jahr"], y=df_wealth["Bank-Schulden"], stackgroup='one', name='Bank-Schulden', line=dict(color='#C62828', width=0)))
            fig_w.update_layout(height=400, hovermode="x unified")
            st.plotly_chart(fig_w, use_container_width=True)

    st.subheader("📋 Objekt-Liste")
    df_data = []
    for r in display_results:
        status_icon = "❌ Archiv" if r["Archiviert"] else "✅ Aktiv"
        df_data.append({
            "Status": status_icon,
            "Objekt": r["Name"],
            "Kaufpreis": f"{r['KP']:,.0f} €",
            "Invest (EK)": f"{r['Invest']:,.0f} €",
            "Rendite": f"{r['Rendite']:.2f} %",
            "EKR (10J)": f"{r['CAGR']:.2f} %", # NEU: EKR
            "Ø CF (Vor St.)": f"{r['Avg_CF_Pre']:,.0f} €",
            "Ø CF (Nach St.)": f"{r['Avg_CF']:,.0f} €",
            "Gewinn (10J)": f"{r['Gewinn_10J']:,.0f} €"
        })
    st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

else:
    st.title("🔍 Detail-Ansicht & Bearbeiten")
    sorted_keys = sorted(OBJEKTE.keys(), key=lambda x: OBJEKTE[x].get("Archiviert", False))
    sel = st.selectbox("Objekt wählen:", sorted_keys)
    obj_data = OBJEKTE[sel]
    
    if obj_data.get("Archiviert"):
        st.warning("⚠️ Dieses Objekt liegt im Archiv (Abgelehnt/Vergleich).")

    # --- MIETE VS MARKTMIETE ---
    curr_miete_m2 = obj_data["Miete_Start"] / obj_data["qm"]
    markt_miete_m2 = obj_data.get("Marktmiete_m2", 0)
    miet_potenzial = ((markt_miete_m2 - curr_miete_m2) / curr_miete_m2) * 100 if curr_miete_m2 > 0 else 0

    st.markdown("### 📍 Objekt-Steckbrief & Miete")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**🏠 Adresse:** {obj_data.get('Adresse', 'n.v.')}")
        st.markdown(f"**📏 Größe:** {obj_data['qm']} m²")
    with c2:
        st.metric("Aktuelle Miete", f"{curr_miete_m2:.2f} €/m²", delta=f"{obj_data['Miete_Start']:.2f} € total")
    with c3:
        st.metric("Marktmiete (Potenzial)", f"{markt_miete_m2:.2f} €/m²", delta=f"{miet_potenzial:.1f} % Luft")

    # --- INVEST DETAIL ---
    kp_val = obj_data["Kaufpreis"]
    nk_quote = obj_data["Nebenkosten_Quote"]
    nk_wert = kp_val * nk_quote
    reno_wert = obj_data.get("Renovierung", 0)
    puffer_wert = obj_data.get("Heizung_Puffer", 0)
    invest_ek = nk_wert + reno_wert + puffer_wert
    
    st.markdown("---")
    st.markdown("### 💸 Investitions-Check")
    i1, i2, i3, i4 = st.columns(4)
    i1.metric("Kaufpreis", f"{kp_val:,.0f} €")
    i2.metric("Kaufnebenkosten", f"{nk_wert:,.0f} €", f"{nk_quote*100:.1f}%")
    i3.metric("Reno/Puffer", f"{reno_wert + puffer_wert:,.0f} €")
    i4.metric("Gesamt-Invest (EK)", f"{invest_ek:,.0f} €", delta="Muss vorhanden sein", delta_color="inverse")

    cl, cp = st.columns(2)
    if obj_data.get("Link"):
        cl.markdown(f"""<a href="{obj_data['Link']}" target="_blank" style="text-decoration: none;"><div style="background-color: #0052cc; color: white; padding: 8px; text-align: center; border-radius: 5px;">↗ Zum Inserat</div></a>""", unsafe_allow_html=True)
    
    # --- GALERIE FIX ---
    valid_imgs = [u for u in obj_data.get("Bild_URLs", []) if u and u.strip()]
    if valid_imgs:
        st.markdown("---")
        cols = st.columns(4)
        for i, u in enumerate(valid_imgs):
            try: cols[i % 4].image(u, use_container_width=True)
            except: cols[i % 4].caption("Bildfehler")

    st.markdown("---")
    st.header("📊 Kalkulation")
    
    # --- MIETSTEIGERUNG SLIDER ---
    with st.expander("⚙️ Parameter anpassen (Live)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        curr_z = obj_data.get("Zins_Indiv", global_zins)
        curr_a = obj_data.get("AfA_Satz", 0.02)
        curr_m = obj_data.get("Mietsteigerung", 0.02)
        curr_w = obj_data.get("Wertsteigerung_Immo", 0.02)

        new_z = c1.slider("Zins (%)", 1.0, 6.0, curr_z*100, 0.1, key=f"z_{sel}") / 100
        new_a = c2.slider("AfA (%)", 1.0, 5.0, curr_a*100, 0.1, key=f"a_{sel}") / 100
        
        if "Meckelfeld" in sel or "Elmshorn" in sel:
             st.caption("ℹ️ Fixe Mietstaffel/Treppe aktiv (Slider inaktiv)")
             new_m = curr_m 
        else:
             new_m = c3.slider("Mietsteigerung (%)", 0.0, 5.0, curr_m*100, 0.1, key=f"m_{sel}") / 100
             
        new_w = c4.slider("Wertsteigerung (%)", 0.0, 6.0, curr_w*100, 0.1, key=f"w_{sel}") / 100
        
        if (new_z != curr_z) or (new_a != curr_a) or (new_m != curr_m) or (new_w != curr_w):
            OBJEKTE[sel]["Zins_Indiv"] = new_z
            OBJEKTE[sel]["AfA_Satz"] = new_a
            OBJEKTE[sel]["Mietsteigerung"] = new_m
            OBJEKTE[sel]["Wertsteigerung_Immo"] = new_w
            save_data(OBJEKTE)
            st.rerun()

    res = calculate_investment(sel, OBJEKTE[sel])
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Ø CF (Nach Steuer)", f"{res['Avg_CF']:,.0f} €")
    k2.metric("EKR (10J)", f"{res['CAGR']:.2f} %")
    k3.metric("Gewinn (10J)", f"{res['Gewinn_10J']:,.0f} €")
    k4.metric("Miete 1. Jahr", f"{res['Detail'][0]['Miete (mtl.)']:,.2f} €")

    st.subheader("📋 10-Jahres-Plan")
    df_full = pd.DataFrame(res["Detail"])
    
    # --- TABLE FIX ---
    st.dataframe(
        df_full.head(10)[["Laufzeit", "Miete (mtl.)", "CF (vor Steuer)", "CF (nach Steuer)", "Restschuld"]],
        column_config={
            "Miete (mtl.)": st.column_config.NumberColumn(format="%.2f €"),
            "CF (vor Steuer)": st.column_config.NumberColumn(format="%.0f €"),
            "CF (nach Steuer)": st.column_config.NumberColumn(format="%.0f €"),
            "Restschuld": st.column_config.NumberColumn(format="%.0f €")
        },
        use_container_width=True, hide_index=True
    )
    
    with st.expander("🔮 Ausblick: Jahr 15 & 20"):
        c1, c2 = st.columns(2)
        d15 = res["Detail"][14]
        c1.write(f"**Jahr 15:** Restschuld {d15['Restschuld']:,.0f} € | Equity {d15['Equity']:,.0f} €")
        d20 = res["Detail"][19]
        c2.write(f"**Jahr 20:** Restschuld {d20['Restschuld']:,.0f} € | Equity {d20['Equity']:,.0f} €")

    st.markdown("---")
    st.header("⚙️ Daten ändern")
    with st.expander("📝 Stammdaten & Status bearbeiten", expanded=False):
        c1, c2 = st.columns(2)
        is_archived = c1.checkbox("❌ Archivieren (Abgelehnt)", value=obj_data.get("Archiviert", False))
        n_kp = c2.number_input("Kaufpreis", value=float(obj_data["Kaufpreis"]))
        n_link = st.text_input("Link", value=obj_data.get("Link", ""))
        n_imgs = st.text_area("Bilder (URLs)", value="\n".join(obj_data.get("Bild_URLs", [])))
        if st.button("💾 Speichern"):
            clean_imgs = [x.strip() for x in n_imgs.split("\n") if x.strip()]
            OBJEKTE[sel].update({"Archiviert": is_archived, "Kaufpreis": n_kp, "Link": n_link, "Bild_URLs": clean_imgs})
            save_data(OBJEKTE)
            st.success("Gespeichert!")
            st.rerun()

    with st.expander("📤 Uploads"):
        up = st.file_uploader("PDF Upload", type="pdf")
        if up:
            path = os.path.join(MEDIA_DIR, f"{sel}_expose.pdf")
            with open(path, "wb") as f: f.write(up.getbuffer())
            OBJEKTE[sel]["PDF_Path"] = path
            save_data(OBJEKTE)
            st.success("PDF gespeichert!")
            st.rerun()
    
    st.sidebar.download_button("📄 Exposé PDF", create_pdf_expose(sel, obj_data, res), f"Expose_{sel}.pdf")
