import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# 1. 페이지 설정
st.set_page_config(
    page_title="작전주 헌터",
    page_icon="🦅",
    layout="centered" # 모바일 보기 편하게 중앙 정렬
)

# --- 스타일(CSS) 적용: 제목 폰트, 카드 디자인 등 ---
st.markdown("""
    <style>
    /* 제목 스타일 */
    .main-title {
        font-size: 1.8rem !important;
        color: #1E1E1E;
        text-align: center;
        font-weight: 800;
        margin-bottom: 5px;
    }
    .sub-text {
        font-size: 0.9rem;
        color: #555;
        text-align: center;
        margin-bottom: 20px;
    }
    /* 카드 스타일 (네모 박스) */
    .stock-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* 수익률 뱃지 */
    .profit-badge-plus {
        background-color: #ffebee;
        color: #d32f2f;
        padding: 4px 8px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .profit-badge-minus {
        background-color: #e3f2fd;
        color: #1976d2;
        padding: 4px 8px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    </style>
""", unsafe_allow_html=True)

# 2. 데이터 로드 함수
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
    except Exception as e:
        return pd.DataFrame()

def clean_data(df):
    if df.empty: return df
    
    # 수익률 숫자 변환
    if '수익률(%)' in df.columns:
        df['수익률_숫자'] = df['수익률(%)'].astype(str).str.replace('%', '').str.replace(',', '')
        df['수익률_숫자'] = pd.to_numeric(df['수익률_숫자'], errors='coerce').fillna(0)
    
    # 현재가 숫자 변환
    if '현재가(Live)' in df.columns:
        df['현재가_표시'] = df['현재가(Live)'].astype(str).str.replace('코드확인', '-')
        
    return df

# --- 메인 화면 시작 ---

# 예쁜 제목 (HTML 사용)
st.markdown('<div class="main-title">🦅 작전주 헌터 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">세력의 매집 흔적을 실시간으로 추적합니다</div>', unsafe_allow_html=True)

# 새로고침 버튼 (작게)
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    if st.button('🔄 최신 데이터 불러오기', use_container_width=True):
        st.cache_data.clear()

raw_df = load_data()

if raw_df is not None and not raw_df.empty:
    df = clean_data(raw_df)
    
    # 최신순 정렬
    if '탐색일' in df.columns:
        df = df.sort_values(by='탐색일', ascending=False)

    # 📊 상단 요약 (심플하게)
    total = len(df)
    today_cnt = len(df[df['탐색일'] == df['탐색일'].iloc[0]])
    
    # 요약 지표를 예쁘게 보여주기
    m1, m2, m3 = st.columns(3)
    m1.metric("총 포착", f"{total}건")
    m2.metric("오늘 발견", f"{today_cnt}건")
    m3.metric("최근 업데이트", df['탐색일'].iloc[0][5:]) # 월-일만 표시

    st.divider()

    # 🃏 카드 뷰 (모바일 최적화의 핵심!)
    st.subheader("📋 포착 종목 리스트")
    
    for index, row in df.iterrows():
        # 수익률에 따라 색상 결정
        profit = row['수익률_숫자']
        profit_str = row['수익률(%)']
        price = row['현재가_표시']
        
        # 숫자에 콤마 찍기 (보기 좋게)
        try:
            price_fmt = f"{int(str(price).replace(',','')): ,}원"
        except:
            price_fmt = price

        badge_class = "profit-badge-plus" if profit >= 0 else "profit-badge-minus"
        emoji = "🔥" if profit >= 5 else ("💧" if profit < 0 else "😐")
        
        # Streamlit 컨테이너를 카드처럼 사용
        with st.container(border=True):
            # 첫째 줄: 종목명 + 수익률 뱃지
            c1, c2 = st.columns([7, 3])
            with c1:
                st.markdown(f"**{row['종목명']}** <span style='color:#888; font-size:0.8em;'>({row['코드']})</span>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<span class='{badge_class}'>{profit_str}</span>", unsafe_allow_html=True)
            
            # 둘째 줄: 현재가 + 포착이유
            st.markdown(f"**현재가:** {price_fmt}")
            st.markdown(f"**포착이유:** {row['거래량급증']}") # 여기 텔레그램 이유가 없어서 거래량급증으로 대체
            
            # 셋째 줄: 날짜 (작게)
            st.caption(f"탐색일: {row['탐색일']} | 포착가: {row['포착가']}원")

    # 📄 엑셀 원본 보기 (필요한 사람만 열어서 보게 함)
    with st.expander("📊 전체 데이터 엑셀형태로 보기 (클릭)"):
        st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.info("데이터를 불러오는 중입니다... (잠시 후 다시 시도해주세요)")
