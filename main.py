# streamlit_population_app.py
# Streamlit 앱: 주민등록인구및세대현황(월간) CSV 파일 시각화 (Plotly 버전)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="주민등록인구 시각화", layout="wide")

CSV_PATH = "/mnt/data/202509_202509_주민등록인구및세대현황_월간 (1).csv"

@st.cache_data
def load_data(path):
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            df = pd.read_csv(path, encoding=enc)
            return df
        except Exception:
            continue
    raise ValueError("CSV 파일을 열 수 없습니다. 인코딩이나 경로를 확인하세요.")

try:
    df = load_data(CSV_PATH)
except Exception as e:
    st.error(f"파일 불러오기 실패: {e}")
    st.stop()

st.title("📊 주민등록 인구 및 세대 현황 — 월간 시각화 (Plotly)")

with st.expander("원본 데이터 보기"):
    st.dataframe(df.head(200))

# 컬럼 전처리
df.columns = [c.strip() for c in df.columns]
period_col = None
for cand in ["기간", "연월", "조회년월", "기준연월", "날짜"]:
    if cand in df.columns:
        period_col = cand
        break

if period_col:
    df["기간_parsed"] = pd.to_datetime(df[period_col].astype(str).str[:6], format="%Y%m", errors='coerce')
else:
    df["기간_parsed"] = pd.NaT

col_map = {}
for c in df.columns:
    low = c.lower()
    if "시도" in low or "도" == low:
        col_map['시도'] = c
    if "시군구" in low or "구" in low:
        col_map['시군구'] = c
    if "성별" in low:
        col_map['성별'] = c
    if "연령" in low or "나이" in low:
        col_map['연령대'] = c
    if "인구" in low:
        col_map['인구수'] = c
    if "세대" in low:
        col_map['세대수'] = c

sido_col = col_map.get('시도')
gungu_col = col_map.get('시군구')
sex_col = col_map.get('성별')
age_col = col_map.get('연령대')
pop_col = col_map.get('인구수')
house_col = col_map.get('세대수')

# Sidebar 필터
st.sidebar.header("필터")
if sido_col:
    sido_vals = sorted(df[sido_col].dropna().unique())
    sido = st.sidebar.multiselect("시도 선택", sido_vals, default=sido_vals[:3])
else:
    sido = None

if gungu_col:
    if sido_col and sido:
        gungu_vals = sorted(df[df[sido_col].isin(sido)][gungu_col].dropna().unique())
    else:
        gungu_vals = sorted(df[gungu_col].dropna().unique())
    gungu = st.sidebar.multiselect("시군구 선택", gungu_vals, default=gungu_vals[:5])
else:
    gungu = None

if sex_col:
    sex_vals = sorted(df[sex_col].dropna().unique())
    sex = st.sidebar.multiselect("성별 선택", sex_vals, default=sex_vals)
else:
    sex = None

if df['기간_parsed'].notna().any():
    min_date, max_date = df['기간_parsed'].min(), df['기간_parsed'].max()
    start, end = st.sidebar.date_input("기간 선택", (min_date.date(), max_date.date()))
else:
    start, end = None, None

mask = pd.Series(True, index=df.index)
if sido_col and sido:
    mask &= df[sido_col].isin(sido)
if gungu_col and gungu:
    mask &= df[gungu_col].isin(gungu)
if sex_col and sex:
    mask &= df[sex_col].isin(sex)
if start and end:
    mask &= (df['기간_parsed'] >= pd.to_datetime(start)) & (df['기간_parsed'] <= pd.to_datetime(end))

df_f = df[mask].copy()

# 요약
st.subheader("요약 정보")
if pop_col:
    total_pop = pd.to_numeric(df_f[pop_col], errors='coerce').sum()
    st.metric("총 인구수", f"{int(total_pop):,}")
if house_col:
    total_house = pd.to_numeric(df_f[house_col], errors='coerce').sum()
    st.metric("총 세대수", f"{int(total_house):,}")

# Plotly 시각화
st.subheader("📈 인구 시계열 추이")
if pop_col and '기간_parsed' in df_f.columns:
    ts = df_f.groupby('기간_parsed')[pop_col].apply(lambda s: pd.to_numeric(s, errors='coerce').sum()).reset_index()
    fig = px.line(ts, x='기간_parsed', y=pop_col, markers=True, title='기간별 총 인구수 추이')
    fig.update_layout(xaxis_title='기간', yaxis_title='인구수', template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

st.subheader("👥 연령대 및 성별 분포")
if age_col and pop_col:
    agg = df_f.groupby([age_col, sex_col])[pop_col].apply(lambda s: pd.to_numeric(s, errors='coerce').sum()).reset_index()
    fig = px.bar(agg, x=age_col, y=pop_col, color=sex_col, barmode='group', title='연령대별 성별 인구 분포')
    fig.update_layout(xaxis_title='연령대', yaxis_title='인구수', template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

st.subheader("🏙️ 지역별 인구수 상위 순위")
if pop_col and sido_col:
    rank = df_f.groupby(sido_col)[pop_col].apply(lambda s: pd.to_numeric(s, errors='coerce').sum()).reset_index()
    rank = rank.sort_values(by=pop_col, ascending=False)
    fig = px.bar(rank.head(20), x=sido_col, y=pop_col, title='시도별 인구수 상위 20')
    fig.update_layout(template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

with st.expander("필터된 데이터 다운로드"):
    csv = df_f.to_csv(index=False).encode('utf-8-sig')
    st.download_button("CSV 다운로드", csv, file_name="filtered_population.csv", mime='text/csv')

st.sidebar.markdown("---")
st.sidebar.info("Plotly 기반 인터랙티브 시각화. 필요시 지도 시각화나 인구 밀도 분석 기능도 추가할 수 있습니다.")
