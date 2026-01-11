import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import tempfile
import json
import os
import shutil

# ==========================================
# 0. SICHERHEIT / LOGIN (ROBUST)
# ==========================================
def check_password():
    """Returns `True` if the user had the correct password."""
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
        st.text_input(
            "🔒 Bitte Passwort eingeben, um das Portfolio zu laden:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        try:
            st.secrets["password"]
        except:
            st.caption(f" (Lokaler Test-Modus aktiv. Passwort: {correct_password})")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "🔒 Bitte Passwort eingeben, um das Portfolio zu laden:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Passwort falsch.")
        return False
    else:
        return True

# ==========================================
# KONFIGURATION & SETUP
# ==========================================
st.set_page_config(page_title="Immo-Portfolio Cockpit Pro", layout="wide", initial_sidebar_state="expanded")

if not check_password():
    st.stop()

st.markdown("""
<style>
    div[data-baseweb="select"] > div {
        border-color: #808495 !important;
        border-width: 1px !important;
    }
</style>
""", unsafe_allow_html=True)

START_JAHR = 2026
DATA_FILE = "portfolio_data_final.json"
PDF_DIR = "expose_files"

if not os.path.exists(PDF_DIR):
    os.makedirs(PDF_DIR)

# ==========================================
# 0. DATEN-MANAGEMENT
# ==========================================
DEFAULT_OBJEKTE = {
    "Elmshorn (Substanz & Hebel)": {
        "Adresse": "Innenstadtbereich, 25335 Elmshorn",
        "qm": 76, "zimmer": 2.0, "bj": 1960,
        "Kaufpreis": 200000, "Nebenkosten_Quote": 0.085,
        "Renovierung": 0, "Heizung_Puffer": 5000, "AfA_Satz": 0.02,
        "Miete_Start": 800, "Hausgeld_Gesamt": 350, "Kosten_n_uml": 120,
        "Wertsteigerung_Immo": 0.025, "Mietsteigerung": 0.02, "Marktmiete_m2": 11.00,
        "Energie_Info": "Verbrauchsausweis, Gas, Klasse E/F",
        "Status": "Leerstand (Sofortige Neuvermietung geplant)",
        "Lage_Beschreibung": """Zentrale Lage in Elmshorn (Mittelzentrum). Bahnhof fußläufig erreichbar.""",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/2-zimmerwohnung-in-innenatadtlage/3281010495-196-877",
        "Bild_URLs": [], "PDF_Path": "", 
        "Basis_Info": """Kalkulation mit ZIEL-Miete (10,50€/qm). 5.000€ Puffer für Instandhaltung.""",
        "Summary_Case": """Value-Add / Hebel-Strategie. Ankauf unter Marktwert.""",
        "Summary_Pros": """- Extrem günstiger Einkaufspreis.\n- Sofortiges Wertsteigerungspotenzial.""",
        "Summary_Cons": """- Baujahr 1960: Mittelfristiges Sanierungsrisiko."""
    },
    "Meckelfeld (Eigenland)": {
        "Adresse": "Am Bach (Sackgasse), 21217 Seevetal (Meckelfeld)", 
        "qm": 59, "zimmer": 2.0, "bj": 1965,
        "Kaufpreis": 180000, 
        "Nebenkosten_Quote": 0.07, 
        "Renovierung": 0, "Heizung_Puffer": 2000, 
        "AfA_Satz": 0.03, 
        "Miete_Start": 632.50, 
        "Hausgeld_Gesamt": 368, 
        "Kosten_n_uml": 190, 
        "Wertsteigerung_Immo": 0.02, 
        "Mietsteigerung": 0.02, 
        "Marktmiete_m2": 11.70,
        "Energie_Info": "Verbrauchsausweis 181 kWh (F), Gas",
        "Status": "Vermietet (Fixe Erhöhung 2027)",
        "Lage_Beschreibung": """Ruhige Sackgassenlage in Meckelfeld.""",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/etw-kapitalanlage-meckelfeld-eigenland-ohne-makler-/3295455732-196-2812", 
        "Bild_URLs": [], "PDF_Path": "", 
        "Basis_Info": """Miete steigt fix auf 690€ ab 07/2027. NK-Quote nur 7% (privat).""",
        "Summary_Case": """Substanz-Deal mit extremem Steuer-Hebel.""",
        "Summary_Pros": """- Provisionsfrei.\n- Fixe Mietsteigerung.\n- Hohe Rücklagen.""",
        "Summary_Cons": """- Energieklasse F.\n- Müllplatz-Umlage möglich."""
    },
    "Harburg (Maisonette / Loft)": {
        "Adresse": "Marienstr. 52, 21073 Hamburg (Harburg-Zentrum)", 
        "qm": 71, 
        "zimmer": 2.0, "bj": 1954,
        "Kaufpreis": 230000, 
        "Nebenkosten_Quote": 0.1107, 
        "Renovierung": 0, 
        "Heizung_Puffer": 5000, 
        "AfA_Satz": 0.02, 
        "Miete_Start": 720, 
        "Hausgeld_Gesamt": 204, 
        "Kosten_n_uml": 84, 
        "Wertsteigerung_Immo": 0.02, 
        "Mietsteigerung": 0.02, 
        "Marktmiete_m2": 12.00,
        "Energie_Info": "Bedarfsausweis 116 kWh (D), Gas-Etagenhzg.",
        "Status": "Vermietet (Mieter sucht neue Whg)",
        "Lage_Beschreibung": """Zentrale Lage in Harburg, Nähe TUHH.""",
        "Link": "", 
        "Bild_URLs": [], "PDF_Path": "", 
        "Basis_Info": """Liebhaber-Objekt mit Galerie. Negativer Cashflow, aber Potenzial.""",
        "Summary_Case": """Lifestyle-Investment ('Trophy Asset').""",
        "Summary_Pros": """- Einzigartiger Schnitt.\n- Vermietung an Studenten/Dozenten.""",
        "Summary_Cons": """- Negativer Cashflow.\n- WEG-Themen & Wasserschaden."""
    }
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data: return DEFAULT_OBJEKTE
            for key, val in DEFAULT_OBJEKTE.items():
                if key not in data:
                    data[key] = val
                for field, default_val in val.items():
                    if field not in data[key]:
                        data[key][field] = default_val
            keys_to_remove = [k for k in data.keys() if k not in DEFAULT_OBJEKTE]
            for k in keys_to_remove: 
                del data[k]
            return data
    else:
        save_data(DEFAULT_OBJEKTE)
        return DEFAULT_OBJEKTE

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

OBJEKTE = load_data()

# ==========================================
# 1. HELPER & PDF
# ==========================================
def generate_auto_texts(data, res):
    case_txt = ""
    if data['bj'] >= 2010: case_txt = "Neubau-Strategie: Fokus auf Wertsicherung."
    elif res['Brutto_Rendite'] > 5.5: case_txt = "Cashflow-Strategie: Hoher Ertrag."
    else: case_txt = "Value-Add Strategie: Potenzial heben."
    
    pros_txt = f"- Mietrendite: {res['Brutto_Rendite']:.2f}%.\n- Lage: {data.get('Adresse', 'k.A.')}"
    cons_txt = "- Älteres Baujahr" if data['bj'] < 1980 else "- Cashflow beachten"
    return case_txt, pros_txt, cons_txt

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
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, 'Bank-Expose & Investment Summary', 0, 1, 'R')
            self.ln(5)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f'Seite {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 10, f"Investment-Profil: {clean_text(obj_name)}", 0, 1, 'L')
    pdf.ln(5)

    pdf.set_fill_color(230, 230, 230)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, "Objekt-Stammdaten", 0, 1, 'L', 1)
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 10)
    col_w = 95
    line_h = 6
    
    pdf.cell(col_w, line_h, f"Adresse: {clean_text(data.get('Adresse', ''))}", 0)
    pdf.cell(col_w, line_h, f"Wohnflaeche: {data['qm']} qm / {data['zimmer']} Zimmer", 0, 1)
    pdf.cell(col_w, line_h, f"Baujahr: {data['bj']}", 0)
    pdf.cell(col_w, line_h, f"Energie: {clean_text(data.get('Energie_Info', ''))}", 0, 1)
    pdf.cell(col_w, line_h, f"Status: {clean_text(data.get('Status', ''))}", 0)
    pdf.cell(col_w, line_h, f"Hausgeld (Gesamt): {data.get('Hausgeld_Gesamt', 0)} EUR", 0, 1)
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, "Finanzierung & Rendite", 0, 1, 'L', 1)
    pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    
    pdf.cell(col_w, line_h, f"Kaufpreis: {res['KP']:,.0f} EUR", 0)
    pdf.cell(col_w, line_h, f"Gesamt-Invest: {res['Invest (EK)']:,.0f} EUR", 0, 1)
    pdf.cell(col_w, line_h, f"Miete (Soll p.a.): {res['Start_Values']['Miete']:,.0f} EUR", 0)
    pdf.cell(col_w, line_h, f"Mietrendite: {res['Brutto_Rendite']:.2f} %", 0, 1)
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, "Strategie & Potenzial", 0, 1, 'L', 1)
    pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, f"Case: {clean_text(data.get('Summary_Case', ''))}")
    pdf.ln(2)
    pdf.multi_cell(0, 6, f"Staerken: {clean_text(data.get('Summary_Pros', ''))}")
    pdf.ln(2)
    pdf.multi_cell(0, 6, f"Risiken & Management: {clean_text(data.get('Summary_Cons', ''))}")
    
    if data.get("Lage_Beschreibung"):
        pdf.ln(2)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "Lage & Umgebung:", 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 6, f"{clean_text(data.get('Lage_Beschreibung'))}")

    return pdf.output(dest='S').encode('latin-1', 'replace')

