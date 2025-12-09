import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import FinanceDataReader as fdr
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(
    page_title="작전주 헌터",
    page_icon="🦅",
    layout="centered"
)

# --- 스타일(CSS) ---
st.markdown("""
    <style>
    .main-title { font-size: 1.8rem !important; color: #1E1E1E; text-align: center; font-weight: 800; margin-bottom: 5px; }
    .sub-text { font-size: 0.9rem; color: #555; text-align: center; margin-bottom: 20px; }
    .profit-badge-plus { background-color: #ffebee; color: #d32f2f; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    .profit-badge-minus { background-color: #e3f2fd; color: #1976d2; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    /* 차트 여백 최소화 */
    .stChart { margin-top: -20px; }
    </style>
""", unsafe_allow_html=True)

# 2. 데이터 로드 함수 (구글 시트)
@st.cache_data(ttl=60)
def load_data():
    try:
        json_key = os.environ.get('GOOGLE_JSON')
        if not json_key: return None
        creds_dict = json.loads(json_key)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sh = client.open("작전주_포착_로그")
        worksheet = sh.sheet1
        data = worksheet.get_all_values()
        if len(data) < 2: return pd.DataFrame()
        header = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=header)
        return df
    except:
        return pd.DataFrame()

# 3. 미니 차트용 데이터 가져오기 (30일치)
@st.cache_data(ttl=3600) # 1시간마다 캐싱 (너무 자주 부르면 느려짐)
def get_mini_chart_data(code):
    try:
        # 최근 30일 데이터 조회
        end_date = datetime.now()
        start_date = end_date - timedelta(days=40) # 휴장일 고려 넉넉히
        df = fdr.DataReader(code, start=start_date)
        return df['Close'].tail(30) # 진짜 30개만 자름
    except:
        return None

def clean_data(df):
    if df.empty: return df
    if '수익률(%)' in df.columns:
        df['수익률_숫자'] = df['수익률(%)'].astype(str).str.replace('%', '').str.replace(',', '')
        df['수익률_숫자'] = pd.to_numeric(df['수익률_숫자'], errors='coerce').fillna(0)
    if '현재가(Live)' in df.columns:
        df['현재가_표시'] = df['현재가(Live)'].astype(str).str.replace('코드확인', '-')
    return df

# --- 메인 화면 ---

st.markdown('<div class="main-title">🦅 작전주 헌터 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">세력의 매집 흔적과 추세를 추적합니다</div>', unsafe_allow_html=True)

col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    if st.button('🔄 최신 데이터 새로고침', use_container_width=True):
        st.cache_data.clear()

raw_df = load_data()

if raw_df is not None and not raw_df.empty:
    df = clean_data(raw_df)
    if '탐색일' in df.columns:
        df = df.sort_values(by='탐색일', ascending=False)

    # 상단 요약
    total = len(df)
    today_cnt = len(df[df['탐색일'] == df['탐색일'].iloc[0]])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("총 포착", f"{total}건")
    m2.metric("오늘 발견", f"{today_cnt}건")
    m3.metric("업데이트", df['탐색일'].iloc[0][5:])

    st.divider()

    st.subheader("📋 포착 종목 리스트")
    
    for index, row in df.iterrows():
        profit = row['수익률_숫자']
        profit_str = row['수익률(%)']
        price = row['현재가_표시']
        code = row['코드'].replace("'", "") # '005930 -> 005930 변환
        
        try:
            price_fmt = f"{int(str(price).replace(',','')): ,}원"
        except:
            price_fmt = price

        badge_class = "profit-badge-plus" if profit >= 0 else "profit-badge-minus"
        
        # --- 카드 디자인 (좌:정보 / 우:차트) ---
        with st.container(border=True):
            col_info, col_chart = st.columns([1.8, 1.2]) # 왼쪽(글씨) 넓게, 오른쪽(차트) 좁게
            
            # [왼쪽] 텍스트 정보
            with col_info:
                st.markdown(f"**{row['종목명']}** <span style='color:#888; font-size:0.8em;'>({code})</span> <span class='{badge_class}'>{profit_str}</span>", unsafe_allow_html=True)
                st.markdown(f"<div style='margin-top:5px; font-size:0.95em; font-weight:bold;'>{price_fmt}</div>", unsafe_allow_html=True)
                st.caption(f"{row['탐색일']} 포착 | {row['거래량급증']}")
            
            # [오른쪽] 미니 차트 (Streamlit 내장 차트)
            with col_chart:
                chart_data = get_mini_chart_data(code)
                if chart_data is not None and not chart_data.empty:
                    # 차트 그리기 (빨강:상승, 파랑:하락)
                    color = '#d32f2f' if profit >= 0 else '#1976d2'
                    st.line_chart(chart_data, height=80, use_container_width=True) # 높이를 80으로 작게 설정
                else:
                    st.caption("차트 로딩 실패")

    with st.expander("📊 전체 데이터 엑셀형태로 보기"):
        st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.info("데이터를 불러오는 중입니다... (잠시 후 다시 시도해주세요)")
