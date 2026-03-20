import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import os
from streamlit_cookies_manager import EncryptedCookieManager
from streamlit_drawable_canvas import st_canvas
import base64
import time

# ページ設定
st.set_page_config(page_title="KSC経費申請管理ツール", layout="wide")

# --- 1. クッキー（ログイン保持）の設定 ---
cookies = EncryptedCookieManager(password="ksc_secure_password_2026_kuma")
if not cookies.ready():
    st.stop()

def check_auth():
    auth_status = cookies.get("auth_status")
    saved_user = cookies.get("current_user")
    expire_time_str = cookies.get("login_expire")
    is_valid = False
    if auth_status == "ok" and expire_time_str:
        try:
            expire_time = datetime.fromisoformat(expire_time_str)
            if datetime.now() < expire_time: is_valid = True
        except: pass
    if is_valid:
        st.session_state["password_correct"] = True
        if saved_user: st.session_state["current_user"] = saved_user
        return True
    st.title("🛡️ ログイン")
    user_id = st.text_input("ログインID")
    password = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if user_id == "KSC" and password == "kuma2019":
            expire_date = datetime.now() + timedelta(hours=2)
            cookies["auth_status"] = "ok"
            cookies["login_expire"] = expire_date.isoformat()
            cookies.save()
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("IDまたはパスワードが正しくありません。")
    return False

if not check_auth(): st.stop()

if "current_user" not in st.session_state or not st.session_state["current_user"]:
    st.title("👤 氏名選択")
    name_list = ["加藤", "瀬野", "平", "稲垣", "富井", "新美", "細川", "島田"]
    selected_user = st.selectbox("あなたの氏名を選択してください", name_list)
    if st.button("決定"):
        st.session_state["current_user"] = selected_user
        cookies["current_user"] = selected_user
        cookies.save()
        st.rerun()
    st.stop()

# --- 2. Google Sheets 認証設定 ---
@st.cache_resource
def get_gspread_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    else:
        key_file = "ksc-cash-app-7b96a6f1774a.json" if os.path.exists("ksc-cash-app-7b96a6f1774a.json") else "credentials.json"
        credentials = Credentials.from_service_account_file(key_file, scopes=scope)
    return gspread.authorize(credentials)

try:
    gc = get_gspread_client()
    sh = gc.open_by_key("1yVYajQm6KeaoppB3KMaHismS-95NWxGGfie9DhDEEgk")
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 3. サイドバー ---
st.sidebar.write(f"ログイン中の氏名: **{st.session_state['current_user']}**")
if st.sidebar.button("ユーザー変更"):
    cookies["current_user"] = ""
    cookies.save(); st.session_state["current_user"] = None; st.rerun()

if st.sidebar.button("ログアウト"):
    cookies["auth_status"] = ""; cookies["current_user"] = ""; cookies["login_expire"] = ""
    cookies.save(); st.session_state["password_correct"] = False; st.session_state["current_user"] = None; st.rerun()

st.title("KSC経費申請管理ツール")
form_type = st.radio("申請書種別を選択してください", ["KSC 交通費清算書", "KSC 日当清算書 兼 受領書"], horizontal=True)
st.markdown("---")

# 申請保存ロジック (A. 交通費)
if form_type == "KSC 交通費清算書":
    st.header("🚗 KSC 交通費清算書")
    with st.form("transport_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("日付", datetime.now()); dest = st.text_input("行先")
        with col2:
            purp = st.text_input("目的"); amt = st.number_input("金額 (円)", min_value=0, step=1)
        rem = st.text_area("備考")
        if st.form_submit_button("スプレッドシートに保存"):
            try:
                ws = sh.worksheet("transport_log")
                ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state["current_user"], str(date), dest, purp, int(amt), rem])
                st.cache_data.clear()
                st.success("データを保存しました。入力内容をクリアします。")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"保存失敗: {e}")

