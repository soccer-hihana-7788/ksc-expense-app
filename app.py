import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ページ設定
st.set_page_config(page_title="KSC経費管理アプリ", layout="centered")

# Google Sheets 認証設定
try:
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    conf = st.secrets["gcp_service_account"].to_dict()
    
    # 秘密鍵の改行補正（これがないとPEMエラーになります）
    if "private_key" in conf:
        conf["private_key"] = conf["private_key"].replace("\\n", "\n")

    credentials = Credentials.from_service_account_info(conf, scopes=scope)
    gc = gspread.authorize(credentials)
    
    # スプレッドシート接続
    sh = gc.open_by_key(st.secrets["spreadsheet"]["key"])
    # ワークシート名が正しいか確認してください（例: "シート1"など）
    worksheet = sh.worksheet("transport_log")

except Exception as e:
    st.error(f"接続エラーが発生しました。Secretsの設定を確認してください: {e}")
    st.stop()

# ログイン機能
if "password_correct" not in st.session_state:
    st.title("ログイン")
    user = st.text_input("ユーザー名")
    pw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if user == st.secrets["login"]["username"] and pw == st.secrets["login"]["password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("ユーザー名またはパスワードが正しくありません")
    st.stop()

# メイン画面
st.title("💰 KSC経費管理システム")
with st.form("input_form"):
    date = st.date_input("利用日", datetime.now())
    category = st.selectbox("項目", ["交通費", "臨時コーチ依頼料", "備品購入", "その他"])
    amount = st.number_input("金額", min_value=0, step=1)
    desc = st.text_area("備考")
    if st.form_submit_button("スプレッドシートに保存"):
        try:
            now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            worksheet.append_row([now, str(date), category, amount, desc])
            st.success("スプレッドシートに保存しました！")
        except Exception as e:
            st.error(f"保存失敗: {e}")

if st.button("履歴を表示"):
    try:
        data = worksheet.get_all_records()
        st.dataframe(pd.DataFrame(data))
    except Exception as e:
        st.error(f"取得失敗: {e}")