# ==========================================
# 3. RECHENKERN
# ==========================================
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio("Menü:", ["📊 Portfolio Übersicht", "🔍 Detail-Ansicht & Bearbeiten"])
st.sidebar.markdown("---")

if st.sidebar.button("⚠️ Daten Reset (Auf Standard)"):
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
        if os.path.exists(PDF_DIR): shutil.rmtree(PDF_DIR)
    st.rerun()

st.sidebar.header("🏦 Finanzierung (Global)")
global_zins = st.sidebar.number_input("Zins Bank (%)", 1.0, 6.0, 3.80, 0.1) / 100
global_tilgung = st.sidebar.number_input("Tilgung (%)", 0.0, 10.0, 1.50, 0.1) / 100
global_steuer = st.sidebar.number_input("Steuersatz (%)", 20.0, 50.0, 42.00, 0.5) / 100

def calculate_investment(obj_name, params, zins_indiv=None, mietsteig_indiv=None, wertsteig_indiv=None, afa_indiv=None):
    kp = params["Kaufpreis"]
    zins = zins_indiv if zins_indiv is not None else global_zins
    miet_st = mietsteig_indiv if mietsteig_indiv is not None else params["Mietsteigerung"]
    wert_st = wertsteig_indiv if wertsteig_indiv is not None else params["Wertsteigerung_Immo"]
    
    nk_betrag = kp * params["Nebenkosten_Quote"]
    renovierung = params.get("Renovierung", 0) 
    heizung_puffer = params.get("Heizung_Puffer", 0) 
    ek_invest = nk_betrag + renovierung + heizung_puffer
    
    darlehen = kp
    rate_jahr = darlehen * (zins + global_tilgung)
    
    used_afa_rate = afa_indiv if afa_indiv is not None else params["AfA_Satz"]
    afa_basis = kp * 0.80 
    afa_jahr = afa_basis * used_afa_rate
    
    detail_data = [] 
    restschuld = darlehen
    immo_wert = kp
    cum_cf = 0
    
    for i in range(20): 
        jahr_zahl = START_JAHR + i
        miete_jahr = (params["Miete_Start"] * (1 + miet_st)**i) * 12
        immo_wert_alt = immo_wert
        immo_wert = immo_wert * (1 + wert_st)
        wertzuwachs = immo_wert - immo_wert_alt
        
        zinsen = restschuld * zins
        tilgung_betrag = rate_jahr - zinsen
        if tilgung_betrag > restschuld: tilgung_betrag = restschuld 
        
        kosten_jahr = params["Kosten_n_uml"] * 12
        
        steuer_basis = miete_jahr - zinsen - afa_jahr - kosten_jahr
        steuer_effekt = steuer_basis * global_steuer * -1 
        
        cf_pre_tax = miete_jahr - rate_jahr - kosten_jahr
        cf_post_tax = cf_pre_tax + steuer_effekt
        
        cum_cf += cf_post_tax
        restschuld -= tilgung_betrag
        
        detail_data.append({
            "Jahr": jahr_zahl,
            "Miete": miete_jahr,
            "Bewirtschaftung": -kosten_jahr,
            "Zinsen": -zinsen,
            "Tilgung": -tilgung_betrag,
            "CF_Vor_Steuer": cf_pre_tax,
            "Steuer_Effekt": steuer_effekt,
            "CF_Nach_Steuer": cf_post_tax,
            "Restschuld": restschuld,
            "Immo_Wert": immo_wert,
            "Wertzuwachs": wertzuwachs,
            "Cum_CF": cum_cf 
        })

    # KPIs nach 10 Jahren
    idx_10 = 9
    end_equity_10 = (detail_data[idx_10]['Immo_Wert'] - detail_data[idx_10]['Restschuld']) + detail_data[idx_10]['Cum_CF']
    cagr_10 = ((end_equity_10 / ek_invest) ** (1/10) - 1) * 100 if end_equity_10 > 0 and ek_invest > 0 else 0
    
    # Durchschnittlicher monatlicher Cashflow (nach Steuer) über 120 Monate (10 Jahre)
    sum_cf_10y = sum([d['CF_Nach_Steuer'] for d in detail_data[:10]])
    avg_cf_10y_mtl = sum_cf_10y / 120

    start_values = {
        "Miete": params["Miete_Start"]*12, "Bewirtschaft": params["Kosten_n_uml"]*12,
        "Zins": darlehen*zins, "Tilgung": rate_jahr - (darlehen*zins)
    }
    
    return {
        "Name": obj_name, 
        "Invest (EK)": ek_invest, 
        "EK": ek_invest,
        "KP": kp, "NK": nk_betrag, "Darlehen": darlehen,
        "Detail_Tabelle": detail_data,
        "CAGR": cagr_10, 
        "Gewinn 10J": end_equity_10 - ek_invest, 
        "Avg_CF_10y_mtl": avg_cf_10y_mtl,
        "Start_Values": start_values,
        "Brutto_Rendite": (start_values["Miete"]/kp)*100,
        "Raw_Kosten_n_uml": params["Kosten_n_uml"],
        "Raw_Bj": params["bj"],
        "Sim_Mietsteig": miet_st,
        "Sim_Wertsteig": wert_st,
        "Sim_AfA": used_afa_rate,
        "Summary_Case": params["Summary_Case"]
    }

