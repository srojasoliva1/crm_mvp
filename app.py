import streamlit as st
import pandas as pd
import gspread
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime

st.set_page_config(page_title="CRM Custom Operations", layout="wide")

# ==========================================
# 1. CONFIGURACIÓN DE ENLACES
# ==========================================
# Reemplaza con las URLs reales de tus 3 Google Sheets
URL_OPERACION = "https://docs.google.com/spreadsheets/d/16mbhnSOg75H_WcSsWPblLpcslnu7v4VYEaQlyBLnR8A/edit"
URL_CALIDAD = "https://docs.google.com/spreadsheets/d/1ij82h2c7WpO7-2LvNwuwLGexpp080wNkIKUH8IJY6KE/edit"
URL_REGISTROS = "https://docs.google.com/spreadsheets/d/1peujLDzEu9tEyWFrEiZfGb9d_SrgmJ5gTb0bTYmCG6U/edit"

# Reemplaza con la ID de la carpeta raíz de SOPs en Google Drive
SOP_FOLDER_ID = "1VzG0XA2pxxGzxfUiCcabwm6nBZjRhtdY"

# ==========================================
# 2. CONEXIÓN OAUTH 2.0 (LOCAL Y NUBE)
# ==========================================
@st.cache_resource
def obtener_cliente_oauth():
    # Detecta si se está ejecutando en Streamlit Cloud con Secrets
    if "authorized_user" in st.secrets:
        secret_data = st.secrets["authorized_user"]
        user_info = json.loads(secret_data) if isinstance(secret_data, str) else dict(secret_data)
        creds = Credentials.from_authorized_user_info(user_info)
        return gspread.authorize(creds)
    
    # Si se ejecuta en tu computadora local
    return gspread.oauth(
        credentials_filename='oauth_credentials.json',
        authorized_user_filename='authorized_user.json'
    )

try:
    gc = obtener_cliente_oauth()
    creds = gc.auth
except Exception as e:
    st.error(f"Error en la autenticación OAuth: {e}")
    st.stop()

# ==========================================
# 3. NAVEGACIÓN Y MENÚ LATERAL
# ==========================================
st.sidebar.title("🏢 CRM Operativo")
agente = st.sidebar.selectbox("Agente Activo:", ["María Gómez", "Juan Pérez", "Carlos Pérez"])

opcion = st.sidebar.radio("Módulos del Sistema", [
    "1. Experts & Calls",
    "2. Groups & Evaluations",
    "3. My Performance (CSAT/QA)",
    "4. Attendance & Shift Log",
    "5. Churn & Issue Reporting",
    "6. SOP Library"
])

# ==========================================
# MÓDULO 1: EXPERTS & CALLS
# ==========================================
if opcion == "1. Experts & Calls":
    st.header("📞 Experts Directory & Call Logging")
    sheet_op = gc.open_by_url(URL_OPERACION)
    df_expertos = pd.DataFrame(sheet_op.worksheet("experts").get_all_records())
    
    mis_expertos = df_expertos[df_expertos["agent"] == agente] if not df_expertos.empty else pd.DataFrame()
    
    st.subheader("Assigned Experts")
    if not mis_expertos.empty:
        st.dataframe(
            mis_expertos[["expert_id", "expert_name", "status", "phone", "country", "city", "program"]], 
            use_container_width=True
        )
    else:
        st.info("No experts assigned to this agent.")
        
    st.subheader("Log Call")
    with st.form("form_call"):
        expert_list = mis_expertos["expert_name"].tolist() if not mis_expertos.empty else ["No Experts Available"]
        experto_sel = st.selectbox("Expert Called:", expert_list)
        resultado = st.selectbox("Call Result:", ["Successful call", "No answer", "Follow-up needed", "Requested Churn"])
        notas = st.text_area("Call Notes:")
        
        if st.form_submit_button("Save Call Record"):
            sheet_op.worksheet("log_calls").append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                experto_sel,
                agente,
                resultado,
                notas
            ])
            st.success("✅ Interaction saved to Google Drive.")

