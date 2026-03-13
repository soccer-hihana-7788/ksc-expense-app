import streamlit as st
import pandas as pd
from gspread_streamlit import gspread_connect
from datetime import datetime

# --- 1. 認証機能 (Secrets管理) ---
def check_password():
    def password_guessed():
        # Streamlit SecretsからID/PWを取得 (設定方法は後述)
        if st.session_state["password"] == st.secrets["login"]["password"] and \
           st.session_state["username"] == st.secrets["login"]["username"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("KSC試合管理ツール ログイン")
        st.text_input("ログインID", key="username")
        st.text_input("パスワード", type="password", key="password")
        st.button("ログイン", on_click=password_guessed)
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("ログインID", key="username")
        st.text_input("パスワード", type="password", key="password")
        st.button("ログイン", on_click=password_guessed)
        st.error("IDまたはパスワードが正しくありません")
        return False
    return True

# --- 2. Googleスプレッドシート接続 ---
def save_to_sheets(sheet_name, data_df):
    try:
        # st.secretsの認証情報を使用して接続
        conn = gspread_connect(st.secrets["gcp_service_account"])
        sh = conn.open_by_key(st.secrets["spreadsheet"]["key"])
        worksheet = sh.worksheet(sheet_name)
        
        # データの整形（空行を除外して申請日時を追加）
        valid_data = data_df[data_df.iloc[:, 1] != ""].copy()
        if not valid_data.empty:
            valid_data.insert(0, "申請日時", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.append_rows(valid_data.values.tolist())
            return True
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        return False

# --- 3. メインアプリ画面 ---
if check_password():
    st.sidebar.title("メニュー")
    page = st.sidebar.radio("申請書種別", ["交通費清算書", "日当清算書 兼 受領書", "過去ログ閲覧"])

    # A. 交通費清算書 [cite: 10]
    if page == "交通費清算書":
        st.header("KSC 交通費清算書")
        
        # 15行の空枠作成 [cite: 17-33]
        df_init = pd.DataFrame(
            [{"日付": datetime.now().strftime("%Y-%m-%d"), "行先": "", "目的": "", "金額": 0, "備考": ""} for _ in range(15)]
        )
        # データエディタ (手動入力・カレンダー対応) [cite: 35, 36]
        edited_df = st.data_editor(df_init, num_rows="fixed", hide_index=True)
        
        # 合計金額の自動計算
        total = edited_df["金額"].sum()
        st.markdown(f"### **合計金額: ¥{total:,}**")

        if st.button("スプレッドシートに保存"):
            if save_to_sheets("transport_log", edited_df):
                st.success("交通費データを保存しました！")

    # B. 日当清算書 兼 受領書 [cite: 38]
    elif page == "日当清算書 兼 受領書":
        st.header("KSC 日当清算書 兼 受領書")
        
        df_allowance = pd.DataFrame(
            [{"日時": datetime.now().strftime("%Y-%m-%d"), "依頼内容": "", "金額": 0, "確認(コーチ)": False, "確認(臨時)": False} for _ in range(15)]
        )
        # チェックボックス込みのエディタ [cite: 96, 97]
        edited_allowance = st.data_editor(df_allowance, num_rows="fixed", hide_index=True)
        
        total_allw = edited_allowance["金額"].sum()
        st.markdown(f"### **合計金額: ¥{total_allw:,}**")

        if st.button("スプレッドシートに保存"):
            if save_to_sheets("allowance_log", edited_allowance):
                st.success("日当データを保存しました！")

    # C. 過去ログ閲覧
    elif page == "過去ログ閲覧":
        st.header("過去の申請実績")
        st.info("スプレッドシートからデータを読み込んで表示します（実装予定）")