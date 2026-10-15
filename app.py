import streamlit as st
import gspread

# Načítanie údajov zo Streamlit Secrets
credentials = st.secrets["gcp_service_account"]

# Prihlásenie pomocou informácií z účtu
gc = gspread.service_account_from_dict(credentials)

# Otvorenie tabuľky podľa názvu
sh = gc.open("Názov Vašej Google Tabuľky")
import streamlit as st
import pandas as pd
import gspread

# 1. Nastavenie vzhľadu aplikácie
st.set_page_config(page_title="Sklad Doskového Materiálu", page_icon="📦", layout="wide")

st.title("📦 Interný sklad - Doskový materiál")
st.markdown("Uprav množstvo priamo v bunke tabuľky a na konci klikni na **Uložiť zmeny**.")

# Názov tvojej Google tabuľky
NAZOV_TABULKY = "app-skuska" 

# Definícia stĺpcov
NAZOV_PRVEHO_STLPCA = "Názov dekoru / Farba"
PREDVOLENE_STLPCE = [NAZOV_PRVEHO_STLPCA, "18mm (ks)", "25mm (ks)", "38mm (ks)", "16mm (ks)"]

# 2. Prepojenie na Google Sheets cez gspread
try:
    gc = gspread.service_account(filename="kluc.json")
    sh = gc.open(NAZOV_TABULKY)
    worksheet = sh.get_worksheet(0)
    
    data = worksheet.get_all_records()
    
    if len(data) == 0:
        df = pd.DataFrame(columns=PREDVOLENE_STLPCE)
    else:
        df = pd.DataFrame(data)
        
        # Ošetrenie názvu prvého stĺpca
        if len(df.columns) > 0 and df.columns[0] != NAZOV_PRVEHO_STLPCA:
            df = df.rename(columns={df.columns[0]: NAZOV_PRVEHO_STLPCA})
            
        if "16mm (ks)" not in df.columns:
            df["16mm (ks)"] = 0
except Exception as e:
    st.error(f"Nepodarilo sa pripojiť ku Google Sheets. Chyba: {e}")
    df = pd.DataFrame([
        {NAZOV_PRVEHO_STLPCA: "Biela Hladká", "18mm (ks)": 15, "25mm (ks)": 4, "38mm (ks)": 0, "16mm (ks)": 0},
        {NAZOV_PRVEHO_STLPCA: "Dub Antik", "18mm (ks)": 8, "25mm (ks)": 12, "38mm (ks)": 2, "16mm (ks)": 5},
        {NAZOV_PRVEHO_STLPCA: "Antracit", "18mm (ks)": 22, "25mm (ks)": 0, "38mm (ks)": 5, "16mm (ks)": 10},
    ])

# Prevedieme stĺpec s názvami na čistý text
df[NAZOV_PRVEHO_STLPCA] = df[NAZOV_PRVEHO_STLPCA].astype(str)

# Presné zoradenie stĺpcov
poradie_stlpcoov = [NAZOV_PRVEHO_STLPCA, "18mm (ks)", "25mm (ks)", "38mm (ks)", "16mm (ks)"]
df = df.reindex(columns=poradie_stlpcoov)

# Uistíme sa, že všetky číselné stĺpce sú brané ako čísla
for col in ["18mm (ks)", "25mm (ks)", "38mm (ks)", "16mm (ks)"]:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# 3. Bočný panel na pridanie úplne nového dekoru
st.sidebar.header("➕ Pridať nový dekor")
novy_nazov = st.sidebar.text_input(f"{NAZOV_PRVEHO_STLPCA}:")
hrubka_18 = st.sidebar.number_input("18mm (ks)", min_value=0, value=0)
hrubka_25 = st.sidebar.number_input("25mm (ks)", min_value=0, value=0)
hrubka_38 = st.sidebar.number_input("38mm (ks)", min_value=0, value=0)
hrubka_16 = st.sidebar.number_input("16mm (ks)", min_value=0, value=0)

if st.sidebar.button("Pridať do zoznamu"):
    if novy_nazov and novy_nazov not in df[NAZOV_PRVEHO_STLPCA].values:
        # Pridáme nový riadok priamo do DataFrame bez použitia indexu
        novy_riadok = pd.DataFrame([{
            NAZOV_PRVEHO_STLPCA: str(novy_nazov),
            "18mm (ks)": hrubka_18,
            "25mm (ks)": hrubka_25,
            "38mm (ks)": hrubka_38,
            "16mm (ks)": hrubka_16
        }])
        df = pd.concat([df, novy_riadok], ignore_index=True)
        
        # Hneď to uložíme do Google Sheets, aby sa tabuľka aktualizovala
        try:
            worksheet.clear()
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            st.sidebar.success(f"Dekor '{novy_nazov}' bol úspešne pridaný a uložený!")
            st.rerun()
        except Exception as save_err:
            st.sidebar.error(f"Nepodarilo sa uložiť nový dekor: {save_err}")
    elif novy_nazov in df[NAZOV_PRVEHO_STLPCA].values:
        st.sidebar.warning("Tento dekor už v zozname existuje.")
    else:
        st.sidebar.error("Zadajte názov dekoru.")

# 4. Rýchle full-text vyhľadávanie dekoru
st.subheader("🔍 Vyhľadávanie v sklade")
hladany_text = st.text_input("Zadaj názov dekoru alebo jeho časť:", value="")

# Filtrujeme priamo stĺpec, nie index
if hladany_text:
    df_na_zobrazenie = df[df[NAZOV_PRVEHO_STLPCA].str.contains(hladany_text, case=False, na=False)].copy()
else:
    df_na_zobrazenie = df.copy()

# 5. Interaktívna úprava dát (Tabuľku zobrazujeme BEZ indexu, čo uľahčuje prepisovanie všetkých buniek)
st.subheader("📊 Aktuálny stav zásob")
upraveny_df = st.data_editor(
    df_na_zobrazenie,
    use_container_width=True,
    num_rows="dynamic",
    key="sklad_editor"
)

# 6. Uloženie zmien späť do Google Sheets
if st.button("💾 Uložiť zmeny", type="primary"):
    try:
        # KĽÚČOVÁ ZMENA: Ak sme filtrovali, zlúčime zmeny na základe názvu dekoru
        if hladany_text:
            # Prejdeme upravené riadky a prepíšeme ich v hlavnom df
            for _, row in upraveny_df.iterrows():
                dekor = row[NAZOV_PRVEHO_STLPCA]
                df.loc[df[NAZOV_PRVEHO_STLPCA] == dekor, poradie_stlpcoov] = row[poradie_stlpcoov].values
        else:
            # Ak sa nefiltrovalo, zoberieme rovno celé upravené dáta
            df = upraveny_df
            
        # Očistíme prázdne riadky, ktoré by mohol používateľ omylom vytvoriť na konci tabuľky
        df = df[df[NAZOV_PRVEHO_STLPCA].str.strip() != ""]
        
        # Prevedieme číselné stĺpce pre istotu na int pred odoslaním
        for col in ["18mm (ks)", "25mm (ks)", "38mm (ks)", "16mm (ks)"]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        # Vymažeme starý obsah hárku a nahráme kompletne nové čisté dáta
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.success("Všetky zmeny boli úspešne a bezpečne uložené do Google Sheets!")
        st.rerun()
    except Exception as e:
        st.error(f"Zmeny sa nepodarilo uložiť. Chyba: {e}")