# 申請保存ロジック (B. 日当)
else:
    st.header("📋 KSC 日当清算書 兼 受領書")
    if "form_key_suffix" not in st.session_state:
        st.session_state["form_key_suffix"] = time.time()

    with st.form("allowance_form", clear_on_submit=True):
        dt = st.date_input("日時", datetime.now())
        cont = st.text_area("臨時コーチ依頼内容")
        amt = st.number_input("金額 (円)", min_value=0, step=1)
        c_c = st.checkbox("確認 (コーチ)")
        c_t = st.checkbox("確認 (臨時コーチ)")
        
        st.write("🖋️ **臨時コーチ署名**")
        sig_name = st.text_input("確認(臨時コーチ氏名)を入力してください")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1)", stroke_width=2, stroke_color="#000",
            background_color="#fff", height=120, width=300, drawing_mode="freedraw", 
            key=f"canvas_{st.session_state['form_key_suffix']}"
        )
        
        if st.form_submit_button("スプレッドシートに保存"):
            try:
                sig_b64 = ""
                if c_t and canvas_result.image_data is not None:
                    from PIL import Image
                    import io
                    img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    sig_b64 = base64.b64encode(buffered.getvalue()).decode()

                ws = sh.worksheet("allowance_log")
                ws.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state["current_user"], 
                    str(dt), cont, int(amt), "済" if c_c else "未", sig_name, sig_b64
                ])
                st.cache_data.clear()
                st.session_state["form_key_suffix"] = time.time()
                st.success("データを保存しました。入力内容をクリアします。")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"保存失敗: {e}")

# --- 4. 履歴表示・印刷・修正 ---
@st.cache_data(ttl=60)
def fetch_records(sheet_name):
    ws = sh.worksheet(sheet_name)
    return ws.get_all_records()

st.markdown("---")
st.subheader(f"📊 {st.session_state['current_user']} 様の申請済み一覧")

