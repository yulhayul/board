import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="전국 고령화 단계구분도 (2026년)", layout="wide")

st.title("전국 시군구별 고령화 단계구분도 (2026년)")

# 데이터 로딩 함수 (캐싱 처리로 속도 최적화)
@st.cache_data
def load_population_data():
    pop_url = "https://raw.githubusercontent.com/first2022-cyber/contents//main/population_ts_yearly_gender.zip"
    
    # 판다스로 zip 압축 파일 바로 읽기 (코드 열을 문자열로 다룸)
    df = pd.read_csv(pop_url, compression='zip', dtype={'코드': str})
    
    # 2026년 데이터만 필터링
    df_2026 = df[df['연도'] == 2026].copy()
    
    # 코드 앞 5자리로 시군구 코드 추출
    df_2026['sigungu_code'] = df_2026['코드'].astype(str).str.zfill(8).str[:5]
    
    # 열 분류 (계_ 로 시작하는 열)
    total_pop_cols = [c for c in df_2026.columns if c.startswith('계_')]
    
    # 65세 이상 열 선택 ('계_65세'부터 '계_100세 이상' 또는 그 이상까지)
    # 나이 숫자를 파악하기 위한 조건 추출
    elderly_cols = []
    for c in total_pop_cols:
        age_str = c.replace('계_', '').replace('세', '').replace(' 이상', '').strip()
        if age_str.isdigit() and int(age_str) >= 65:
            elderly_cols.append(c)
        elif '100세' in c or '100' in c:  # '계_100세 이상' 등 처리
            elderly_cols.append(c)
            
    # 전체 인구 및 65세 이상 인구 합계 계산
    df_2026['전체인구'] = df_2026[total_pop_cols].sum(axis=1)
    df_2026['고령인구'] = df_2026[elderly_cols].sum(axis=1)
    
    # 시군구 코드로 그룹화하여 합산
    sigungu_df = df_2026.groupby('sigungu_code')[['전체인구', '고령인구']].sum().reset_index()
    
    # 고령화율(%) 계산
    sigungu_df['고령화율'] = (sigungu_df['고령인구'] / sigungu_df['전체인구']) * 100
    sigungu_df['고령화율'] = sigungu_df['고령화율'].round(2)
    
    return sigungu_df

@st.cache_data
def load_geojson():
    geojson_url = "https://raw.githubusercontent.com/first2022-cyber/contents//main/sigungu_kr.geojson"
    res = requests.get(geojson_url)
    geojson_data = res.json()
    return geojson_data

with st.spinner("데이터를 불러오는 중입니다..."):
    df_sigungu = load_population_data()
    geojson_data = load_geojson()

# GeoJSON 파일에서 시군구 코드를 기반으로 시군구명 및 시도명을 딕셔너리로 매핑하여 DataFrame에 대입
code_to_name = {}
for feature in geojson_data['features']:
    props = feature['properties']
    code_to_name[str(props['코드'])] = f"{props['시도']} {props['시군구']}"

df_sigungu['시군구명'] = df_sigungu['sigungu_code'].map(code_to_name).fillna("알 수 없음")

# Plotly Choropleth 생성
fig = px.choropleth_mapbox(
    df_sigungu,
    geojson=geojson_data,
    locations='sigungu_code',
    featureidkey='properties.코드',
    color='고령화율',
    color_continuous_scale="Reds",
    range_color=(0, df_sigungu['고령화율'].max()),
    mapbox_style="white-bg",  # 타일 지도 없이 백그라운드를 흰색으로
    center={"lat": 36.3, "lon": 127.8},
    zoom=6.2,
    hover_name='시군구명',
    hover_data={'sigungu_code': False, '고령화율': ':.2f%'},
    labels={'고령화율': '고령화율(%)'}
)

# 지도 외곽선 및 레이아웃 설정
fig.update_traces(marker_line_width=0.5, marker_line_color='gray')
fig.update_layout(
    margin={"r": 0, "t": 30, "l": 0, "b": 0},
    height=750
)

# Streamlit에 그래프 표시
st.plotly_chart(fig, use_container_width=True)

# 요약 정보 표시
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("분석 대상 시군구 수", f"{len(df_sigungu)} 개")
with col2:
    st.metric("최고 고령화율 지역", f"{df_sigungu.loc[df_sigungu['고령화율'].idxmax()]['시군구명']} ({df_sigungu['고령화율'].max()}%)")
with col3:
    st.metric("최저 고령화율 지역", f"{df_sigungu.loc[df_sigungu['고령화율'].idxmin()]['시군구명']} ({df_sigungu['고령화율'].min()}%)")
