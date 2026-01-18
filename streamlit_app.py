import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import tempfile
import json
import os
from datetime import date

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

# CSS Hack für schönere Selectboxen & Tabellen-Farben
st.markdown("""
<style>
div[data-baseweb="select"] > div {border-color: #808495 !important; border-width: 1px !important;}
/* Abgelehnten Zeilen eine leichte Rötung geben (optional, wirkt nur bedingt in st.dataframe) */
</style>
""", unsafe_allow_html=True)

START_JAHR = 2026
DATA_FILE = "portfolio_data_final_v2.json" # Neue Datei für Version 2
MEDIA_DIR = "expose_files"

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# ==========================================
# 0. DATEN (DIE OBJEKTE)
# ==========================================
DEFAULT_OBJEKTE = {
    "Winsen (Optimierter Deal)": {
        "Adresse": "21423 Winsen (Luhe)", 
        "qm": 55.0, "zimmer": 2.0, "bj": 1985,
        "Kaufpreis": 160080, "Nebenkosten_Quote": 0.1057, 
        "Renovierung": 0, "Heizung_Puffer": 1000, 
        "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 633.65, 
        "Hausgeld_Gesamt": 262, "Kosten_n_uml": 80, 
        "Marktmiete_m2": 11.52, "Energie_Info": "Gas-Zentral, Bj 1985 (Solide)",
        "Status": "Vermietet (Top-Miete)",
        "Link": "https://www.immobilienscout24.de/expose/159800505", 
        "Bild_URLs": [], "PDF_Path": "",
        "Erfassungsdatum": "2026-01-18", "Archiviert": False,
        "Basis_Info": """Kaufpreis fiktiv auf 160.080€ (-8%) verhandelt! Miete ist mit 11,50€/qm top.""",
        "Summary_Case": """Durch Preisreduktion fast Cashflow-Neutral (-180€). Solide Substanz.""",
        "Summary_Pros": """- Hohe Miete (633€).\n- Guter Zustand (Bj 85).\n- Verhandlungs-Potenzial.""",
        "Summary_Cons": """- Maklerprovision fällig.\n- Wenig Mietsteigerungspotenzial (schon hoch)."""
    },
    "Meckelfeld (Ziel-Preis 160k)": {
        "Adresse": "Am Bach, 21217 Seevetal", 
        "qm": 59, "zimmer": 2.0, "bj": 1965,
        "Kaufpreis": 160000, "Nebenkosten_Quote": 0.07, 
        "Renovierung": 0, "Heizung_Puffer": 2000, 
        "AfA_Satz": 0.03, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 632.50, "Hausgeld_Gesamt": 368, "Kosten_n_uml": 130, 
        "Marktmiete_m2": 13.45, "Energie_Info": "Gas (2022/23 neu!), 181 kWh (F)",
        "Status": "Vermietet (Treppenmiete)",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/etw-kapitalanlage-meckelfeld-eigenland-ohne-makler-/3295455732-196-2812", 
        "Bild_URLs": [], "PDF_Path": "",
        "Erfassungsdatum": "2026-01-18", "Archiviert": False,
        "Basis_Info": """Heizung NEU (2022). Miete steigt in Stufen (2027: 690€, 2029: 727€). Kalkuliert mit Zielpreis 160k.""",
        "Summary_Case": """Substanz-Deal mit extremem Steuer-Hebel. Bei 160k sehr attraktiv nach Steuer.""",
        "Summary_Pros": """- Provisionsfrei.\n- Fixe Mietsteigerung (Treppe).\n- Heizung nagelneu.""",
        "Summary_Cons": """- Energieklasse F (aber Heizung neu).\n- WEG-Risiko (Fassade/Bahn)."""
    },
    "Pinneberg-Thesdorf (Provisionsfrei)": {
        "Adresse": "25421 Pinneberg (Thesdorf)", 
        "qm": 59.0, "zimmer": 2.0, "bj": 1976,
        "Kaufpreis": 174000, "Nebenkosten_Quote": 0.085, 
        "Renovierung": 1500, "Heizung_Puffer": 0, 
        "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 650, 
        "Hausgeld_Gesamt": 245, "Kosten_n_uml": 85, 
        "Marktmiete_m2": 11.50, "Energie_Info": "Bj 1976, Fernwärme/Gas",
        "Status": "Offen (Anlage/Eigennutz)",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/anlage-oder-eigennutzung-2-zi-whg-in-pi-thesdorf/3301019183-196-786", 
        "Bild_URLs": [], "PDF_Path": "",
        "Erfassungsdatum": "2026-01-18", "Archiviert": False,
        "Basis_Info": """Provisionsfrei! S-Bahn-Lage. Günstiges Hausgeld.""",
        "Summary_Case": """Geringes Invest (nur ~15k EK). Solider Cashflow bei Neuvermietung.""",
        "Summary_Pros": """- Provisionsfrei.\n- S-Bahn Nähe.\n- Hausgeld moderat.""",
        "Summary_Cons": """- Baujahr 1976 (Beton-Charme).\n- Miete ist Schätzwert."""
    },
    "Buxtehude (5-Zi Volumen-Deal)": {
        "Adresse": "Stader Str., 21614 Buxtehude", 
        "qm": 109.07, "zimmer": 5.0, "bj": 1972,
        "Kaufpreis": 236000, "Nebenkosten_Quote": 0.1057, 
        "Renovierung": 0, "Heizung_Puffer": 2000, 
        "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 925, 
        "Hausgeld_Gesamt": 380, "Kosten_n_uml": 120, 
        "Marktmiete_m2": 10.00, "Energie_Info": "Fernwärme (Bj 1972), Klasse F",
        "Status": "Vermietet seit 2007",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/vermietete-eigentumswohnung-in-buxtehude/3299469372-196-3328", 
        "Bild_URLs": [], "PDF_Path": "",
        "Erfassungsdatum": "2026-01-12", "Archiviert": False,
        "Basis_Info": """Riesige Fläche für 2.163€/qm. Langjähriger Mieter (Potenzial).""",
        "Summary_Case": """Substanz-Deal. Günstiger Einkauf, aber Energie-Risiko.""",
        "Summary_Pros": """- Preis/qm sehr niedrig (2.163€).\n- 5 Zimmer (selten).""",
        "Summary_Cons": """- Energieklasse F (Sanierungsdruck).\n- Alter Mietvertrag."""
    },
    "Harburg (10er Paket)": {
        "Adresse": "Eißendorf, Harburg", 
        "qm": 313, "zimmer": 10, "bj": 1956,
        "Kaufpreis": 998000, "Nebenkosten_Quote": 0.11,
        "Miete_Start": 3900, "Hausgeld_Gesamt": 1000, "Kosten_n_uml": 500,
        "Marktmiete_m2": 12.50, "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02, 
        "Renovierung": 0, "Heizung_Puffer": 0, "Status": "Vermietet", "Energie_Info": "n.v.", "Link": "", "Bild_URLs": [], "PDF_Path": "",
        "Erfassungsdatum": "2026-01-18", "Archiviert": True, # BEISPIEL FÜR ROT
        "Basis_Info": """Zu teuer (3.188 €/m²). Kein Mengenrabatt.""",
        "Summary_Case": """Abgelehnt.""", "Summary_Pros": "", "Summary_Cons": ""
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
                # Backfill new fields if missing in saved data
                if "Erfassungsdatum" not in merged[k]: merged[k]["Erfassungsdatum"] = date.today().strftime("%Y-%m-%d")
                if "Archiviert" not in merged[k]: merged[k]["Archiviert"] = False
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
    
    # Check Special Logic Flags
    is_meckelfeld = "Meckelfeld" in obj_name
    
    data = []
    restschuld = loan
    immo_wert = kp
    
    # 20 Jahre Berechnung
    for i in range(21): # 0 bis 20
        jahr = START_JAHR + i
        
        # --- MIET-LOGIK ---
        if is_meckelfeld:
            rent_monthly = 0
            if jahr < 2027: rent_monthly = params["Miete_Start"] 
            elif jahr < 2029: rent_monthly = 690.00
            elif jahr < 2032: rent_monthly = 727.38
            else:
                base_2032 = 793.50
                rent_monthly = base_2032 * (1 + miet_st)**(jahr - 2032)
            rent_yr = rent_monthly * 12
        else:
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
        "Used_Zins": zins, "Used_AfA": afa_rate,
        "Datum": params.get("Erfassungsdatum", "n.v."),
        "Archiviert": params.get("Archiviert", False)
    }

# ==========================================
# 3. UI
# ==========================================
if page == "📊 Portfolio Übersicht":
    st.title("📊 Immobilien-Portfolio Dashboard")
    results = [calculate_investment(k, v) for k, v in OBJEKTE.items()]
    
    # Nur aktive Deals für die Metriken zählen
    active_results = [r for r in results if not r["Archiviert"]]
    
    tot_invest = sum(r["Invest"] for r in active_results)
    tot_cf = sum(r["Avg_CF"] for r in active_results)
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Gesamt-Invest (Aktive Deals)", f"{tot_invest:,.0f} €")
        c2.metric("Ø Cashflow (Aktive)", f"{tot_cf:,.0f} €", delta_color="normal")
        c3.metric("Aktive Objekte", len(active_results))
    
    # Styling Funktion für DataFrame
    def color_archiv(val):
        color = '#ffcccc' if val == "❌ Ja" else ''
        return f'background-color: {color}'

    df_data = []
    for r in results:
        status_icon = "❌ Ja" if r["Archiviert"] else "✅ Nein"
        df_data.append({
            "Datum": r["Datum"],
            "Status": status_icon,
            "Objekt": r["Name"],
            "Kaufpreis": f"{r['KP']:,.0f} €",
            "Invest (EK)": f"{r['Invest']:,.0f} €",
            "Rendite": f"{r['Rendite']:.2f} %",
            "EKR (10J)": f"{r['CAGR']:.2f} %",
            "Ø CF (Nach St.)": f"{r['Avg_CF']:,.0f} €"
        })
        
    df = pd.DataFrame(df_data)
    
    # Anzeige mit bedingter Formatierung (via Pandas Styler in Streamlit bedingt möglich, 
    # hier einfache Darstellung. Rot-Markierung über 'Status'-Spalte visuell erkennbar).
    st.dataframe(
        df.style.applymap(lambda x: "background-color: #3b1e1e; color: #ff9999" if x == "❌ Ja" else "", subset=["Status"]),
        use_container_width=True, 
        hide_index=True
    )

else:
    st.title("🔍 Detail-Ansicht & Bearbeiten")
    sel = st.selectbox("Objekt wählen:", list(OBJEKTE.keys()))
    obj_data = OBJEKTE[sel]
    
    # Archiv Status Anzeige
    if obj_data.get("Archiviert"):
        st.error("❌ Dieses Objekt ist als 'Abgelehnt/Archiviert' markiert.")
    
    # ----------------------------------------------------
    # STECKBRIEF (INKL. INVEST-BERECHNUNG)
    # ----------------------------------------------------
    st.markdown("### 📍 Objekt-Steckbrief")
    
    # KAUFPREIS & NK BERECHNUNG FÜR HERLEITUNG
    kp_val = obj_data["Kaufpreis"]
    nk_quote = obj_data["Nebenkosten_Quote"]
    nk_wert = kp_val * nk_quote
    reno_wert = obj_data.get("Renovierung", 0)
    puffer_wert = obj_data.get("Heizung_Puffer", 0)
    invest_ek = nk_wert + reno_wert + puffer_wert

    with st.container(border=True):
        c_prof1, c_prof2 = st.columns(2)
        with c_prof1:
            st.markdown(f"**📅 Erfasst am:** {obj_data.get('Erfassungsdatum', 'n.v.')}")
            st.markdown(f"**🏠 Adresse:** {obj_data.get('Adresse', 'n.v.')}")
            st.markdown(f"**📏 Größe:** {obj_data['qm']} m² | {obj_data['zimmer']} Zi.")
            st.markdown(f"**⚡ Energie:** {obj_data.get('Energie_Info', 'n.v.')}")
        with c_prof2:
            st.markdown(f"**💶 Hausgeld:** {obj_data.get('Hausgeld_Gesamt', 0)} €")
            st.markdown(f"**🔑 Status:** {obj_data.get('Status', 'n.v.')}")
        
        st.markdown("---")
        st.metric("💸 Invest (Eigenkapital)", f"{invest_ek:,.0f} €")

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

    # ----------------------------------------------------
    # EDIT & UPLOAD AREA
    # ----------------------------------------------------
    st.markdown("---")
    st.header("⚙️ Daten ändern & Status")
    
    with st.expander("📝 Stammdaten & Status bearbeiten", expanded=True):
        c_e1, c_e2 = st.columns(2)
        
        # STATUS CHECKBOX
        is_archived = c_e1.checkbox("❌ Als 'Abgelehnt/Archiviert' markieren", value=obj_data.get("Archiviert", False))
        
        # DATE PICKER
        try:
            curr_date = date.fromisoformat(obj_data.get("Erfassungsdatum", "2026-01-01"))
        except:
            curr_date = date.today()
        new_date = c_e2.date_input("Erfassungsdatum", curr_date)
        
        st.markdown("---")
        
        c_e3, c_e4, c_e5 = st.columns(3)
        n_kp = c_e3.number_input("Kaufpreis", value=float(obj_data["Kaufpreis"]))
        n_miete = c_e4.number_input("Start-Miete", value=float(obj_data["Miete_Start"]))
        n_qm = c_e5.number_input("Wohnfläche", value=float(obj_data["qm"]))
        
        n_link = st.text_input("Link zum Inserat", value=obj_data.get("Link", ""))
        n_case = st.text_area("Investment Case", value=obj_data.get("Summary_Case", ""))
        
        if st.button("💾 Änderungen Speichern"):
            OBJEKTE[sel].update({
                "Archiviert": is_archived,
                "Erfassungsdatum": new_date.strftime("%Y-%m-%d"),
                "Kaufpreis": n_kp, "Miete_Start": n_miete, "qm": n_qm, "Link": n_link,
                "Summary_Case": n_case
            })
            save_data(OBJEKTE)
            st.success("Gespeichert!")
            st.rerun()

    # ----------------------------------------------------
    # LIVE-CALC & JAHRESPLÄNE
    # ----------------------------------------------------
    if not obj_data.get("Archiviert"):
        st.markdown("---")
        st.header("📊 Kalkulation & Szenarien")
        
        res = calculate_investment(sel, OBJEKTE[sel])
        
        # 1. TOP KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Ø Monatl. CF (Nach Steuer)", f"{res['Avg_CF']:,.0f} €")
        k2.metric("EKR (10J)", f"{res['CAGR']:.2f} %")
        k3.metric("Miete/m²", f"{(res['Detail'][0]['Miete (mtl.)']/obj_data['qm']):.2f} €")
        k4.metric("Gewinn nach 10J", f"{res['Gewinn_10J']:,.0f} €")

        # 2. HAUPT-TABELLE
        df_full = pd.DataFrame(res["Detail"])
        df_10 = df_full.head(10)[["Laufzeit", "Miete (mtl.)", "CF (vor Steuer)", "CF (nach Steuer)", "Restschuld"]]
        
        st.dataframe(
            df_10.style.format({
                "Miete (mtl.)": "{:,.2f} €",
                "CF (vor Steuer)": "{:,.0f} €",
                "CF (nach Steuer)": "{:,.0f} €",
                "Restschuld": "{:,.0f} €"
            }),
            use_container_width=True,
            hide_index=True
        )
