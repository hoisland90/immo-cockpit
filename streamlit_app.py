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
# KONFIGURATION
# ==========================================
st.set_page_config(page_title="Immo-Cockpit Pro", layout="wide")
if not check_password(): st.stop()

START_JAHR = 2026
DATA_FILE = "portfolio_data_final.json"
PDF_DIR = "expose_files"
if not os.path.exists(PDF_DIR): os.makedirs(PDF_DIR)

# ==========================================
# 0. DATEN (DAS 4-SÄULEN PORTFOLIO - FINAL)
# ==========================================
DEFAULT_OBJEKTE = {
    "Meckelfeld (Cashflow-King)": {
        "Adresse": "Am Bach, 21217 Seevetal", 
        "qm": 59, "zimmer": 2.0, "bj": 1965,
        "Kaufpreis": 180000, "Nebenkosten_Quote": 0.07, 
        "Renovierung": 0, "Heizung_Puffer": 2000, 
        "AfA_Satz": 0.03, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 632.50, "Hausgeld_Gesamt": 368, "Kosten_n_uml": 190, 
        "Marktmiete_m2": 11.70, "Energie_Info": "181 kWh (F), Gas",
        "Status": "Vermietet (Fixe Erhöhung 2027)",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/etw-kapitalanlage-meckelfeld-eigenland-ohne-makler-/3295455732-196-2812", 
        "Basis_Info": """Miete steigt fix auf 690€ (2027). NK nur 7% (privat).""",
        "Summary_Case": """Substanz-Deal mit extremem Steuer-Hebel.""",
        "Summary_Pros": """- Provisionsfrei.\n- Fixe Mietsteigerung.\n- Hohe Rücklagen.""",
        "Summary_Cons": """- Energieklasse F.\n- Müllplatz-Umlage möglich."""
    },
    "Elmshorn (Terrasse & Staffel)": {
        "Adresse": "Johannesstr. 24-28, 25335 Elmshorn", 
        "qm": 75.67, "zimmer": 2.0, "bj": 1994,
        "Kaufpreis": 229000, "Nebenkosten_Quote": 0.1207, # 6.5% GrESt + 2% Notar + 3.57% Makler
        "Renovierung": 0, "Heizung_Puffer": 1000, # Reduziert da Heizung 2012 (C)
        "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 665, 
        "Hausgeld_Gesamt": 370, "Kosten_n_uml": 165, 
        "Marktmiete_m2": 11.00, "Energie_Info": "104,9 kWh (C), Gas Bj. 2012",
        "Status": "Vermietet (Staffel 2026/27)",
        "Link": "https://www.kleinanzeigen.de/s-anzeige/moderne-2-zimmer-wohnung-inkl-aussenstellplatz-in-begehrter-lage/3296695424-196-2807", 
        "Basis_Info": """Staffelmiete (im Exposé zugesichert): 2026 -> 765€, 2027 -> 815€. Heizung lt. Ausweis 2012 (nicht 1994!).""",
        "Summary_Case": """Solides Investment mit eingebautem Rendite-Turbo und guter Substanz.""",
        "Summary_Pros": """- Heizung Bj. 2012 (Energie C).\n- Miete steigt fix auf 815€ (2027).\n- Terrasse & TG.""",
        "Summary_Cons": """- Hohes Hausgeld (Rücklagen).\n- Nachtrag zur Miete noch einzuholen."""
    },
    "Neu Wulmstorf (Neubau-Anker)": {
        "Adresse": "Hauptstraße, 21629 Neu Wulmstorf", 
        "qm": 65.79, "zimmer": 2.0, "bj": 2016,
        "Kaufpreis": 249000, "Nebenkosten_Quote": 0.07, 
        "Renovierung": 0, "Heizung_Puffer": 0, 
        "AfA_Satz": 0.02, "Mietsteigerung": 0.02, "Wertsteigerung_Immo": 0.02,
        "Miete_Start": 920, 
        "Hausgeld_Gesamt": 260, "Kosten_n_uml": 60, 
        "Marktmiete_m2": 14.50, "Energie_Info": "Energieeffizient (Bj 2016), Fußbodenhzg.",
        "Status": "Frei ab 02/2026 (Sofortige Neuvermietung)",
        "Link": "", 
        "Basis_Info": """Sicherheits-Baustein. Baujahr 2016. Privatverkauf (ohne Makler). Frei ab Februar -> Marktmiete.""",
        "Summary_Case": """'Sorglos-Paket'. Wertsicherung durch moderne Substanz & günstigen Einkauf.""",
        "Summary_Pros": """- PROVISIONSFREI (Invest < 18k).\n- Baujahr 2016 (Technik top).\n- Frei lieferbar (sofort 14€/qm).""",
        "Summary_Cons": """- Höchster Kaufpreis (249k).\n- Rendite ca. 4,4% (dafür sicher)."""
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
            # Merge logic: Keep user edits, add new defaults, remove deleted objects
            merged = {k: v for k, v in data.items() if k in DEFAULT_OBJEKTE} 
            for k, v in DEFAULT_OBJEKTE.items():
                if k not in merged:
                    merged[k] = v
                else:
                    # Special Update for Elmshorn if user has old data
                    if "Elmshorn" in k:
                         # Force update critical fields from default if they look old
                         if merged[k].get("Heizung_Puffer") > 2000:
                             merged[k]["Heizung_Puffer"] = 1000
                             merged[k]["Energie_Info"] = DEFAULT_OBJEKTE[k]["Energie_Info"]
            return merged
    return DEFAULT_OBJEKTE

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

OBJEKTE = load_data()

# ==========================================
# 1. BERECHNUNG
# ==========================================
st.sidebar.header("🏦 Global-Parameter")
global_zins = st.sidebar.number_input("Zins (%)", 1.0, 6.0, 3.8, 0.1) / 100
global_tilgung = st.sidebar.number_input("Tilgung (%)", 0.0, 10.0, 1.5, 0.1) / 100
global_steuer = st.sidebar.number_input("Steuersatz (%)", 20.0, 50.0, 42.0, 0.5) / 100

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
    
    # Spezielle Logik für Elmshorn Staffel
    is_elmshorn = "Elmshorn" in obj_name
    rent_start = params["Miete_Start"] * 12
    
    data = []
    restschuld = loan
    immo_wert = kp
    
    for i in range(20):
        jahr = START_JAHR + i
        
        if is_elmshorn:
            # Staffel: 2026=9180 (765), 2027=9780 (815), danach Steigerung
            if jahr == 2026: 
                rent_yr = 9180 
            elif jahr == 2027: 
                rent_yr = 9780 
            elif jahr > 2027:
                # Ab 2028 normale Steigerung auf Basis 2027
                # i=2 (2028) -> (i-1)=1 Jahr Steigerung
                rent_yr = 9780 * (1 + miet_st)**(i - 1) 
            else: 
                rent_yr = rent_start # Fallback 2025
        else:
            rent_yr = rent_start * (1 + miet_st)**i
            
        immo_wert *= (1 + wert_st)
        
        zinsen = restschuld * zins
        tilgung = rate_pa - zinsen
        costs = params["Kosten_n_uml"] * 12
        
        tax_base = rent_yr - zinsen - (kp*0.8*afa_rate) - costs
        tax = tax_base * global_steuer * -1
        cf = rent_yr - rate_pa - costs + tax
        
        restschuld -= tilgung
        data.append({"CF_Nach_Steuer": cf, "Immo_Wert": immo_wert, "Restschuld": restschuld})

    # KPIs
    res_10 = data[9]
    equity_10 = (res_10["Immo_Wert"] - res_10["Restschuld"]) + sum([d["CF_Nach_Steuer"] for d in data[:10]])
    cagr = ((equity_10 / invest)**(0.1) - 1) * 100 if invest > 0 else 0
    avg_cf = sum([d["CF_Nach_Steuer"] for d in data[:10]]) / 120
    
    return {
        "Name": obj_name, "Invest": invest, "KP": kp, "Rendite": (rent_start/kp)*100,
        "CAGR": cagr, "Avg_CF": avg_cf, "Gewinn_10J": equity_10 - invest,
        "Detail": data, "Params": params,
        "Used_Zins": zins, "Used_AfA": afa_rate, "Used_Miet": miet_st, "Used_Wert": wert_st
    }

# ==========================================
# 2. UI & PDF
# ==========================================
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
    pdf.cell(0, 10, f"{obj_name}", 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, f"Kaufpreis: {res['KP']:,.0f} EUR | Invest: {res['Invest']:,.0f} EUR", 0, 1)
    pdf.cell(0, 8, f"Rendite (Start): {res['Rendite']:.2f}% | EKR (10J): {res['CAGR']:.2f}%", 0, 1)
    pdf.ln(5)
    pdf.multi_cell(0, 6, f"Strategie: {data.get('Summary_Case')}")
    pdf.ln(2)
    pdf.multi_cell(0, 6, f"Pros: {data.get('Summary_Pros')}")
    pdf.ln(2)
    pdf.multi_cell(0, 6, f"Risiken: {data.get('Summary_Cons')}")
    return pdf.output(dest='S').encode('latin-1', 'replace')

page = st.sidebar.radio("Menü", ["Portfolio", "Details"])

if page == "Portfolio":
    st.title("📊 Portfolio Übersicht")
    results = [calculate_investment(k, v) for k, v in OBJEKTE.items()]
    
    # KPIs
    tot_invest = sum(r["Invest"] for r in results)
    tot_cf = sum(r["Avg_CF"] for r in results)
    st.metric("Gesamt-Invest (EK)", f"{tot_invest:,.0f} €")
    st.metric("Ø Cashflow Portfolio (mtl.)", f"{tot_cf:,.0f} €", delta_color="normal")
    
    # Tabelle
    df = pd.DataFrame([{
        "Objekt": r["Name"],
        "Kaufpreis": f"{r['KP']:,.0f} €",
        "Invest (EK)": f"{r['Invest']:,.0f} €",
        "Rendite (Start)": f"{r['Rendite']:.2f} %",
        "EK-Rendite (10J)": f"{r['CAGR']:.2f} %",
        "Ø CF (mtl. 10J)": f"{r['Avg_CF']:,.0f} €"
    } for r in results])
    st.dataframe(df, use_container_width=True)

else:
    st.title("🔍 Details & Edit")
    sel = st.selectbox("Objekt", list(OBJEKTE.keys()))
    obj = OBJEKTE[sel]
    
    # Edit Area mit direktem Speichern
    with st.expander("⚙️ Parameter bearbeiten (Live)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        curr_z = obj.get("Zins_Indiv", global_zins)
        curr_a = obj.get("AfA_Satz", 0.02)
        curr_m = obj.get("Mietsteigerung", 0.02)
        curr_w = obj.get("Wertsteigerung_Immo", 0.02)

        new_z = c1.slider("Zins (%)", 1.0, 6.0, curr_z*100, 0.1, key=f"z_{sel}") / 100
        new_a = c2.slider("AfA (%)", 1.0, 5.0, curr_a*100, 0.1, key=f"a_{sel}") / 100
        new_m = c3.slider("Mietsteigerung (%)", 0.0, 5.0, curr_m*100, 0.1, key=f"m_{sel}") / 100
        new_w = c4.slider("Wertsteigerung (%)", 0.0, 6.0, curr_w*100, 0.1, key=f"w_{sel}") / 100
        
        if (new_z != curr_z) or (new_a != curr_a) or (new_m != curr_m) or (new_w != curr_w):
            OBJEKTE[sel]["Zins_Indiv"] = new_z
            OBJEKTE[sel]["AfA_Satz"] = new_a
            OBJEKTE[sel]["Mietsteigerung"] = new_m
            OBJEKTE[sel]["Wertsteigerung_Immo"] = new_w
            save_data(OBJEKTE)
            st.rerun()

    # Calc & Show
    res = calculate_investment(sel, OBJEKTE[sel])
    
    st.subheader(f"Ergebnis: {res['Name']}")
    k1, k2, k3 = st.columns(3)
    k1.metric("Ø Cashflow (10J)", f"{res['Avg_CF']:,.0f} €")
    k2.metric("EK-Rendite (Exit)", f"{res['CAGR']:.2f} %")
    k3.metric("Gewinn nach 10J", f"{res['Gewinn_10J']:,.0f} €")

    st.write(f"**Strategie:** {obj.get('Summary_Case')}")
    st.write(f"**Pros:** {obj.get('Summary_Pros')}")
    st.write(f"**Cons:** {obj.get('Summary_Cons')}")
    
    with st.expander("Genaue Zahlen (10 Jahre)"):
        st.dataframe(pd.DataFrame(res["Detail"]).head(10).style.format("{:,.0f} €"))
    
    st.sidebar.markdown("---")
    pdf_bytes = create_pdf_expose(sel, obj, res)
    st.sidebar.download_button("📄 Exposé PDF", pdf_bytes, f"Expose_{sel}.pdf")
    
    with st.expander("📝 Stammdaten bearbeiten"):
        n_kp = st.number_input("Kaufpreis", value=float(obj["Kaufpreis"]))
        n_miete = st.number_input("Start-Miete", value=float(obj["Miete_Start"]))
        if st.button("Stammdaten speichern"):
            OBJEKTE[sel]["Kaufpreis"] = n_kp
            OBJEKTE[sel]["Miete_Start"] = n_miete
            save_data(OBJEKTE)
            st.success("Gespeichert!")
            st.rerun()