try:
    current_ws_name = "transport_log" if form_type == "KSC 交通費清算書" else "allowance_log"
    all_records = fetch_records(current_ws_name)
    
    if all_records:
        df_all = pd.DataFrame(all_records)
        df_all['row_idx'] = range(2, len(df_all) + 2)
        df_user = df_all[df_all["氏名"] == st.session_state["current_user"]].copy()
        
        if not df_user.empty:
            date_col = '日付' if form_type == "KSC 交通費清算書" else '日時'
            df_user[date_col] = pd.to_datetime(df_user[date_col])
            
            col_d1, col_d2 = st.columns(2)
            with col_d1: start_date = st.date_input("開始日", df_user[date_col].min().date())
            with col_d2: end_date = st.date_input("終了日", df_user[date_col].max().date())
            mask = (df_user[date_col].dt.date >= start_date) & (df_user[date_col].dt.date <= end_date)
            df_filtered = df_user.loc[mask].sort_values(by=date_col, ascending=False)
            
            display_df = df_filtered.drop(columns=['row_idx'])
            if '確認(臨時コーチ署名)' in display_df.columns:
                display_df = display_df.drop(columns=['確認(臨時コーチ署名)'])
            display_df[date_col] = display_df[date_col].dt.strftime('%Y-%m-%d')
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # --- 印刷機能 ---
            p_col1, p_col2 = st.columns(2)
            btn_coach = p_col1.button("🖨️ コーチ用PDF印刷" if form_type == "KSC 日当清算書 兼 受領書" else "🖨️ PDF印刷プレビューを表示")
            btn_temp = False
            if form_type == "KSC 日当清算書 兼 受領書":
                btn_temp = p_col2.button("🖨️ 臨時コーチ用PDF印刷")

            if btn_coach or btn_temp:
                if btn_temp:
                    print_df = df_user.sort_values(by='row_idx', ascending=False).head(1)
                else:
                    print_df = df_filtered

                rows_html = ""
                if form_type == "KSC 日当清算書 兼 受領書":
                    headers_html = "<tr><th>申請日時</th><th>氏名</th><th>日時</th><th>臨時コーチ<br>依頼内容</th><th>金額</th><th>確認<br>(コーチ)</th><th>確認<br>(臨時コーチ氏名)</th><th>確認<br>(臨時コーチ署名)</th></tr>"
                else:
                    headers = display_df.columns.tolist()
                    headers_html = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
                
                rows_html += headers_html
                for _, row in print_df.iterrows():
                    cells = [row[date_col].strftime('%Y-%m-%d') if c == date_col else row[c] for c in display_df.columns]
                    row_html = "".join(f"<td>{c}</td>" for c in cells)
                    if form_type == "KSC 日当清算書 兼 受領書":
                        sig = row.get('確認(臨時コーチ署名)', '')
                        # 修正：署名がはみ出ないようpaddingを入れ、max-heightをセルの高さ(50px)より小さい38pxに設定
                        sig_img = f'<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; padding:2px;"><img src="data:image/png;base64,{sig}" style="max-width:95%; max-height:38px; object-fit:contain;"></div>' if sig else ""
                        row_html += f'<td style="padding: 0; overflow: hidden;">{sig_img}</td>'
                    rows_html += f"<tr>{row_html}</tr>"

                print_script = f"""
                <html><head><style>
                    @media print {{ @page {{ margin: 10mm; }} }}
                    body {{ font-family: sans-serif; padding:10px; font-size: 10px; color: #333; }}
                    h2 {{ text-align:center; font-size: 16px; margin-bottom: 20px; }}
                    table {{ width:100%; border-collapse:collapse; table-layout: fixed; }}
                    th, td {{ border:1px solid #000; padding:4px 2px; text-align:center; height: 50px; word-wrap: break-word; vertical-align: middle; }}
                    th {{ background-color: #f2f2f2; font-size: 9px; line-height: 1.4; }}
                    td {{ font-size: 9px; line-height: 1.2; }}
                </style></head>
                <body>
                    <h2>経費精算書 ({form_type})</h2>
                    <table>{rows_html}</table>
                    <script>setTimeout(function() {{ window.print(); }}, 500);</script>
                </body></html>
                """
                st.components.v1.html(print_script, height=600, scrolling=True)

            st.markdown("---")
            st.write("🔧 個別データの修正・削除")
            ws_to_edit = sh.worksheet(current_ws_name)
            for idx, row in df_filtered.iterrows():
                row_date_str = row[date_col].strftime('%Y-%m-%d')
                with st.expander(f"📌 {row_date_str} - {row.get('行先') or row.get('臨時コーチ依頼内容')} ({row['金額']}円)"):
                    cols = st.columns([1, 1, 8])
                    if cols[1].button("削除", key=f"del_{idx}"):
                        ws_to_edit.delete_rows(int(row['row_idx']))
                        st.cache_data.clear(); st.rerun()
                    if cols[0].button("修正", key=f"edit_{idx}"):
                        st.session_state[f"editing_{idx}"] = True

                    if st.session_state.get(f"editing_{idx}"):
                        with st.form(f"edit_form_{idx}"):
                            if form_type == "KSC 交通費清算書":
                                n_d = st.date_input("日付", row[date_col]); n_ds = st.text_input("行先", row['行先'])
                                n_p = st.text_input("目的", row['目的']); n_a = st.number_input("金額", value=int(row['金額']))
                                n_r = st.text_area("備考", row['備考'])
                                if st.form_submit_button("更新"):
                                    ws_to_edit.update(f"A{row['row_idx']}:G{row['row_idx']}", [[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row['氏名'], str(n_d), n_ds, n_p, int(n_a), n_r]])
                                    st.cache_data.clear(); st.session_state[f"editing_{idx}"] = False; st.rerun()
                            else:
                                n_dt = st.date_input("日時", row[date_col]); n_c = st.text_area("臨時コーチ依頼内容", row['臨時コーチ依頼内容'])
                                n_a = st.number_input("金額", value=int(row['金額']))
                                n_cc = st.checkbox("確認(コーチ)", row['確認(コーチ)']=="済")
                                if st.form_submit_button("更新"):
                                    ws_to_edit.update_cell(row['row_idx'], 3, str(n_dt))
                                    ws_to_edit.update_cell(row['row_idx'], 4, n_c)
                                    ws_to_edit.update_cell(row['row_idx'], 5, int(n_a))
                                    ws_to_edit.update_cell(row['row_idx'], 6, "済" if n_cc else "未")
                                    st.cache_data.clear(); st.session_state[f"editing_{idx}"] = False; st.rerun()
                        if st.button("キャンセル", key=f"cancel_{idx}"):
                            st.session_state[f"editing_{idx}"] = False; st.rerun()
        else: st.info("データがありません。")
except Exception as e: st.error(f"エラー: {e}")
