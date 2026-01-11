import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import tempfile
import requests
import json
import os
import shutil
import datetime

# ==========================================
# 0. SICHERHEIT / LOGIN (ROBUST)
# ==========================================
def check_password():
    """Returns `True` if the user had the correct password."""

    # 1. Das richtige Passwort ermitteln (Cloud oder Lokal)
    try:
        # Versuch, das Passwort aus dem Cloud-Tresor zu holen
        correct_password = st.secrets["password"]
    except:
        # Falls kein Tresor da ist (Lokal auf dem Mac), nimm dieses hier:
        correct_password = "DeinGeheimesPasswort123"

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Passwortfeld leeren
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Erster Aufruf, zeige Eingabe
        st.text_input(
            "🔒 Bitte Passwort eingeben, um das Portfolio zu laden:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        # Hinweis für dich lokal:
        try:
            st.secrets["password"]
        except:
            st.caption(f" (Lokaler Test-Modus aktiv. Passwort: {correct_password})")
            
        return False
    elif not st.session_state["password_correct"]:
        # Passwort war falsch
        st.text_input(
            "🔒 Bitte Passwort eingeben, um das Portfolio zu laden:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Passwort falsch.")
        return False
    else:
        # Passwort war richtig
        return True

# ==========================================
# KONFIGURATION & SETUP
# ==========================================
st.set_page_config(page_title="Immo-Portfolio Cockpit Pro", layout="wide", initial_sidebar_state="expanded")

# --- HIER GREIFT DER SCHUTZ ---
if not check_password():
    st.stop()  # Stoppt die App hier, wenn kein PW eingegeben wurde

# --- DESIGN FIX: Sichtbare Rahmen für Auswahlboxen ---
st.markdown("""
<style>
    /* Erzwingt einen hellen Rahmen um die Auswahlboxen im Dark Mode */
    div[data-baseweb="select"] > div {
        border-color: #808495 !important; /* Helleres Grau für Sichtbarkeit */
        border-width: 1px !important;
    }
</style>
""", unsafe_allow_html=True)
# -----------------------------------------------------

START_JAHR = 2026
DATA_FILE = "portfolio_data_final.json"
PDF_DIR = "expose_files"

if not os.path.exists(PDF_DIR):
    os.makedirs(PDF_DIR)

# ==========================================
# 0. DATEN-MANAGEMENT
# ==========================================
DEFAULT_OBJEKTE = {
    "Brackel (Neubau Sorgenfrei)": {
        "Adresse": "Beispielstraße 1, 21438 Brackel",
        "qm": 45, "zimmer": 2.0, "bj": 2021,
        "Kaufpreis": 119000, "Nebenkosten_Quote": 0.1057,
        "Renovierung": 0, "Heizung_Puffer": 0, "AfA_Satz": 0.02,
        "Miete_Start": 570, "Hausgeld_Gesamt": 180, "Kosten_n_uml": 40,
        "Wertsteigerung_Immo": 0.02, "Mietsteigerung": 0.02, "Marktmiete_m2": 10.50,
        "Energie_Info": "Bedarfsausweis, Klasse A/B (Neubau)",
        "Status": "Vermietet (Staffelmiete)",
        "Lage_Beschreibung": """Ruhige Dorflage im Speckgürtel. Gute Anbindung über A7, aber PKW notwendig. Ländlich geprägt, ideal für Pendler, die Ruhe suchen.""",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/charmante-2-zimmer-wohnung-in-brackel-als-kapitalanlage/3274042827-196-2809",
        "Bild_URLs": [], "PDF_Path": "", 
        "Basis_Info": """IST-Miete laut Exposé (Staffelmiete). Hausgeld konservativ geschätzt. AfA Standard 2%.""",
        "Summary_Case": """Klassische 'Cashflow-Cow'. Durch den sehr günstigen Einkaufspreis und die hohe Mietrendite trägt sich das Objekt fast von selbst.""",
        "Summary_Pros": """- Neubau-Standard (2021): Kein Sanierungsrisiko.
- Hohe Anfangsrendite.
- Staffelmiete vereinbart.""",
        "Summary_Cons": """- B-Lage (Brackel).
- Kleines Objekt."""
    },
    "Elmshorn (Substanz & Hebel)": {
        "Adresse": "Innenstadtbereich, 25335 Elmshorn",
        "qm": 76, "zimmer": 2.0, "bj": 1960,
        "Kaufpreis": 200000, "Nebenkosten_Quote": 0.085,
        "Renovierung": 0, "Heizung_Puffer": 5000, "AfA_Satz": 0.02,
        "Miete_Start": 800, "Hausgeld_Gesamt": 350, "Kosten_n_uml": 120,
        "Wertsteigerung_Immo": 0.025, "Mietsteigerung": 0.02, "Marktmiete_m2": 11.00,
        "Energie_Info": "Verbrauchsausweis, Gas, Klasse E/F",
        "Status": "Leerstand (Sofortige Neuvermietung geplant)",
        "Lage_Beschreibung": """Zentrale Lage in Elmshorn (Mittelzentrum). Bahnhof fußläufig erreichbar (Anbindung Hamburg-Altona ca. 25 Min). Alle Geschäfte des täglichen Bedarfs vor Ort.""",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/2-zimmerwohnung-in-innenatadtlage/3281010495-196-877",
        "Bild_URLs": [], "PDF_Path": "", 
        "Basis_Info": """Kalkulation mit ZIEL-Miete (10,50€/qm) bei sofortiger Neuvermietung (Leerstand). 5.000€ Puffer für Instandhaltung (Bj. 1960). Ankauf provisionsfrei.""",
        "Summary_Case": """Value-Add / Hebel-Strategie. Ankauf unter Marktwert. Durch den Leerstand kann sofort auf Marktniveau vermietet werden.""",
        "Summary_Pros": """- Extrem günstiger Einkaufspreis.
- Sofortiges Wertsteigerungspotenzial.
- Top Anbindung nach Hamburg.""",
        "Summary_Cons": """- Baujahr 1960: Mittelfristiges Sanierungsrisiko."""
    },
    "Eißendorf (Bj. 1994)": {
        "Adresse": "Ehestorfer Weg / Umfeld, 21075 Hamburg",
        "qm": 54, "zimmer": 2.0, "bj": 1994,
        "Kaufpreis": 195000, "Nebenkosten_Quote": 0.1107,
        "Renovierung": 0, "Heizung_Puffer": 0, "AfA_Satz": 0.02,
        "Miete_Start": 705, "Hausgeld_Gesamt": 285, "Kosten_n_uml": 80,
        "Wertsteigerung_Immo": 0.02, "Mietsteigerung": 0.02, "Marktmiete_m2": 13.50,
        "Energie_Info": "Verbrauchsausweis, 119 kWh (D), Gas-Zentral",
        "Status": "Vermietet (Solide)",
        "Lage_Beschreibung": """Beliebte Wohnlage in Hamburg-Eißendorf (Süd). Ruhig und grün (Nähe Harburger Berge), dennoch gute Busanbindung zum Harburger Zentrum. Solide bürgerliche Gegend.""",
        "Link": "https://www.immobilienscout24.de/expose/164391718",
        "Bild_URLs": [], 
        "PDF_Path": "", 
        "Basis_Info": """Hausgeld 285€ inkl. Rücklage. Miete 13€/qm ist marktüblich.""",
        "Summary_Case": """Sicherheits-Anker ('Safe Haven'). Qualitatives Fundament des Portfolios.""",
        "Summary_Pros": """- Top-Zustand (Bj. 1994): Fußbodenheizung.
- Starke Mieteinnahme.""",
        "Summary_Cons": """- Cashflow leicht negativ."""
    },
    "Harburg (Immovion - Risk Adjusted)": {
        "Adresse": "Hastedtstraße / Hastedtplatz, 21073 Hamburg (Harburg-Zentrum)", 
        "qm": 57, "zimmer": 2.0, "bj": 1954,
        "Kaufpreis": 159000, "Nebenkosten_Quote": 0.1107,
        "Renovierung": 5000, "Heizung_Puffer": 10000, "AfA_Satz": 0.025,
        "Miete_Start": 770, "Hausgeld_Gesamt": 162, "Kosten_n_uml": 60,
        "Wertsteigerung_Immo": 0.02, "Mietsteigerung": 0.02, "Marktmiete_m2": 13.60,
        "Energie_Info": "Verbrauch: 176 kWh (F), Gas",
        "Status": "Vermietet (Frei ab Frühjahr 2026)",
        "Lage_Beschreibung": """Zentrale City-Lage Harburg. Harburger Bahnhof (Fernverkehr) nur ca. 700m entfernt (5 Min). S-Bahn fußläufig (15 Min zum Hbf Hamburg). Phoenix-Center und Harburg-Arcaden in unmittelbarer Nähe. Hoher Freizeitwert durch Hastedtplatz/Grünflächen.""",
        "Link": "", "Bild_URLs": [], "PDF_Path": "", 
        "Basis_Info": """Szenario: 2,5% AfA. Invest inkl. 5k Reno + 10k Heizungs-Puffer. Miete auf 13,50€/qm.""",
        "Summary_Case": """Aggressive Rendite-Strategie mit Sicherheitsnetz. Günstiger Einkaufspreis erlaubt Investitionen.""",
        "Summary_Pros": """- Sehr günstiger Einkauf (< 2.800 EUR/qm).
- Steuer-Booster: 2,5% AfA.
- Puffer für Heizungstausch ist einkalkuliert.""",
        "Summary_Cons": """- Energieklasse F (Sanierungsstau).
- AfA-Erhöhung erfordert Gutachten."""
    },
    "Meckelfeld (Eigenland)": {
        "Adresse": "Am Bach (Sackgasse), 21217 Seevetal (Meckelfeld)", 
        "qm": 59, "zimmer": 2.0, "bj": 1965,
        "Kaufpreis": 180000, 
        "Nebenkosten_Quote": 0.07, # 5% GrESt + 2% Notar (KEIN Makler)
        "Renovierung": 0, "Heizung_Puffer": 2000, # Kleiner Sicherheitspuffer (Feuchtigkeit?)
        "AfA_Satz": 0.03, # 3% als konservatives Szenario (4% möglich)
        "Miete_Start": 632.50, 
        "Hausgeld_Gesamt": 368, 
        "Kosten_n_uml": 190, # 190,08 EUR lt. Wirtschaftsplan
        "Wertsteigerung_Immo": 0.02, 
        "Mietsteigerung": 0.02, 
        "Marktmiete_m2": 11.70,
        "Energie_Info": "Verbrauchsausweis 181 kWh (F), Gas",
        "Status": "Vermietet (Fixe Erhöhung 2027)",
        "Lage_Beschreibung": """Ruhige Sackgassenlage in Meckelfeld (Seevetal). Gute Anbindung nach Hamburg. Wohnung liegt im Halbparterre.""",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/etw-kapitalanlage-meckelfeld-eigenland-ohne-makler-/3295455732-196-2812", 
        "Bild_URLs": [], "PDF_Path": "", 
        "Basis_Info": """Miete steigt fix auf 690€ ab 07/2027. NK-Quote nur 7% da provisionsfrei. AfA-Potenzial (3-4%).""",
        "Summary_Case": """Substanz-Deal mit extremem Steuer-Hebel. Durch 100% Finanzierung und optimierte AfA (3-4%) sehr hohe Eigenkapitalrendite.""",
        "Summary_Pros": """- Provisionsfrei (Geringer Cash-Einsatz).
- Fixe Mietsteigerung 2027 vereinbart.
- Sehr hohe Rücklagenbildung (gut für Substanz).""",
        "Summary_Cons": """- Energieklasse F (181 kWh).
- Halbparterre (Feuchtigkeitsrisiko prüfen).
- Sonderumlage Müllplatz möglich (ca. 220€ Anteil)."""
    }
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data: return DEFAULT_OBJEKTE
            # Merge neuer Objekte in bestehende Daten
            for key, val in DEFAULT_OBJEKTE.items():
                if key not in data:
                    data[key] = val
                # Neue Felder ergänzen falls nötig
                for field, default_val in val.items():
                    if field not in data[key]:
                        data[key][field] = default_val
            
            # Aufräumen (optional, wenn du alte Testdaten löschen willst)
            # keys_to_remove = [k for k in data.keys() if k not in DEFAULT_OBJEKTE]
            # for k in keys_to_remove: del data[k]
            
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
    if data['bj'] >= 2010: case_txt = "Neubau-Strategie: Fokus auf Wertsicherung und minimalen Instandhaltungsaufwand."
    elif res['Brutto_Rendite'] > 5.5: case_txt = "Cashflow-Strategie: Hoher Ertrag deckt Kosten."
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
    
    # Header Info
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 10, f"Investment-Profil: {clean_text(obj_name)}", 0, 1, 'L')
    pdf.ln(5)

    # STECKBRIEF
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

    # FINANZEN
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, "Finanzierung & Rendite", 0, 1, 'L', 1)
    pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    
    pdf.cell(col_w, line_h, f"Kaufpreis: {res['KP']:,.0f} EUR", 0)
    pdf.cell(col_w, line_h, f"Gesamt-Invest: {res['Invest (EK)']:,.0f} EUR", 0, 1)
    pdf.cell(col_w, line_h, f"Miete (Soll p.a.): {res['Start_Values']['Miete']:,.0f} EUR", 0)
    pdf.cell(col_w, line_h, f"Mietrendite: {res['Brutto_Rendite']:.2f} %", 0, 1)
    pdf.ln(5)

    # INVESTMENT CASE
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
global_zins = st.sidebar.number_input("Zins Bank (%)", 1.0, 6.0, 3.80, 0.1) / 100 # Default auf 3.8 angepasst
global_tilgung = st.sidebar.number_input("Tilgung (%)", 0.0, 10.0, 1.50, 0.1) / 100 # Default auf 1.5 angepasst
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

    idx_10 = 9
    end_equity_10 = (detail_data[idx_10]['Immo_Wert'] - detail_data[idx_10]['Restschuld']) + detail_data[idx_10]['Cum_CF']
    cagr_10 = ((end_equity_10 / ek_invest) ** (1/10) - 1) * 100 if end_equity_10 > 0 else -99
    
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
        "Start_Values": start_values,
        "Brutto_Rendite": (start_values["Miete"]/kp)*100,
        "Raw_Kosten_n_uml": params["Kosten_n_uml"],
        "Raw_Bj": params["bj"],
        "Sim_Mietsteig": miet_st,
        "Sim_Wertsteig": wert_st,
        "Sim_AfA": used_afa_rate,
        "Gewinn 10J": end_equity_10 - ek_invest,
        "Summary_Case": params["Summary_Case"] # Für Dashboard
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

    # 1. HIGH LEVEL METRICS
    with st.container(border=True):
        st.subheader("🏢 Portfolio Gesamt-Status")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Portfolio Wert (Kaufpreis)", f"{total_volume:,.0f} €")
        m2.metric("Investiertes EK", f"{total_invest:,.0f} €")
        m3.metric("Bank-Finanzierung", f"{total_debt:,.0f} €")
        m4.metric("Ø Mietrendite", f"{avg_yield:.2f} %")
        m5.metric("Cashflow (mtl. nach Steuer)", f"{total_cf_month:,.0f} €", delta_color="normal")

    st.markdown("---")

    # 2. STRATEGIE MATRIX (TABELLE)
    st.subheader("📋 Objekt-Performance & Strategie")
    
    # Daten für Tabelle aufbereiten
    table_data = []
    for r in results:
        table_data.append({
            "Objekt": r["Name"],
            "Strategie": r["Summary_Case"].split(".")[0], # Erster Satz als Kurz-Strategie
            "Kaufpreis": f"{r['KP']:,.0f} €",
            "Invest (EK)": f"{r['Invest (EK)']:,.0f} €",
            "Rendite": f"{r['Brutto_Rendite']:.2f} %",
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
            if "kleinanzeigen" in url:
                btn_color = "#2D8C3C" 
                portal_name = "eBay Kleinanzeigen"
            elif "immobilienscout" in url:
                btn_color = "#FF6600" 
                portal_name = "ImmoScout24"
            elif "immowelt" in url:
                btn_color = "#F4B400" 
                portal_name = "Immowelt"
            else:
                btn_color = "#0052cc" 
                portal_name = "Online-Inserat"
            
            btn_html = f"""
            <a href="{url}" target="_blank" style="text-decoration: none;">
                <div style="background-color: {btn_color}; padding: 8px 12px; border-radius: 4px; text-align: center; color: white; font-weight: 500; font-family: sans-serif; font-size: 14px; width: 100%;">
                    ↗ Zum Inserat auf {portal_name}
                </div>
            </a>
            """
            c_link.markdown(btn_html, unsafe_allow_html=True)

        pdf_path = obj_data.get("PDF_Path")
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                c_pdf.download_button(
                    label="📄 Original Exposé herunterladen", 
                    data=f, 
                    file_name=os.path.basename(pdf_path), 
                    mime="application/pdf", 
                    use_container_width=True
                )
        else:
            c_pdf.info("ℹ️ Kein Exposé hinterlegt (Upload unten)")

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
        kpi_container = st.container()

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

        with kpi_container:
            miete_pro_qm = obj_data['Miete_Start'] / obj_data['qm'] if obj_data.get('qm', 0) > 0 else 0
            markt_miete = obj_data.get("Marktmiete_m2", 0)
            delta_markt = miete_pro_qm - markt_miete

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Kaufpreis", f"{obj_data['Kaufpreis']:,.0f} €")
            c2.metric("Invest (EK inkl. Puffer)", f"{res['Invest (EK)']:,.0f} €")
            c3.metric("Mietrendite (Soll)", f"{res['Brutto_Rendite']:.2f} %")
            c4.metric("Ø Miete vs. Markt", 
                      f"{miete_pro_qm:.2f} €/m²", 
                      delta=f"{delta_markt:+.2f} € (vs. Ø {markt_miete:.2f} € Markt)", 
                      delta_color="normal" if delta_markt >= 0 else "inverse")

        st.markdown("---")
        st.header("💰 Financial Figures")
        
        # --- BANKER LESEHILFE (PROAKTIV) ---
        with st.expander("📘 Lesehilfe: Berechnungsgrundlagen & Annahmen (für Bank)", expanded=False):
            st.markdown(f"""
            Diese Tabelle stellt die Liquiditätsentwicklung über die nächsten Jahre dar.
            
            * **Miete:** Startmiete {obj_data['Miete_Start']} € mit einer dynamischen Steigerung von **{res['Sim_Mietsteig']*100:.1f}% p.a.** (Inflationsausgleich).
            * **Bewirtschaftung:** Laufende, nicht-umlagefähige Kosten (Verwaltung & Instandhaltung). Hier kalkuliert mit **{res['Raw_Kosten_n_uml']} €/Monat**.
            * **Zinsen & Tilgung:** Annuitätendarlehen ({sim_zins*100:.1f}% Zins + {global_tilgung*100:.1f}% Tilgung).
            * **Steuer-Effekt:** Steuerliche Rückerstattung (bei negativen Einkünften) oder Last (bei Gewinn). Basis: Persönlicher Steuersatz {global_steuer*100:.0f}% und AfA von **{res['Sim_AfA']*100:.1f}%** auf den Gebäudeanteil.
            * **Immo-Wert:** Konservative Wertentwicklung der Immobilie um **{res['Sim_Wertsteig']*100:.1f}% p.a.**
            * **Cashflow (CF):** Der monatliche Überschuss/Unterdeckung nach Steuern. (Hinweis: Ein negativer CF ist oft durch die Tilgung bedingt, die realen Vermögensaufbau darstellt).
            """)
        
        # --- BANKER TOOLTIP / ERKLÄRUNG (NEU) ---
        monthly_cost = res['Raw_Kosten_n_uml']
        yearly_cost = monthly_cost * 12
        
        if monthly_cost < 60:
            reason = "Da es sich um einen Neubau/jüngeres Baujahr handelt, sind die Instandhaltungskosten initial sehr gering angesetzt."
        elif monthly_cost > 100:
            reason = "Aufgrund des Baujahres wurde ein erhöhter Sicherheits-Puffer für Instandhaltung berücksichtigt."
        else:
            reason = "Standard-Satz für Verwaltung und Instandhaltung."

        st.info(f"ℹ️ **Hinweis zur Bewirtschaftung:** Die Spalte 'Bewirtschaftung' enthält die nicht-umlagefähigen Kosten (Verwaltung & Instandhaltung). Hier: **{monthly_cost} €/Monat** (x12 = {yearly_cost} € p.a.). {reason}")
        # ----------------------------------

        df_full = pd.DataFrame(res["Detail_Tabelle"])
        st.subheader("📅 10-Jahres-Szenario")
        render_scenario_table(df_full, 10, res['Invest (EK)'])
        
        with st.expander("📅 15-Jahres-Szenario anzeigen"):
            render_scenario_table(df_full, 15, res['Invest (EK)'])

        with st.expander("📅 20-Jahres-Szenario anzeigen"):
            render_scenario_table(df_full, 20, res['Invest (EK)'])

        # --- EXECUTIVE SUMMARY / BANKER PITCH (WIEDER DA & UMBENANNT) ---
        st.markdown("---")
        st.header("Warum dieses Objekt eine sinnvolle Investition ist") # Titel angepasst
        
        yield_val = res['Brutto_Rendite']
        if yield_val > 5.0:
            strategy_title = "Cashflow-orientierte Strategie"
        else:
            strategy_title = "Wertsicherungs-Strategie"

        risk_puffer = obj_data.get('Heizung_Puffer', 0)
        risk_text = f"Zusätzlich wurde ein Investitions-Puffer von {risk_puffer:,.0f} € (z.B. für Heizung/Energetik) in die Finanzierung einkalkuliert, um Risiken zu minimieren." if risk_puffer > 0 else "Aufgrund des guten baulichen Zustands sind kurzfristig keine Sonderinvestitionen (CAPEX) notwendig."

        with st.container(border=True):
            st.markdown(f"""
            ### 📄 Executive Summary
            
            **Strategische Einordnung:**
            Das Investment in **{obj_data.get('Adresse', 'dieses Objekt')}** verfolgt eine klare **{strategy_title}**. 
            Mit einem Einkaufspreis von **{res['KP']:,.0f} €** und einer Anfangsrendite von **{yield_val:.2f} %** liegt das Objekt attraktiv im Marktvergleich.

            **1. Standort & Nachhaltigkeit:**
            {obj_data.get('Lage_Beschreibung', 'Die Lage bietet eine solide Vermietbarkeit.')}
            
            **2. Wirtschaftlichkeit & Sicherheit:**
            Das Objekt trägt sich operativ selbst. Die monatlichen Einnahmen decken die Bewirtschaftungskosten und einen Großteil des Kapitaldienstes. 
            Durch die Tilgung und konservativ geschätzte Wertsteigerung wird in den ersten 10 Jahren ein **Netto-Vermögenszuwachs von ca. {res['Gewinn 10J']:,.0f} €** prognostiziert.

            **3. Objektzustand & Risikomanagement:**
            Energie-Status: {obj_data.get('Energie_Info', 'k.A.')}.
            {risk_text}
            """)
        # -------------------------------------------------------------------

    st.sidebar.markdown("---")
    st.sidebar.header("🖨 Export")
    pdf_bytes = create_pdf_expose(selected_obj_name, obj_data, res)
    st.sidebar.download_button("📄 Download Bank-Exposé (PDF)", pdf_bytes, f"Bank_Expose_{selected_obj_name}.pdf", "application/pdf")

    with bottom_area:
        st.header("⚙️ Configuration Center")
        
        with st.expander("📝 Daten & Details bearbeiten", expanded=False):
            st.subheader("🏠 Stammdaten")
            c_e1, c_e2, c_e3 = st.columns(3)
            new_adresse = c_e1.text_input("Adresse:", value=obj_data.get("Adresse", ""))
            new_qm = c_e2.number_input("Wohnfläche (m²):", value=float(obj_data.get("qm", 0)), step=1.0)
            new_bj = c_e3.number_input("Baujahr:", value=int(obj_data.get("bj", 1900)), step=1)
            
            c_e4, c_e5, c_e6 = st.columns(3)
            new_zimmer = c_e4.number_input("Zimmer:", value=float(obj_data.get("zimmer", 1.0)), step=0.5)
            new_energie = c_e5.text_input("Energie-Info:", value=obj_data.get("Energie_Info", ""))
            new_status = c_e6.text_input("Status:", value=obj_data.get("Status", ""))
            
            new_lage = st.text_area("Lage & Umgebung:", value=obj_data.get("Lage_Beschreibung", ""), height=70)

            st.subheader("💰 Finanzen & Kosten")
            f1, f2, f3 = st.columns(3)
            new_kaufpreis = f1.number_input("Kaufpreis (€):", value=float(obj_data.get("Kaufpreis", 0)), step=1000.0)
            new_miete = f2.number_input("Miete Start (kalt p.m.):", value=float(obj_data.get("Miete_Start", 0)), step=10.0)
            new_marktmiete = f3.number_input("Marktmiete (€/m²):", value=float(obj_data.get("Marktmiete_m2", 0.0)), step=0.5)

            f4, f5, f6 = st.columns(3)
            new_hausgeld = f4.number_input("Hausgeld Gesamt (€):", value=float(obj_data.get("Hausgeld_Gesamt", 0)), step=10.0)
            new_kosten_n_uml = f5.number_input("Nicht umlagefähig (€):", value=float(obj_data.get("Kosten_n_uml", 0)), step=5.0)
            
            st.subheader("🛠️ Invest & Strategie")
            i1, i2, i3 = st.columns(3)
            new_reno = i1.number_input("Renovierung (fix) €:", value=float(obj_data.get("Renovierung", 0)), step=1000.0)
            new_puffer = i2.number_input("Puffer (Risiko) €:", value=float(obj_data.get("Heizung_Puffer", 0)), step=1000.0)
            new_link = i3.text_input("Link zum Inserat:", value=obj_data.get("Link", ""))
            
            new_basis_info = st.text_area("Notiz / Berechnungsgrundlage:", value=obj_data.get("Basis_Info", ""))

            st.markdown("#### Management Summary (Texte)")
            if st.button("✨ KI-Vorschlag generieren"):
                 sim_res_temp = calculate_investment(selected_obj_name, obj_data)
                 s_case, s_pros, s_cons = generate_auto_texts(obj_data, sim_res_temp)
                 OBJEKTE[selected_obj_name]["Summary_Case"] = s_case
                 OBJEKTE[selected_obj_name]["Summary_Pros"] = s_pros
                 OBJEKTE[selected_obj_name]["Summary_Cons"] = s_cons
                 save_data(OBJEKTE)
                 st.success("Texte generiert! Bitte Seite neu laden.")
                 st.rerun()

            sum_c1, sum_c2 = st.columns(2)
            new_case = sum_c1.text_area("Investment Case:", value=obj_data.get("Summary_Case", ""), height=100)
            new_pros = sum_c2.text_area("Stärken (Pros):", value=obj_data.get("Summary_Pros", ""), height=100)
            new_cons = st.text_area("Herausforderungen (Cons):", value=obj_data.get("Summary_Cons", ""), height=80)
            
            st.markdown("#### Datei-Upload")
            uploaded_pdf = st.file_uploader("Original-Exposé hochladen (PDF)", type="pdf")
            if uploaded_pdf:
                safe_name = "".join([c for c in selected_obj_name if c.isalnum()]) + ".pdf"
                save_path = os.path.join(PDF_DIR, safe_name)
                with open(save_path, "wb") as f: f.write(uploaded_pdf.getbuffer())
                OBJEKTE[selected_obj_name]["PDF_Path"] = save_path
                save_data(OBJEKTE)
                st.success(f"Exposé für {selected_obj_name} gespeichert!")
                st.rerun()

            new_imgs_str = st.text_area("Bild-URLs (eine pro Zeile):", value="\n".join(obj_data.get("Bild_URLs", [])), height=100)

            if st.button("💾 Alle Änderungen Speichern"):
                OBJEKTE[selected_obj_name].update({
                    "Adresse": new_adresse, "qm": new_qm, "bj": new_bj,
                    "zimmer": new_zimmer, "Energie_Info": new_energie, "Status": new_status,
                    "Lage_Beschreibung": new_lage,
                    "Kaufpreis": new_kaufpreis, "Miete_Start": new_miete, "Marktmiete_m2": new_marktmiete,
                    "Hausgeld_Gesamt": new_hausgeld, "Kosten_n_uml": new_kosten_n_uml,
                    "Renovierung": new_reno, "Heizung_Puffer": new_puffer, "Link": new_link,
                    "Basis_Info": new_basis_info,
                    "Summary_Case": new_case, "Summary_Pros": new_pros, "Summary_Cons": new_cons,
                    "Bild_URLs": [url.strip() for url in new_imgs_str.split("\n") if url.strip()]
                })
                save_data(OBJEKTE)
                st.success("Daten erfolgreich aktualisiert!")
                st.rerun()
