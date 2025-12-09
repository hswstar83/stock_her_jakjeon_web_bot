import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# 1. 페이지 설정
st.set_page_config(
    page_title="작전주 헌터 대시보드",
    page_icon="📈",
    layout="wide" # 화면을 넓게 씀
)

# 2. 제목 및 설명
st.title("📈 작전주 헌터 : 세력 포착 시스템")
st.markdown("""
매일 **오후 3:40**, 세력의 매집 흔적이 있는 종목을 자동으로 찾아냅니다.
이 데이터는 **구글 시트**와 실시간으로 연동됩니다.
""")

# 3. 구글 시트 데이터 가져오기 (캐싱 기능 사용)
# (매번 새로고침할 때마다 구글에 접속하면 느리니까, 데이터를 잠깐 기억해두는 기능)
@st.cache_data(ttl=60) # 60초마다 갱신
def load_data():
    try:
        # 레일웨이 환경변수에서 키 가져오기
        json_key = os.environ.get('GOOGLE_JSON')
        if not json_key:
            return None

        # 인증 및 연결
        creds_dict = json.loads(json_key)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        # 시트 열기 (이름 정확해야 함!)
        sh = client.open("작전주_포착_로그")
        worksheet = sh.sheet1
        
        # 모든 데이터 가져오기
        data = worksheet.get_all_values()
        
        # 첫 번째 줄은 제목(Header), 나머지는 데이터
        if len(data) < 2:
            return pd.DataFrame() # 데이터가 없으면 빈 표 반환
            
        header = data[0]
        rows = data[1:]
        
        # 데이터 프레임 만들기
        df = pd.DataFrame(rows, columns=header)
        return df

    except Exception as e:
        st.error(f"데이터를 가져오는 중 에러가 발생했습니다: {e}")
        return pd.DataFrame()

# 4. 데이터 로드 및 화면 표시
if st.button('🔄 데이터 새로고침'):
    st.cache_data.clear() # 캐시 비우고 다시 불러오기

df = load_data()

if df is not None and not df.empty:
    # 최신 날짜가 위로 오게 정렬 (A열 '탐색일' 기준 내림차순)
    # 날짜 형식이 문자열이라 정확하지 않을 수 있지만 기본 정렬 시도
    if '탐색일' in df.columns:
        df = df.sort_values(by='탐색일', ascending=False)

    # 몇 개 찾았는지 표시
    st.success(f"총 **{len(df)}**개의 작전주 후보가 포착되었습니다.")

    # 표 그리기
    st.dataframe(
        df, 
        use_container_width=True, # 화면 꽉 차게
        hide_index=True # 0,1,2,3 인덱스 번호 숨기기
    )
else:
    st.warning("아직 포착된 데이터가 없거나, 구글 시트 연결에 실패했습니다.")
    st.info("레일웨이 Variables에 GOOGLE_JSON이 잘 들어있는지 확인해주세요.")
