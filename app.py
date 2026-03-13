import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="KSC経費管理アプリ", layout="centered")

try:
    # 認証情報の構築
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    s = st.secrets["gcp_service_account"]
    
    # 秘密鍵の改行を補正
    pk = s["private_key"].replace("\\n", "\n")
    
    info = {
        "type": s["type"],
        "project_id": s["project_id"],
        "private_key_id": s["private_key_id"],
        "private_key": pk,
        "client_email": s["client_email"],
        "client_id": s["client_id"],
        "auth_uri": s["auth_uri"],
        "token_uri": s["token_uri"],
        "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
        "client_x509_cert_url": s["client_x509_cert_url"]
    }
    
    credentials = Credentials.from_service_account_info(info, scopes=scope)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(st.secrets["spreadsheet"]["key"])
    worksheet = sh.worksheet("transport_log")

except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

def check_password():
    if "password_correct" not in st.session_state:
        st.text_input("ユーザー名", key="username")
        st.text_input("パスワード", type="password", key="password")
        if st.button("ログイン"):
            if st.session_state["username"] == st.secrets["login"]["username"] and \
               st.session_state["password"] == st.secrets["login"]["password"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("認証失敗")
        return False
    return True

if check_password():
    st.title("💰 KSC経費管理システム")
    with st.form("expense_form"):
        date = st.date_input("利用日", datetime.now())
        category = st.selectbox("項目", ["交通費", "臨時コーチ依頼料", "備品購入", "その他"])
        amount = st.number_input("金額", min_value=0, step=1)
        description = st.text_area("備考")
        if st.form_submit_button("保存"):
            now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            worksheet.append_row([now, str(date), category, amount, description])
            st.success("保存完了")