def render_scenario_table(df_full, years, invest_ek):
    df_slice = df_full.head(years).copy()
    
    cols_to_sum = ["Miete", "Bewirtschaftung", "Zinsen", "Tilgung", "CF_Vor_Steuer", "Steuer_Effekt", "CF_Nach_Steuer", "Wertzuwachs"]
    totals = df_slice[cols_to_sum].sum()
    
    last_row = df_slice.iloc[-1]
    verkaufspreis = last_row["Immo_Wert"]
    restschuld = last_row["Restschuld"]
    summe_cf = totals["CF_Nach_Steuer"]
    
    gewinn_immo = (verkaufspreis - restschuld) + summe_cf - invest_ek
    cagr_immo = (((verkaufspreis - restschuld) + summe_cf) / invest_ek) ** (1/years) - 1 if invest_ek > 0 else 0

    st.markdown(f"##### 📊 Rendite-Vergleich nach {years} Jahren")
    k1, k2, k3 = st.columns(3)
    k1.metric("EK-Rendite (mit Hebel)", f"{cagr_immo*100:.2f} %")
    k2.metric("Gewinn (Netto)", f"{gewinn_immo:,.0f} €")
    
    display_cols = ["Jahr", "Miete", "Bewirtschaftung", "Zinsen", "Tilgung", "CF_Vor_Steuer", "Steuer_Effekt", "CF_Nach_Steuer", "Restschuld", "Immo_Wert", "Cum_CF"]
    st.dataframe(df_slice[display_cols].style.format("{:,.0f} €"), use_container_width=True)