# ==========================================
# MÓDULO 2: GROUPS & EVALUATIONS
# ==========================================
elif opcion == "2. Groups & Evaluations":
    st.header("👥 Active Groups & Weekly Evaluations")
    sheet_op = gc.open_by_url(URL_OPERACION)
    df_grupos = pd.DataFrame(sheet_op.worksheet("active_groups").get_all_records())
    
    mis_grupos = df_grupos[df_grupos["agent"] == agente] if not df_grupos.empty else pd.DataFrame()
    
    st.subheader("My Active Groups")
    if not mis_grupos.empty:
        st.dataframe(mis_grupos, use_container_width=True)
    else:
        st.info("No active groups assigned.")

    st.markdown("---")
    st.subheader("⭐ Weekly Group & Expert Evaluation")
    
    df_exp = pd.DataFrame(sheet_op.worksheet("experts").get_all_records())
    mis_exp = df_exp[df_exp["agent"] == agente] if not df_exp.empty else pd.DataFrame()
    
    with st.form("form_weekly_eval"):
        c1, c2, c3 = st.columns(3)
        with c1:
            grp_sel = st.selectbox("Group ID:", mis_grupos["group_id"].unique().tolist() if not mis_grupos.empty else ["N/A"])
        with c2:
            exp_sel = st.selectbox("Expert ID:", mis_exp["expert_id"].unique().tolist() if not mis_exp.empty else ["N/A"])
        with c3:
            wk_sel = st.selectbox("Week:", ["Week 1", "Week 2", "Week 3", "Week 4"])
            
        st.markdown("**Evaluation Rubric (0 - 10):**")
        r1, r2, r3 = st.columns(3)
        with r1:
            scroll = st.number_input("Scroll de Seguridad:", min_value=0.0, max_value=10.0, step=0.5, value=5.0)
        with r2:
            msg = st.number_input("Envío de Mensajes:", min_value=0.0, max_value=10.0, step=0.5, value=5.0)
        with r3:
            therm = st.number_input("Termómetro de Dudas:", min_value=0.0, max_value=10.0, step=0.5, value=5.0)
            
        total_eval = scroll + msg + therm
        st.metric("Total Evaluation Score", f"{total_eval:.1f} / 30.0")
        notes = st.text_area("Notes / Feedback:")
        
        if st.form_submit_button("Submit Evaluation"):
            sheet_op.worksheet("expert_evaluations").append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                agente, grp_sel, exp_sel, wk_sel, scroll, msg, therm, total_eval, notes
            ])
            st.success(f"✅ Evaluation recorded for Group {grp_sel} / Expert {exp_sel}.")

# ==========================================
# MÓDULO 3: MY PERFORMANCE (CSAT/QA)
# ==========================================
elif opcion == "3. My Performance (CSAT/QA)":
    st.header("📊 Performance & Quality Audits")
    sheet_qa = gc.open_by_url(URL_CALIDAD)
    
    df_csat = pd.DataFrame(sheet_qa.worksheet("encuestas_csat").get_all_records())
    df_audits = pd.DataFrame(sheet_qa.worksheet("auditorias_qa").get_all_records())
    
    mis_csat = df_csat[df_csat["assigned_agent"] == agente] if not df_csat.empty else pd.DataFrame()
    mis_audits = df_audits[df_audits["agent"] == agente] if not df_audits.empty else pd.DataFrame()
    
    c1, c2, c3 = st.columns(3)
    avg_csat = pd.to_numeric(mis_csat["csat_score"], errors='coerce').mean() if not mis_csat.empty else 0
    avg_nps = pd.to_numeric(mis_csat["nps_score"], errors='coerce').mean() if not mis_csat.empty else 0
    avg_qa = pd.to_numeric(mis_audits["qa_score"], errors='coerce').mean() if not mis_audits.empty else 0
    
    c1.metric("Average CSAT (1-5)", f"{avg_csat:.2f}")
    c2.metric("Average NPS Score (0-10)", f"{avg_nps:.1f}")
    c3.metric("Average QA Audit Score", f"{avg_qa:.1f}%")
    
    st.markdown("---")
    tab_csat, tab_qa = st.tabs(["Driver CSAT Surveys", "QA Audits"])
    
    with tab_csat:
        st.dataframe(mis_csat, use_container_width=True)
    with tab_qa:
        st.dataframe(mis_audits, use_container_width=True)

