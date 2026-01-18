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
# 0. KONFIGURATION
# ==========================================
st.set_page_config(page_title="Immo-Cockpit Pro", layout="wide", initial_sidebar_state="expanded")

# Nur minimales CSS für Selectboxen
st.markdown("""<style>div[data-baseweb="select"] > div {border-color: #808495 !important; border-width: 1px !important;}</style>""", unsafe_allow_html=True)

# LOGIN
def check_password():
    try:
        correct_password = st.secrets["password"]
    except:
        correct_password = "123" # Fallback für lokal

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.text_input("🔒 Passwort:", type="password", key="pwd_input")
        if st.session_state.get("pwd_input") == correct_password:
            st.session_state["password_correct"] = True
            st.rerun()
        return False
    return True

if not check_password(): st.stop()

START_JAHR = 2026
DATA_FILE = "portfolio_data_v5_plus.json" 
MEDIA_DIR = "expose_files"

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# ==========================================
# 0. DATEN
# ==========================================
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
# 1. BERECHNUNGSKERN
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
# 2. UI (NATIVE LOOK)
# ==========================================

st.sidebar.title("🧭 Menü")
page = st.sidebar.radio("Navigation:", ["📊 Portfolio Übersicht", "🔍 Detail-Ansicht & Bearbeiten"])
st.sidebar.markdown("---")

st.sidebar.header("🏦 Global-Parameter")
g_zins = st.sidebar.number_input("Zins Bank (%)", 1.0, 6.0, 3.80, 0.1) / 100
g_tilg = st.sidebar.number_input("Tilgung (%)", 0.0, 10.0, 1.50, 0.1) / 100
g_steuer = st.sidebar.number_input("Steuer (%)", 20.0, 50.0, 42.00, 0.5) / 100

# --- DATA PREP ---
results = [calculate_investment(k, v, g_zins, g_tilg, g_steuer) for k, v in OBJEKTE.items()]

# --- PAGE 1: ÜBERSICHT ---
if page == "📊 Portfolio Übersicht":
    st.title("📊 Immobilien-Portfolio Dashboard")
    
    show_mode = st.radio("Ansicht:", ["Nur Aktive (Top-Liste)", "Alle (inkl. Archiv/Vergleich)"], horizontal=True)
    
    if "Nur Aktive" in show_mode:
        display_results = [r for r in results if not r["Archiviert"]]
    else:
        display_results = results
    
    # KPIs
    tot_invest = sum(r["Invest"] for r in display_results)
    tot_cf = sum(r["Avg_CF"] for r in display_results)
    tot_gewinn = sum(r["Gewinn_10J"] for r in display_results)
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Gesamt-Invest", f"{tot_invest:,.0f} €")
        c2.metric("Ø Cashflow (mtl.)", f"{tot_cf:,.0f} €")
        c3.metric("Gewinn nach 10J (Gesamt)", f"{tot_gewinn:,.0f} €")
    
    # CHARTS
    if len(display_results) > 0:
        st.markdown("---")
        t1, t2 = st.tabs(["📈 Portfolio-Matrix", "💰 Vermögens-Maschine"])
        
        with t1:
            st.subheader("Bubble Chart: Wo liegen die Perlen?")
            bubble_data = []
            for r in display_results:
                bubble_data.append({
                    "Objekt": r["Name"], "Kaufpreis": r["KP"], 
                    "Rendite (%)": round(r["Rendite"], 2), "Invest": r["Invest"],
                    "Status": "Archiv" if r["Archiviert"] else "Aktiv"
                })
            fig = px.scatter(pd.DataFrame(bubble_data), x="Kaufpreis", y="Rendite (%)", size="Invest", color="Status", 
                             hover_name="Objekt", size_max=60, color_discrete_map={"Aktiv": "green", "Archiv": "red"})
            st.plotly_chart(fig, use_container_width=True)

        with t2:
            st.subheader("Die Vermögens-Maschine (20 Jahre)")
            years = list(range(START_JAHR, START_JAHR + 21))
            agg_equity = {y: 0 for y in years}
            agg_debt = {y: 0 for y in years}
            for r in display_results:
                for row in r["Detail"]:
                    agg_equity[row["Jahr"]] += (row["Immo-Wert"] - row["Restschuld"])
                    agg_debt[row["Jahr"]] += row["Restschuld"]
            
            df_wealth = pd.DataFrame({"Jahr": years, "Netto-Vermögen": list(agg_equity.values()), "Bank-Schulden": list(agg_debt.values())})
            
            # Area Chart mit Plotly für bessere Kontrolle
            fig_w = go.Figure()
            fig_w.add_trace(go.Scatter(x=df_wealth["Jahr"], y=df_wealth["Netto-Vermögen"], stackgroup='one', name='Netto-Vermögen', line=dict(color='#2E7D32', width=0)))
            fig_w.add_trace(go.Scatter(x=df_wealth["Jahr"], y=df_wealth["Bank-Schulden"], stackgroup='one', name='Bank-Schulden', line=dict(color='#C62828', width=0)))
            fig_w.update_layout(height=400, hovermode="x unified")
            st.plotly_chart(fig_w, use_container_width=True)

    # TABELLE (JETZT MIT GEWINN SPALTE!)
    st.subheader("📋 Objekt-Liste")
    table_data = []
    for r in display_results:
        status_icon = "❌ Archiv" if r["Archiviert"] else "✅ Aktiv"
        table_data.append({
            "Status": status_icon,
            "Objekt": r["Name"],
            "Kaufpreis": r['KP'],
            "Invest (EK)": r['Invest'],
            "Rendite": r['Rendite'],
            "Ø CF (Nach St.)": r['Avg_CF'],
            "Gewinn (10J)": r['Gewinn_10J'] # <--- NEUE SPALTE
        })
    
    st.dataframe(
        pd.DataFrame(table_data),
        column_config={
            "Kaufpreis": st.column_config.NumberColumn(format="%d €"),
            "Invest (EK)": st.column_config.NumberColumn(format="%d €"),
            "Rendite": st.column_config.NumberColumn(format="%.2f %%"),
            "Ø CF (Nach St.)": st.column_config.NumberColumn(format="%d €"),
            "Gewinn (10J)": st.column_config.NumberColumn(format="%d €"), # <--- FORMATIERUNG
        },
        use_container_width=True, hide_index=True
    )

