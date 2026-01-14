import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import tempfile
import json
import os
import shutil

# ==========================================
# 0. SICHERHEIT / LOGIN
# ==========================================
def check_password():
    try:
        correct_password = st.secrets["password"]
    except:
        # Fallback für lokales Testen ohne secrets.toml
        correct_password = "DeinGeheimesPasswort123"

    def password_entered():
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 Passwort:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 Passwort:", type="password", on_change=password_entered, key="password")
        st.error("Falsch.")
        return False
    else:
        return True

# ==========================================
# KONFIGURATION & SETUP
# ==========================================
st.set_page_config(page_title="Immo-Cockpit Pro", layout="wide", initial_sidebar_state="expanded")

if not check_password(): st.stop()

# CSS Hack für schönere Selectboxen
st.markdown("""<style>div[data-baseweb="select"] > div {border-color: #808495 !important; border-width: 1px !important;}</style>""", unsafe_allow_html=True)

START_JAHR = 2026
DATA_FILE = "portfolio_data_final.json"
MEDIA_DIR = "expose_files"

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# ==========================================
# 0. DATEN (DIE OBJEKTE)
# ==========================================
DEFAULT_OBJEKTE = {
    "Meckelfeld (Cashflow-King)": {
        "Adresse": "Am Bach, 21217 Seevetal", 
        "qm": 59, "zimmer": 2.0, "bj": 1965,
        "Kaufpreis": 180000, "Nebenkosten_Quote": 0.07, 
        "Renovierung": 0, "Heizung_Puffer": 2000, 
        "AfA_Satz": 0.03, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 632.50, "Hausgeld_Gesamt": 368, "Kosten_n_uml": 190, 
        "Marktmiete_m2": 13.45, "Energie_Info": "Gas (2022/23 neu!), 181 kWh (F)",
        "Status": "Vermietet (Treppenmiete)",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/etw-kapitalanlage-meckelfeld-eigenland-ohne-makler-/3295455732-196-2812", 
        "Bild_URLs": [], "PDF_Path": "",
        "Basis_Info": """Heizung NEU (2022). Miete steigt in Stufen (2027: 690€, 2029: 727€, 2032: 793€).""",
        "Summary_Case": """Substanz-Deal mit extremem Steuer-Hebel und neuer Heizung.""",
        "Summary_Pros": """- Provisionsfrei.\n- Fixe Mietsteigerung (Treppe).\n- Heizung nagelneu.""",
        "Summary_Cons": """- Energieklasse F (aber Heizung neu).\n- Boden/Bad optisch renovierungsbedürftig."""
    },
    "Stade (4-Zi Leerstand/Top-Zustand)": {
        "Adresse": "Köhnshöhe 10a, 21680 Stade", 
        "qm": 87.0, "zimmer": 3.5, "bj": 1972,
        "Kaufpreis": 239000, "Nebenkosten_Quote": 0.07, # Provisionsfrei (5% GrESt + 2% Notar)
        "Renovierung": 0, "Heizung_Puffer": 0, # Zustand ist top ("Einziehen & Wohlfühlen")
        "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 950, # SOLL-Miete bei Neuvermietung (ca. 10,90 €/qm)
        "Hausgeld_Gesamt": 286, "Kosten_n_uml": 105, # Sehr günstig!
        "Marktmiete_m2": 11.50, "Energie_Info": "Öl-Zentralheizung (Bj 1972), Klasse E",
        "Status": "Leerstehend (Sofort neu vermietbar)",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/einziehen-wohlfuehlen-moderne-4-zimmer-wohnung-in-toplage-/3282261577-196-2829", 
        "Bild_URLs": [], "PDF_Path": "",
        "Basis_Info": """Provisionsfrei! Leerstand = Chance auf sofortige Marktmiete. Hausgeld extrem niedrig.""",
        "Summary_Case": """Cashflow-Case durch Neuvermietung. Risiko: Ölheizung in Hochhaus-Siedlung.""",
        "Summary_Pros": """- Keine Maklergebühr.\n- Kein Sanierungsstau in der Wohnung.\n- Sofort ca. 11€/qm realisierbar.""",
        "Summary_Cons": """- Lage (Hochhaus-Charakter).\n- Ölheizung (Zukunfts-Risiko)."""
    },
    "Stade (Altbau-Schnapper)": {
        "Adresse": "Zentrumsnah, 21680 Stade", 
        "qm": 67.0, "zimmer": 2.0, "bj": 1905,
        "Kaufpreis": 159500, "Nebenkosten_Quote": 0.1057, # Mit Makler (ca. 3,57%)
        "Renovierung": 2000, "Heizung_Puffer": 5000, # Puffer für Austausch Gastherme (Bj 1990)
        "AfA_Satz": 0.025, # WICHTIG: 2,5% AfA weil Baujahr vor 1925!
        "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 575, # Ist-Miete (8,58 €/qm)
        "Hausgeld_Gesamt": 170, "Kosten_n_uml": 69, # Sehr günstig
        "Marktmiete_m2": 10.00, "Energie_Info": "Gas-Etage (Bj 1990 - Austausch fällig!)",
        "Status": "Vermietet (Steigerungspotenzial)",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/vermietete-altbauwohnung-mit-balkon-in-zentraler-lage-/3279", 
        "Bild_URLs": [], "PDF_Path": "",
        "Basis_Info": """Heizung (Gastherme 1990) muss gemacht werden -> Puffer eingerechnet. Kleine WEG.""",
        "Summary_Case": """Günstiger Einkauf (2.380€/qm). Cashflow fast am Ziel (-225€).""",
        "Summary_Pros": """- Hohe AfA (2,5%).\n- Extrem niedriges Hausgeld.\n- Preis verhandelbar wegen Heizung.""",
        "Summary_Cons": """- Maklerprovision fällig.\n- Heizungstausch steht an."""
    },
    "Neu Wulmstorf (Neubau-Anker)": {
        "Adresse": "Hauptstraße 43, 21629 Neu Wulmstorf", 
        "qm": 65.79, "zimmer": 2.0, "bj": 2016,
        "Kaufpreis": 249000, "Nebenkosten_Quote": 0.07, 
        "Renovierung": 0, "Heizung_Puffer": 0, 
        "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 920, 
        "Hausgeld_Gesamt": 260, "Kosten_n_uml": 60, 
        "Marktmiete_m2": 14.50, "Energie_Info": "Gas + Solar (Bj 2016), Klasse B (est.)",
        "Status": "Frei ab 02/2026 (Provisionsfrei)",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/moderne-2-zimmer-wohnung-inkl-aussenstellplatz-in-begehrter-lage/3296695424-196-2807", 
        "Bild_URLs": [
            "https://img.kleinanzeigen.de/api/v1/prod-ads/images/b8/b8d9237e-390c-4f6d-9420-a262fb63e7c4?rule=$_59.AUTO",
            "https://img.kleinanzeigen.de/api/v1/prod-ads/images/44/44e6c91e-dcb6-4d18-b759-ec288cf895fc?rule=$_59.AUTO",
            "https://img.kleinanzeigen.de/api/v1/prod-ads/images/c2/c2c20f6e-904f-43df-b3f6-815ae965458a?rule=$_59.AUTO",
            "https://img.kleinanzeigen.de/api/v1/prod-ads/images/9d/9d538360-5d4e-4cac-92c3-f672fc0d3a5e?rule=$_59.AUTO"
        ], "PDF_Path": "",
        "Basis_Info": """Baujahr 2016 bestätigt. 14 Einheiten. Frei ab Feb 2026. LAGE: Direkt an B73 (laut!).""",
        "Summary_Case": """'Sorglos-Paket'. Wertsicherung durch moderne Substanz & günstigen Einkauf.""",
        "Summary_Pros": """- PROVISIONSFREI (Invest < 18k).\n- Baujahr 2016 (Technik top, Gas+Solar).\n- Frei lieferbar (sofort 14€/qm).""",
        "Summary_Cons": """- LAGE AN B73 (Lärm/Emissionen).\n- Höchster Kaufpreis (249k).\n- Rendite ca. 4,4%."""
    },
    "Elmshorn (Terrasse & Staffel)": {
        "Adresse": "Johannesstr. 24-28, 25335 Elmshorn", 
        "qm": 75.67, "zimmer": 2.0, "bj": 1994,
        "Kaufpreis": 229000, "Nebenkosten_Quote": 0.1207, 
        "Renovierung": 0, "Heizung_Puffer": 1000, 
        "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 665, 
        "Hausgeld_Gesamt": 370, "Kosten_n_uml": 165, 
        "Marktmiete_m2": 11.00, "Energie_Info": "104,9 kWh (C), Gas Bj. 2012",
        "Status": "Vermietet (Staffel 2026/27)",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/moderne-2-zimmer-wohnung-inkl-aussenstellplatz-in-begehrter-lage/3296695424-196-2807", 
        "Bild_URLs": [], "PDF_Path": "",
        "Basis_Info": """Staffelmiete: 2026 -> 765€, 2027 -> 815€. Heizung lt. Ausweis 2012 (Klasse C).""",
        "Summary_Case": """Solides Investment mit eingebautem Rendite-Turbo (Staffel) und guter Substanz.""",
        "Summary_Pros": """- Heizung Bj. 2012 (Energie C).\n- Miete steigt fix auf 815€ (2027).\n- Terrasse & TG.""",
        "Summary_Cons": """- Hohes Hausgeld (Rücklagen).\n- Nachtrag zur Miete noch einzuholen."""
    },
    "Harburg (Maisonette/Lifestyle)": {
        "Adresse": "Marienstr. 52, 21073 Hamburg", 
        "qm": 71, "zimmer": 2.0, "bj": 1954,
        "Kaufpreis": 230000, "Nebenkosten_Quote": 0.1107, 
        "Renovierung": 0, "Heizung_Puffer": 5000, 
        "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 720, "Hausgeld_Gesamt": 204, "Kosten_n_uml": 84, 
        "Marktmiete_m2": 12.00, "Energie_Info": "116 kWh (D), Gas-Etage",
        "Status": "Vermietet (Mieterwechsel?)",
        "Link": "", 
        "Bild_URLs": [], "PDF_Path": "",
        "Basis_Info": """Liebhaber-Objekt mit Galerie. Negativer Cashflow, aber Potenzial.""",
        "Summary_Case": """Trophy Asset / Spekulation.""",
        "Summary_Pros": """- Einzigartiger Schnitt (Galerie).\n- Lage TUHH.""",
        "Summary_Cons": """- Negativer Cashflow (-400€).\n- WEG-Probleme (Wasser/Lärm)."""
    }
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = {k: v for k, v in data.items() if k in DEFAULT_OBJEKTE}
            for k, v in DEFAULT_OBJEKTE.items():
                if k not in merged:
                    merged[k] = v
            return merged
    return DEFAULT_OBJEKTE

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

OBJEKTE = load_data()

# ==========================================
# 1. HELPER & PDF
# ==========================================
def clean_text(text):
    if not text: return ""
    replacements = {"€": "EUR", "ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

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
    pdf.ln(2)
    pdf.multi_cell(0, 6, f"Pros: {clean_text(data.get('Summary_Pros'))}")
    pdf.ln(2)
    pdf.multi_cell(0, 6, f"Risiken: {clean_text(data.get('Summary_Cons'))}")
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ==========================================
# 2. BERECHNUNGSKERN (MIT SPEZIAL-MIETEN)
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
    
    # Check Special Logic Flags
    is_elmshorn_staffel = "Elmshorn" in obj_name and "Terrasse" in obj_name
    is_meckelfeld_treppe = "Meckelfeld" in obj_name
    
    data = []
    restschuld = loan
    immo_wert = kp
    
    # 20 Jahre Berechnung
    for i in range(21): # 0 bis 20
        jahr = START_JAHR + i
        
        # --- MIET-LOGIK ---
        if is_elmshorn_staffel:
            if jahr == 2026: rent_yr = 9180 
            elif jahr == 2027: rent_yr = 9780 
            elif jahr > 2027: rent_yr = 9780 * (1 + miet_st)**(i - 2) 
            else: rent_yr = rent_start
            
        elif is_meckelfeld_treppe:
            # Manuelle Treppe gemäß User & Frau Lorenz
            # 2026: 632.50
            # 2027: 690.00 (Zugesichert)
            # 2029: 727.38 (Lorenz Stufe 1)
            # 2032: 793.50 (Lorenz Stufe 2, unter Annahme 3J Sperrfrist)
            
            rent_monthly = 0
            if jahr < 2027:
                rent_monthly = params["Miete_Start"] # 632.50
            elif jahr < 2029:
                rent_monthly = 690.00
            elif jahr < 2032:
                rent_monthly = 727.38
            else:
                # Ab 2032 Stufe 2, danach normale Steigerung
                base_2032 = 793.50
                years_since_2032 = jahr - 2032
                rent_monthly = base_2032 * (1 + miet_st)**years_since_2032
            
            rent_yr = rent_monthly * 12
            
        else:
            # Standard
            rent_yr = rent_start * (1 + miet_st)**i
            
        immo_wert *= (1 + wert_st)
        zinsen = restschuld * zins
        tilgung = rate_pa - zinsen
        costs = params["Kosten_n_uml"] * 12
        
        # Cashflow VOR Steuer
        cf_pre_tax = rent_yr - rate_pa - costs

        # Steuer-Effekt
        tax_base = rent_yr - zinsen - (kp*0.8*afa_rate) - costs
        tax = tax_base * global_steuer * -1
        
        # Cashflow NACH Steuer
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

    # KPIs Jahr 10
    res_10 = data[9] 
    equity_10 = res_10["Equity"] + sum([d["CF (nach Steuer)"] for d in data[:10]])
    cagr = ((equity_10 / invest)**(0.1) - 1) * 100 if invest > 0 else 0
    avg_cf = sum([d["CF (nach Steuer)"] for d in data[:10]]) / 120
    
    return {
        "Name": obj_name, "Invest": invest, "KP": kp, "Rendite": (rent_start/kp)*100,
        "CAGR": cagr, "Avg_CF": avg_cf, "Gewinn_10J": equity_10 - invest,
        "Detail": data, "Params": params,
        "Used_Zins": zins, "Used_AfA": afa_rate
    }

# ==========================================
# 3. UI
# ==========================================
if page == "📊 Portfolio Übersicht":
    st.title("📊 Immobilien-Portfolio Dashboard")
    results = [calculate_investment(k, v) for k, v in OBJEKTE.items()]
    
    tot_invest = sum(r["Invest"] for r in results)
    tot_cf = sum(r["Avg_CF"] for r in results)
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Gesamt-Invest (EK)", f"{tot_invest:,.0f} €")
        c2.metric("Ø Cashflow Portfolio (mtl.)", f"{tot_cf:,.0f} €", delta_color="normal")
        c3.metric("Anzahl Objekte", len(results))
    
    df = pd.DataFrame([{
        "Objekt": r["Name"],
        "Kaufpreis": f"{r['KP']:,.0f} €",
        "Invest (EK)": f"{r['Invest']:,.0f} €",
        "Rendite (Start)": f"{r['Rendite']:.2f} %",
        "EKR (10J)": f"{r['CAGR']:.2f} %",
        "Ø CF (mtl. 10J)": f"{r['Avg_CF']:,.0f} €",
        "Gewinn (10J)": f"{r['Gewinn_10J']:,.0f} €"
    } for r in results])
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.title("🔍 Detail-Ansicht & Bearbeiten")
    sel = st.selectbox("Objekt wählen:", list(OBJEKTE.keys()))
    obj_data = OBJEKTE[sel]
    
    # ----------------------------------------------------
    # STECKBRIEF (INKL. INVEST-BERECHNUNG)
    # ----------------------------------------------------
    st.markdown("### 📍 Objekt-Steckbrief")
    
    # KAUFPREIS & NK BERECHNUNG FÜR HERLEITUNG
    kp_val = obj_data["Kaufpreis"]
    nk_quote = obj_data["Nebenkosten_Quote"]
    
    # Logik für NK-Herleitung basierend auf Bundesland-Schätzung
    addr = obj_data.get("Adresse", "").lower()
    if "hamburg" in addr:
        grest_proz = 5.5
    elif "elmshorn" in addr: # Schleswig-Holstein
        grest_proz = 6.5
    else: # Default Niedersachsen (Meckelfeld/Neu Wulmstorf/Stade)
        grest_proz = 5.0
        
    notar_proz = 2.0
    makler_proz = (nk_quote * 100) - grest_proz - notar_proz
    if makler_proz < 0: makler_proz = 0 # Fallback
    
    nk_wert = kp_val * nk_quote
    reno_wert = obj_data.get("Renovierung", 0)
    puffer_wert = obj_data.get("Heizung_Puffer", 0)
    invest_ek = nk_wert + reno_wert + puffer_wert

    with st.container(border=True):
        c_prof1, c_prof2 = st.columns(2)
        with c_prof1:
            st.markdown(f"**🏠 Adresse:** {obj_data.get('Adresse', 'n.v.')}")
            st.markdown(f"**📏 Größe:** {obj_data['qm']} m² | {obj_data['zimmer']} Zi.")
            st.markdown(f"**📅 Baujahr:** {obj_data['bj']}")
            st.markdown(f"**⚡ Energie:** {obj_data.get('Energie_Info', 'n.v.')}")
        with c_prof2:
            st.markdown(f"**💶 Hausgeld:** {obj_data.get('Hausgeld_Gesamt', 0)} €")
            st.markdown(f"**🔑 Status:** {obj_data.get('Status', 'n.v.')}")
        
        st.markdown("---")
        # INVEST-BLOCK (EK-BEDARF) - AUF WUNSCH BEIBEHALTEN
        c_inv1, c_inv2 = st.columns([1, 2])
        with c_inv1:
            st.metric("💸 Invest (Eigenkapital)", f"{invest_ek:,.0f} €", help="Summe aus Kaufnebenkosten, Renovierung und Puffer")
        with c_inv2:
            with st.expander("ℹ️ Herleitung (100% Finanzierung) ansehen"):
                st.markdown(f"""
                **Kaufpreis:** {kp_val:,.0f} € (wird zu 100% finanziert)  
                
                **Cash-Bedarf (EK):**
                * Grunderwerbsteuer ({grest_proz}%): {kp_val*(grest_proz/100):,.0f} €
                * Notar & Gericht (ca. {notar_proz}%): {kp_val*(notar_proz/100):,.0f} €
                * Makler ({makler_proz:.2f}%): {kp_val*(makler_proz/100):,.0f} €
                * + Renovierung: {reno_wert:,.0f} €
                * + Puffer: {puffer_wert:,.0f} €
                
                **= {invest_ek:,.0f} €**
                """)

    if obj_data.get("Basis_Info"):
        st.info(f"ℹ️ **Info:** {obj_data['Basis_Info']}")

    # Links & PDF
    c_link, c_pdf = st.columns(2)
    url = obj_data.get("Link", "")
    if url:
        c_link.markdown(f"""<a href="{url}" target="_blank" style="text-decoration: none;"><div style="background-color: #0052cc; padding: 8px 12px; border-radius: 4px; text-align: center; color: white;">↗ Zum Inserat</div></a>""", unsafe_allow_html=True)

    pdf_path = obj_data.get("PDF_Path")
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            c_pdf.download_button("📄 Exposé PDF", f, file_name=os.path.basename(pdf_path), use_container_width=True)
    else:
        c_pdf.warning("Kein PDF hinterlegt")

    img_urls = obj_data.get("Bild_URLs", [])
    if img_urls:
        st.markdown("---")
        st.subheader("📸 Galerie")
        cols = st.columns(4)
        for i, u in enumerate(img_urls):
            with cols[i % 4]:
                st.image(u, use_container_width=True)

    # ----------------------------------------------------
    # LIVE-CALC & JAHRESPLÄNE
    # ----------------------------------------------------
    st.markdown("---")
    st.header("📊 Kalkulation & Szenarien")
    
    with st.expander("⚙️ Parameter anpassen (Live)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        curr_z = obj_data.get("Zins_Indiv", global_zins)
        curr_a = obj_data.get("AfA_Satz", 0.02)
        curr_m = obj_data.get("Mietsteigerung", 0.02)
        curr_w = obj_data.get("Wertsteigerung_Immo", 0.02)

        new_z = c1.slider("Zins (%)", 1.0, 6.0, curr_z*100, 0.1, key=f"z_{sel}") / 100
        new_a = c2.slider("AfA (%)", 1.0, 5.0, curr_a*100, 0.1, key=f"a_{sel}") / 100
        
        # Hinweis bei Meckelfeld, dass Mietsteigerung hier inaktiv ist
        if "Meckelfeld" in sel:
            st.caption("ℹ️ Meckelfeld nutzt feste Stufen (2027/29/32)")
            new_m = curr_m # Keine Änderung
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
    
    # 1. TOP KPIs
    k1, k2, k3, k4 = st.columns(4)
    qm = res["Params"]["qm"]
    miete_sqm = (res["Detail"][0]["Miete (mtl.)"]) / qm if qm > 0 else 0
    markt_sqm = res["Params"].get("Marktmiete_m2", 0)
    
    k1.metric("Ø Monatl. Cashflow (10 Jahre)", f"{res['Avg_CF']:,.0f} €")
    k2.metric("EKR (Eigenkapitalrendite 10J)", f"{res['CAGR']:.2f} %")
    k3.metric("Miete/m² (Start)", f"{miete_sqm:.2f} €", f"Ziel: {markt_sqm:.2f} €")
    k4.metric("Gewinn nach 10J", f"{res['Gewinn_10J']:,.0f} €")

    # 2. HAUPT-TABELLE (10 JAHRE)
    st.subheader("📋 10-Jahres-Plan (Detail)")
    df_full = pd.DataFrame(res["Detail"])
    
    # Nur die ersten 10 Jahre anzeigen + relevante Spalten
    df_10 = df_full.head(10)[["Laufzeit", "Miete (mtl.)", "CF (vor Steuer)", "CF (nach Steuer)", "Restschuld", "Immo-Wert"]]
    
    st.dataframe(
        df_10.style.format({
            "Miete (mtl.)": "{:,.2f} €",
            "CF (vor Steuer)": "{:,.0f} €",
            "CF (nach Steuer)": "{:,.0f} €",
            "Restschuld": "{:,.0f} €",
            "Immo-Wert": "{:,.0f} €"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    # 3. AUSBLICK
    with st.expander("🔮 Ausblick: Jahr 15 & Jahr 20 ansehen"):
        c_15, c_20 = st.columns(2)
        
        with c_15:
            st.markdown("#### Jahr 15")
            d15 = res["Detail"][14]
            st.write(f"**Miete:** {d15['Miete (mtl.)']:,.2f} €")
            st.write(f"**Restschuld:** {d15['Restschuld']:,.0f} €")
            st.write(f"**Equity:** {d15['Equity']:,.0f} €")
            
        with c_20:
            st.markdown("#### Jahr 20")
            d20 = res["Detail"][19]
            st.write(f"**Miete:** {d20['Miete (mtl.)']:,.2f} €")
            st.write(f"**Restschuld:** {d20['Restschuld']:,.0f} €")
            st.write(f"**Equity:** {d20['Equity']:,.0f} €")

    # ----------------------------------------------------
    # EDIT & UPLOAD AREA
    # ----------------------------------------------------
    st.markdown("---")
    st.header("⚙️ Daten ändern & Uploads")
    
    with st.expander("📝 Stammdaten, Link & Texte bearbeiten", expanded=False):
        c_e1, c_e2, c_e3 = st.columns(3)
        n_kp = c_e1.number_input("Kaufpreis", value=float(obj_data["Kaufpreis"]))
        n_miete = c_e2.number_input("Start-Miete", value=float(obj_data["Miete_Start"]))
        n_qm = c_e3.number_input("Wohnfläche", value=float(obj_data["qm"]))
        
        n_link = st.text_input("Link zum Inserat", value=obj_data.get("Link", ""))
        
        n_case = st.text_area("Investment Case", value=obj_data.get("Summary_Case", ""))
        n_pros = st.text_area("Pros", value=obj_data.get("Summary_Pros", ""))
        n_cons = st.text_area("Cons", value=obj_data.get("Summary_Cons", ""))
        
        n_imgs = st.text_area("Bild-URLs (eine pro Zeile)", value="\n".join(obj_data.get("Bild_URLs", [])))
        
        if st.button("💾 Änderungen Speichern"):
            OBJEKTE[sel].update({
                "Kaufpreis": n_kp, "Miete_Start": n_miete, "qm": n_qm, "Link": n_link,
                "Summary_Case": n_case, "Summary_Pros": n_pros, "Summary_Cons": n_cons,
                "Bild_URLs": [x.strip() for x in n_imgs.split("\n") if x.strip()]
            })
            save_data(OBJEKTE)
            st.success("Gespeichert!")
            st.rerun()

    with st.expander("📤 Dateien hochladen (PDF & Bild)", expanded=False):
        uploaded_pdf = st.file_uploader("Exposé PDF hochladen", type="pdf")
        if uploaded_pdf:
            safe_name = "".join([c for c in sel if c.isalnum()]) + ".pdf"
            save_path = os.path.join(MEDIA_DIR, safe_name)
            with open(save_path, "wb") as f: f.write(uploaded_pdf.getbuffer())
            OBJEKTE[sel]["PDF_Path"] = save_path
            save_data(OBJEKTE)
            st.success("PDF gespeichert!")
            st.rerun()
            
    st.sidebar.download_button("📄 Exposé PDF erstellen", create_pdf_expose(sel, obj_data, res), f"Expose_{sel}.pdf")