# ==========================================
# MÓDULO 4: ATTENDANCE & SHIFT LOG
# ==========================================
elif opcion == "4. Attendance & Shift Log":
    st.header("⏱️ Shift & Activity Log")
    sheet_reg = gc.open_by_url(URL_REGISTROS)
    
    c_in, c_out = st.columns(2)
    with c_in:
        if st.button("🟢 Check-in"):
            sheet_reg.worksheet("jornada_asistencia").append_row([
                datetime.now().strftime("%Y-%m-%d"), agente, datetime.now().strftime("%H:%M:%S"), "", ""
            ])
            st.success("Check-in registered.")
            
    with c_out:
        report = st.text_area("Daily Activity Summary:")
        if st.button("🔴 Check-out"):
            sheet_reg.worksheet("jornada_asistencia").append_row([
                datetime.now().strftime("%Y-%m-%d"), agente, "", datetime.now().strftime("%H:%M:%S"), report
            ])
            st.success("Check-out saved.")

# ==========================================
# MÓDULO 5: CHURN & ISSUE REPORTING
# ==========================================
elif opcion == "5. Churn & Issue Reporting":
    st.header("⚠️ Reporting Center")
    sheet_reg = gc.open_by_url(URL_OPERACION)
    
    tab_churn, tab_issues = st.tabs(["Report Churn", "Report Issue"])
    
    with tab_churn:
        st.subheader("Driver Churn Report")
        with st.form("form_churn"):
            driver_id = st.text_input("Driver ID:")
            group_id = st.text_input("Group ID:")
            exit_reason = st.selectbox("Exit Reason:", ["Voluntary Departure", "Inactivity", "Operational Removal", "Other"])
            retention = st.selectbox("Retention Process Attempted?:", ["Yes", "No"])
            main_reason = st.selectbox("Main Exit Reason:", ["Earnings", "Technical Issues", "Personal Reasons", "Other"])
            add_info = st.text_area("Additional Info:")
            evidence = st.text_input("Evidence URL (Drive Link):")
            
            if st.form_submit_button("Submit Churn Report"):
                sheet_reg.worksheet("churn_reports").append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    driver_id, group_id, exit_reason, retention, main_reason, add_info, evidence, agente
                ])
                st.warning(f"Churn registered for Driver {driver_id}.")

    with tab_issues:
        st.subheader("Operational Issue Report")
        with st.form("form_issues"):
            grp_issue = st.text_input("Group ID:")
            exp_issue = st.text_input("Expert ID:")
            issue_type = st.selectbox("Issue Type:", ["Platform Error", "Assignment Issue", "Expert Conflict", "Other"])
            desc = st.text_area("Description:")
            evid = st.text_input("Evidence URL:")
            
            if st.form_submit_button("Submit Issue Report"):
                sheet_reg.worksheet("issues").append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    agente, grp_issue, exp_issue, issue_type, desc, evid
                ])
                st.success("Issue reported successfully.")

# ==========================================
# MÓDULO 6: SOP LIBRARY
# ==========================================
elif opcion == "6. SOP Library":
    st.header("📚 Standard Operating Procedures (SOPs)")
    
    sops_tree = escanear_sops_por_categoria(SOP_FOLDER_ID)
    
    if sops_tree:
        categoria_sel = st.selectbox("Select Category:", list(sops_tree.keys()))
        
        documentos_cat = sops_tree[categoria_sel]
        if documentos_cat:
            doc_nombre = st.selectbox("Select SOP Document:", list(documentos_cat.keys()))
            doc_id = documentos_cat[doc_nombre]
            
            if st.button("Display SOP Content"):
                with st.spinner("Fetching document from Google Docs..."):
                    contenido = leer_google_doc(doc_id)
                    st.markdown("---")
                    st.info(contenido)
        else:
            st.info("No SOP documents found in this category.")
    else:
        st.warning("No categories or SOP documents found in Google Drive.")