# ==========================================
# 4. VIEW & UI LOGIK
# ==========================================
if page == "📊 Portfolio Übersicht":
    st.title("📊 Immobilien-Portfolio Dashboard")
    
    # BERECHNUNG ALLER OBJEKTE
    results = [calculate_investment(n, d) for n, d in OBJEKTE.items()]
    
    # AGGREGIERTE DATEN
    total_invest = sum([r['Invest (EK)'] for r in results])
    total_volume = sum([r['KP'] for r in results])
    total_debt = sum([r['Darlehen'] for r in results])
    total_cf_month = sum([r['Detail_Tabelle'][0]['CF_Nach_Steuer'] for r in results]) / 12
    avg_yield = sum([r['Brutto_Rendite'] for r in results]) / len(results) if results else 0

    with st.container(border=True):
        st.subheader("🏢 Portfolio Gesamt-Status")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Portfolio Wert", f"{total_volume:,.0f} €")
        m2.metric("Investiertes EK", f"{total_invest:,.0f} €")
        m3.metric("Bank-Finanzierung", f"{total_debt:,.0f} €")
        m4.metric("Ø Mietrendite", f"{avg_yield:.2f} %")
        m5.metric("Cashflow (mtl. Start)", f"{total_cf_month:,.0f} €", delta_color="normal")

    st.markdown("---")

    st.subheader("📋 Objekt-Performance & Strategie")
    
    table_data = []
    for r in results:
        table_data.append({
            "Objekt": r["Name"],
            "Strategie": r["Summary_Case"].split(".")[0],
            "Kaufpreis": f"{r['KP']:,.0f} €",
            "Invest (EK)": f"{r['Invest (EK)']:,.0f} €",
            "Rendite": f"{r['Brutto_Rendite']:.2f} %",
            "EKR (Exit 10J)": f"{r['CAGR']:.2f} %",
            "Ø CF (mtl. 10J)": f"{r['Avg_CF_10y_mtl']:,.0f} €",
            "Gewinn (10J)": f"{r['Gewinn 10J']:,.0f} €"
        })
    
    df_dashboard = pd.DataFrame(table_data)
    st.dataframe(df_dashboard, use_container_width=True, hide_index=True)

