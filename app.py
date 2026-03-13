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
    
    # Secretsから辞書形式で取得
    conf = st.secrets["gcp_service_account"].to_dict()
    
    # 【重要】鍵の文字列を徹底的にクリーニングする処理
    if "private_key" in conf:
        pk = conf["private_key"]
        # 表示上の \n だけでなく、実際の改行コードや前後の空白、余計なダブルクォーテーションをすべて取り除く
        pk = pk.replace("\\n", "\n").replace('"', '').strip()
        conf["private_key"] = pk

    # 認証実行
    credentials = Credentials.from_service_account_info(conf, scopes=scope)
    gc = gspread.authorize(credentials)
    
    # スプレッドシート接続
    sh = gc.open_by_key(st.secrets["spreadsheet"]["key"])
    # シート名「transport_log」が正しいか確認してください
    worksheet = sh.worksheet("transport_log")

except Exception as e:
    # 詳細な原因を表示させる
    st.error(f"接続エラーが発生しました: {e}")
    st.info("Secretsのprivate_keyが正しく貼り付けられているか、またはスプレッドシートのIDが正しいか確認してください。")
    st.stop()

# ログイン機能
if "password_correct" not in st.session_state:
    st.title("🛡️ ログイン")
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
with st.form("input_form", clear_on_submit=True):
    st.subheader("新しいデータを登録")
    date = st.date_input("利用日", datetime.now())
    category = st.selectbox("項目", ["交通費", "臨時コーチ依頼料", "備品購入", "その他"])
    amount = st.number_input("金額", min_value=0, step=1)
    desc = st.text_area("備考（任意）")
    
    submit = st.form_submit_button("スプレッドシートに保存")
    
    if submit:
        try:
            now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            worksheet.append_row([now, str(date), category, amount, desc])
            st.success("✅ スプレッドシートへ保存が完了しました！")
        except Exception as e:
            st.error(f"❌ 保存に失敗しました: {e}")

st.markdown("---")

# 履歴表示ボタン
if st.button("📊 履歴を表示"):
    try:
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("表示できるデータがありません。")
    except Exception as e:
        st.error(f"履歴の取得に失敗しました: {e}")
