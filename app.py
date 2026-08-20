import streamlit as st
import json
import os
import openai
import pandas as pd
import altair as alt
import datetime
import traceback

# --- 1. 초기 설정 및 함수 정의 ---
st.set_page_config(page_title="AI 금융 교육 챗봇", page_icon="🤖", layout="centered")

try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("'.streamlit/secrets.toml' 파일에 OpenAI API 키를 설정해주세요.")
    st.stop()

@st.cache_data
def load_json_data(file_path):
    target_path = file_path if os.path.exists(file_path) else os.path.join("data", file_path)
    if not os.path.exists(target_path): return None
    with open(target_path, 'r', encoding='utf-8') as f: return json.load(f)

@st.cache_data
def load_markdown_content(file_path):
    clean_path = file_path.lstrip('/')
    target_path = clean_path if os.path.exists(clean_path) else os.path.join("curriculum", clean_path)
    if not os.path.exists(target_path): return "학습 콘텐츠를 준비 중입니다."
    with open(target_path, 'r', encoding='utf-8') as f: return f.read()

def initialize_session_state():
    if 'current_page' not in st.session_state: st.session_state.current_page = 'home'
    if 'level' not in st.session_state: st.session_state.level = None
    if 'lt_current_q' not in st.session_state: st.session_state.lt_current_q = 0
    if 'lt_score' not in st.session_state: st.session_state.lt_score = 0
    if 'lt_user_answers' not in st.session_state: st.session_state.lt_user_answers = []
    if 'user_id' not in st.session_state: st.session_state.user_id = None
    if 'current_week' not in st.session_state: st.session_state.current_week = 1
    if 'current_day' not in st.session_state: st.session_state.current_day = 1
    if 'dq_current_q' not in st.session_state: st.session_state.dq_current_q = 0
    if 'dq_score' not in st.session_state: st.session_state.dq_score = 0
    if 'all_incorrect_answers' not in st.session_state: st.session_state.all_incorrect_answers = []
    if 'chat_messages' not in st.session_state: st.session_state.chat_messages = []

# --- 2. 페이지 렌더링 ---
def render_home_page():
    st.title("AI 금융 교육 챗봇 🤖")
    user_id = st.text_input("학습자 ID (고유값을 입력하세요)")
    if st.button("학습 시작하기", type="primary", use_container_width=True):
        if not user_id: st.warning("ID를 입력하세요!")
        else:
            st.session_state.user_id = user_id
            try:
                from streamlit_gsheets import GSheetsConnection
                conn = st.connection("gsheets", type=GSheetsConnection)
                df = conn.read(worksheet="시트1")
                if "ID" in df.columns and user_id in df["ID"].values.astype(str):
                    st.session_state.current_page = 'result'
                else:
                    st.session_state.current_page = 'survey'
            except Exception as e: st.error(f"데이터 확인 오류: {e}")
            st.rerun()

def render_survey_page():
    st.title("📋 참여자 정보 입력")
    with st.form("survey_form"):
        gender = st.radio("성별", ["남성", "여성"], horizontal=True)
        grade = st.selectbox("학년 및 상태", ["1학년", "2학년", "3학년", "4학년", "졸업생", "기타"])
        if st.form_submit_button("레벨 테스트 시작"):
            st.session_state.user_gender = gender
            st.session_state.user_grade = grade
            st.session_state.current_page = 'level_test'
            st.rerun()

def render_level_test_page():
    level_test_data = load_json_data('level_test_questions.json')
    total_q, q_index = len(level_test_data), st.session_state.lt_current_q
    st.title("금융 지식 레벨 테스트")
    st.progress(q_index / total_q)
    q_data = level_test_data[q_index]
    st.subheader(f"Q{q_index + 1}. {q_data['question']}")
    with st.form(key=f"lt_{q_index}"):
        user_answer = st.radio("답:", q_data["options"], index=None)
        if st.form_submit_button("제출"):
            if user_answer:
                if user_answer == q_data["answer"]: st.session_state.lt_score += 1
                st.session_state.lt_user_answers.append({"q": q_data["question"], "sel": user_answer, "ans": q_data["answer"], "correct": (user_answer == q_data["answer"]), "category": q_data.get("category", "기본")})
                if q_index < total_q - 1: st.session_state.lt_current_q += 1
                else: st.session_state.current_page = 'result'
                st.rerun()

def render_result_page():
    score = st.session_state.lt_score
    total_q = len(load_json_data('level_test_questions.json'))
    display_level = "고급자" if (score/total_q) >= 0.8 else ("중급자" if (score/total_q) >= 0.5 else "초급자")
    st.session_state.level = "advanced" if display_level == "고급자" else ("intermediate" if display_level == "중급자" else "beginner")

    if 'db_saved' not in st.session_state:
        try:
            from streamlit_gsheets import GSheetsConnection
            conn = st.connection("gsheets", type=GSheetsConnection)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{
                "ID": st.session_state.user_id,
                "일시": now,
                "성별": st.session_state.get("user_gender", "미상"),
                "학년": st.session_state.get("user_grade", "미상"),
                "점수": score,
                "배치수준": display_level # F열 배치
            }])
            existing_data = conn.read(worksheet="시트1", ttl=5).dropna(how="all")
            conn.update(worksheet="시트1", data=pd.concat([existing_data, new_row], ignore_index=True))
        except Exception as e:
            st.error(f"저장 실패: {type(e).__name__}")
            st.code(traceback.format_exc())
        st.session_state.db_saved = True
    
    st.title("테스트 결과")
    st.write(f"당신의 레벨은 **'{display_level}'** 입니다.")
    if st.button("학습 시작하기"):
        st.session_state.current_page = 'learning'
        st.rerun()

# --- 3. 메인 로직 ---
def main():
    initialize_session_state()
    pages = {'home': render_home_page, 'survey': render_survey_page, 'level_test': render_level_test_page, 'result': render_result_page}
    pages.get(st.session_state.current_page, render_home_page)()

if __name__ == "__main__":
    main()