# --- PAGE 2: DETAIL ---
else:
    st.title("🔍 Detail-Ansicht & Bearbeiten")
    sorted_keys = sorted(OBJEKTE.keys(), key=lambda x: OBJEKTE[x].get("Archiviert", False))
    sel = st.selectbox("Objekt wählen:", sorted_keys)
    obj_data = OBJEKTE[sel]
    
    if obj_data.get("Archiviert"):
        st.warning("⚠️ Dieses Objekt liegt im Archiv.")

    # STECKBRIEF
    st.markdown("### 📍 Objekt-Steckbrief")
    kp_val = obj_data["Kaufpreis"]
    nk_quote = obj_data["Nebenkosten_Quote"]
    invest_ek = kp_val * nk_quote + obj_data.get("Renovierung", 0) + obj_data.get("Heizung_Puffer", 0)

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Adresse:** {obj_data.get('Adresse', '-')}")
            st.markdown(f"**Größe:** {obj_data['qm']} m² | {obj_data['zimmer']} Zi.")
            st.markdown(f"**Energie:** {obj_data.get('Energie_Info', '-')}")
        with c2:
            st.markdown(f"**Hausgeld:** {obj_data.get('Hausgeld_Gesamt', 0)} €")
            st.markdown(f"**Status:** {obj_data.get('Status', '-')}")
        st.markdown("---")
        st.metric("Invest (Eigenkapital)", f"{invest_ek:,.0f} €")

    # LINK & PDF
    cl, cp = st.columns(2)
    if obj_data.get("Link"):
        cl.markdown(f"↗ [Zum Inserat]({obj_data['Link']})")
    if obj_data.get("PDF_Path") and os.path.exists(obj_data["PDF_Path"]):
        with open(obj_data["PDF_Path"], "rb") as f:
            cp.download_button("📄 Exposé PDF", f, "Expose.pdf")

    # KALKULATION
    st.markdown("---")
    st.header("📊 Live-Kalkulation")
    
    with st.expander("⚙️ Parameter anpassen", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        curr_z = obj_data.get("Zins_Indiv", g_zins)
        new_z = c1.slider("Zins (%)", 1.0, 6.0, curr_z*100, 0.1, key=f"z_{sel}") / 100
        # Speichern bei Änderung
        if new_z != curr_z:
            OBJEKTE[sel]["Zins_Indiv"] = new_z
            save_data(OBJEKTE)
            st.rerun()

    res = calculate_investment(sel, OBJEKTE[sel], g_zins, g_tilg, g_steuer)
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Ø CF (Nach Steuer)", f"{res['Avg_CF']:,.0f} €")
    k2.metric("EKR (10J)", f"{res['CAGR']:.2f} %")
    k3.metric("Miete/m²", f"{(res['Detail'][0]['Miete (mtl.)']/obj_data['qm']):.2f} €")
    k4.metric("Gewinn (10J)", f"{res['Gewinn_10J']:,.0f} €")

    st.subheader("📋 10-Jahres-Plan")
    df_full = pd.DataFrame(res["Detail"])
    st.dataframe(
        df_full.head(10)[["Laufzeit", "Miete (mtl.)", "CF (vor Steuer)", "CF (nach Steuer)", "Restschuld"]]
        .style.format("{:,.2f} €" if "Miete" in df_full else "{:,.0f} €"),
        use_container_width=True, hide_index=True
    )
    
    with st.expander("🔮 Ausblick: Jahr 15 & 20"):
        c1, c2 = st.columns(2)
        d15 = res["Detail"][14]
        c1.write(f"**Jahr 15:** Restschuld {d15['Restschuld']:,.0f} € | Equity {d15['Equity']:,.0f} €")
        d20 = res["Detail"][19]
        c2.write(f"**Jahr 20:** Restschuld {d20['Restschuld']:,.0f} € | Equity {d20['Equity']:,.0f} €")

    # BEARBEITEN
    st.markdown("---")
    st.header("⚙️ Daten ändern")
    with st.expander("📝 Stammdaten & Status bearbeiten"):
        c1, c2 = st.columns(2)
        is_archived = c1.checkbox("❌ Archivieren", value=obj_data.get("Archiviert", False))
        n_kp = c2.number_input("Kaufpreis", value=float(obj_data["Kaufpreis"]))
        n_link = st.text_input("Link", value=obj_data.get("Link", ""))
        n_case = st.text_area("Strategie", value=obj_data.get("Summary_Case", ""))
        
        if st.button("💾 Speichern"):
            OBJEKTE[sel].update({"Archiviert": is_archived, "Kaufpreis": n_kp, "Link": n_link, "Summary_Case": n_case})
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
