import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ページ設定
st.set_page_config(page_title="KSC経費管理アプリ", layout="centered")

# --- 認証処理（Secretsから安全に取得） ---
try:
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # 個別に設定した値を辞書にまとめる
    info = {
        "type": st.secrets["GCP_TYPE"],
        "project_id": st.secrets["GCP_PROJECT_ID"],
        "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"],
        "private_key": st.secrets["GCP_PRIVATE_KEY"].replace('\\n', '\n'), # 改行コードを復元
        "client_email": st.secrets["GCP_CLIENT_EMAIL"],
        "client_id": st.secrets["GCP_CLIENT_ID"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{st.secrets['GCP_CLIENT_EMAIL'].replace('@', '%40')}"
    }
    
    credentials = Credentials.from_service_account_info(info, scopes=scope)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(st.secrets["SHEET_KEY"])
    worksheet = sh.worksheet("transport_log")
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# ログイン機能
if "password_correct" not in st.session_state:
    st.title("ログイン")
    user = st.text_input("ユーザー名")
    pw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if user == st.secrets["LOGIN_USER"] and pw == st.secrets["LOGIN_PW"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("認証失敗")
    st.stop()

# メイン画面
st.title("💰 KSC経費管理システム")
with st.form("input_form"):
    date = st.date_input("利用日", datetime.now())
    category = st.selectbox("項目", ["交通費", "臨時コーチ依頼料", "備品購入", "その他"])
    amount = st.number_input("金額", min_value=0, step=1)
    desc = st.text_area("備考")
    if st.form_submit_button("保存"):
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        worksheet.append_row([now, str(date), category, amount, desc])
        st.success("保存完了！")

if st.button("履歴を表示"):
    data = worksheet.get_all_records()
    st.dataframe(pd.DataFrame(data))