else:
    st.title("🔍 Detail-Ansicht & Bearbeiten")
    selected_obj_name = st.selectbox("Objekt wählen:", list(OBJEKTE.keys()))
    obj_data = OBJEKTE[selected_obj_name]

    top_area = st.container()
    st.markdown("---")
    bottom_area = st.container()

    with top_area:
        st.markdown("### 📍 Objekt-Steckbrief (Stammdaten)")
        with st.container(border=True):
            c_prof1, c_prof2 = st.columns(2)
            with c_prof1:
                st.markdown(f"**🏠 Adresse:** {obj_data.get('Adresse', 'n.v.')}")
                st.markdown(f"**📏 Größe:** {obj_data['qm']} m² | {obj_data['zimmer']} Zi.")
                st.markdown(f"**📅 Baujahr:** {obj_data['bj']}")
            with c_prof2:
                st.markdown(f"**⚡ Energie:** {obj_data.get('Energie_Info', 'n.v.')}")
                st.markdown(f"**💶 Hausgeld (Gesamt):** {obj_data.get('Hausgeld_Gesamt', 0)} €")
                st.markdown(f"**🔑 Status:** {obj_data.get('Status', 'n.v.')}")
        
        if obj_data.get("Basis_Info"):
            st.info(f"ℹ️ **Kalkulations-Basis:** {obj_data['Basis_Info']}")

        c_link, c_pdf = st.columns(2)
        url = obj_data.get("Link", "")
        if url:
            btn_html = f"""<a href="{url}" target="_blank" style="text-decoration: none;"><div style="background-color: #0052cc; padding: 8px 12px; border-radius: 4px; text-align: center; color: white;">↗ Zum Inserat</div></a>"""
            c_link.markdown(btn_html, unsafe_allow_html=True)

        pdf_path = obj_data.get("PDF_Path")
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                c_pdf.download_button("📄 Exposé PDF", f, file_name=os.path.basename(pdf_path), use_container_width=True)
        else:
            c_pdf.info("ℹ️ Kein Exposé hinterlegt")

        img_urls = obj_data.get("Bild_URLs", [])
        if img_urls:
            st.markdown("---")
            st.subheader("📸 Galerie")
            cols = st.columns(4)
            for i, url in enumerate(img_urls):
                with cols[i % 4]:
                    st.image(url, use_container_width=True)

        st.markdown("---")
        st.header("📊 Core KPIs (Live-Ergebnis)")
        
        with st.expander("⚙️ Parameter anpassen (Simulation)", expanded=True):
            c_sim1, c_sim2, c_sim3, c_sim4 = st.columns(4)
            sim_zins = c_sim1.slider("Simulierter Zins (%)", 1.0, 6.0, global_zins*100, 0.1) / 100
            sim_mietsteig = c_sim2.slider("Mietsteigerung (%)", 0.0, 5.0, obj_data['Mietsteigerung']*100, 0.1) / 100
            sim_wertsteig = c_sim3.slider("Wertsteigerung (%)", 0.0, 6.0, obj_data['Wertsteigerung_Immo']*100, 0.1) / 100
            sim_afa = c_sim4.slider("AfA Satz (%)", 1.0, 5.0, obj_data['AfA_Satz']*100, 0.1) / 100

        res = calculate_investment(
            selected_obj_name, obj_data, 
            zins_indiv=sim_zins, 
            mietsteig_indiv=sim_mietsteig, 
            wertsteig_indiv=sim_wertsteig,
            afa_indiv=sim_afa
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kaufpreis", f"{obj_data['Kaufpreis']:,.0f} €")
        c2.metric("Invest (EK inkl. Puffer)", f"{res['Invest (EK)']:,.0f} €")
        c3.metric("Mietrendite (Soll)", f"{res['Brutto_Rendite']:.2f} %")
        
        miete_qm = obj_data['Miete_Start'] / obj_data['qm']
        delta_markt = miete_qm - obj_data.get("Marktmiete_m2", 0)
        c4.metric("Ø Miete vs. Markt", f"{miete_qm:.2f} €/m²", delta=f"{delta_markt:+.2f} €", delta_color="normal" if delta_markt >= 0 else "inverse")

        st.markdown("---")
        st.header("💰 Financial Figures")
        
        with st.expander("📘 Lesehilfe anzeigen", expanded=False):
            st.write("Detaillierte Aufschlüsselung der Zahlungsströme über 20 Jahre.")

        df_full = pd.DataFrame(res["Detail_Tabelle"])
        st.subheader("📅 10-Jahres-Szenario")
        render_scenario_table(df_full, 10, res['Invest (EK)'])
        
        with st.expander("📅 Langzeit-Szenarien (15/20 Jahre)"):
            render_scenario_table(df_full, 15, res['Invest (EK)'])
            render_scenario_table(df_full, 20, res['Invest (EK)'])

        st.markdown("---")
        st.header("Executive Summary")
        
        with st.container(border=True):
            st.markdown(f"""
            **Strategie:** {obj_data.get('Summary_Case', 'Standard')}
            
            **Stärken:**
            {obj_data.get('Summary_Pros', '-')}
            
            **Risiken:**
            {obj_data.get('Summary_Cons', '-')}
            """)

    st.sidebar.markdown("---")
    st.sidebar.header("🖨 Export")
    pdf_bytes = create_pdf_expose(selected_obj_name, obj_data, res)
    st.sidebar.download_button("📄 Download Bank-Exposé", pdf_bytes, f"Expose_{selected_obj_name}.pdf", "application/pdf")

    with bottom_area:
        st.header("⚙️ Configuration Center")
        with st.expander("📝 Daten & Details bearbeiten", expanded=False):
            st.subheader("🏠 Stammdaten")
            c_e1, c_e2, c_e3 = st.columns(3)
            new_adresse = c_e1.text_input("Adresse:", value=obj_data.get("Adresse", ""))
            new_qm = c_e2.number_input("Wohnfläche (m²):", value=float(obj_data.get("qm", 0)))
            new_bj = c_e3.number_input("Baujahr:", value=int(obj_data.get("bj", 1900)))
            
            # --- Hier folgen die weiteren Eingabefelder (gekürzt für Übersicht) ---
            
            if st.button("💾 Alle Änderungen Speichern"):
                OBJEKTE[selected_obj_name]["Adresse"] = new_adresse
                OBJEKTE[selected_obj_name]["qm"] = new_qm
                OBJEKTE[selected_obj_name]["bj"] = new_bj
                save_data(OBJEKTE)
                st.success("Gespeichert!")
                st.rerun()
