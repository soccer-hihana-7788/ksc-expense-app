import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="KSC経費管理アプリ", layout="centered")

# 2. Google Sheets 認証設定
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Secretsから辞書形式で取得し、改行コードの不具合を修正
conf = st.secrets["gcp_service_account"].to_dict()
if "private_key" in conf:
    # 貼り付け時に \n がエスケープされてしまう問題を解決
    conf["private_key"] = conf["private_key"].replace("\\n", "\n")

try:
    credentials = Credentials.from_service_account_info(conf, scopes=scope)
    gc = gspread.authorize(credentials)

    # スプレッドシートをIDで開く
    SP_SHEET_KEY = st.secrets["spreadsheet"]["key"]
    sh = gc.open_by_key(SP_SHEET_KEY)
    
    # シート名の指定（スプレッドシートのタブ名と一致させてください）
    worksheet = sh.worksheet("transport_log")

except Exception as e:
    st.error(f"認証またはスプレッドシートの接続でエラーが発生しました: {e}")
    st.stop()

# 3. ログイン機能
def check_password():
    def password_entered():
        if st.session_state["username"] == st.secrets["login"]["username"] and \
           st.session_state["password"] == st.secrets["login"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("ユーザー名", key="username")
        st.text_input("パスワード", type="password", key="password")
        st.button("ログイン", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("ユーザー名", key="username")
        st.text_input("パスワード", type="password", key="password")
        st.button("ログイン", on_click=password_entered)
        st.error("ユーザー名またはパスワードが違います")
        return False
    else:
        return True

# 4. メイン画面
if check_password():
    st.title("💰 KSC経費管理システム")
    
    with st.form("expense_form"):
        date = st.date_input("利用日", datetime.now())
        category = st.selectbox("項目", ["交通費", "臨時コーチ依頼料", "備品購入", "その他"])
        amount = st.number_input("金額", min_value=0, step=1)
        description = st.text_area("備考")
        
        submitted = st.form_submit_button("スプレッドシートに保存")
        
        if submitted:
            try:
                # スプレッドシートに書き込み
                now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                worksheet.append_row([now, str(date), category, amount, description])
                st.success("データを保存しました！")
            except Exception as e:
                st.error(f"保存に失敗しました: {e}")

    # 履歴の表示
    if st.button("履歴を表示"):
        try:
            data = worksheet.get_all_records()
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df)
            else:
                st.info("データがありません。")
        except Exception as e:
            st.error(f"履歴の取得に失敗しました: {e}")
