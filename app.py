import streamlit as st
import json
import os
import openai
import pandas as pd
import altair as alt

# --- 1. 초기 설정 및 함수 정의 ---
st.set_page_config(page_title="AI 금융 교육 챗봇", page_icon="🤖", layout="centered")

try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("'.streamlit/secrets.toml' 파일에 OpenAI API 키를 정확히 설정해주세요.")
    st.stop()

@st.cache_data
def load_json_data(file_path):
    if not os.path.exists(file_path): return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

@st.cache_data
def load_markdown_content(file_path):
    if not os.path.exists(file_path): return "학습 콘텐츠를 준비 중입니다."
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def initialize_session_state():
    if 'current_page' not in st.session_state: st.session_state.current_page = 'home'
    if 'level' not in st.session_state: st.session_state.level = None
    if 'lt_current_q' not in st.session_state: st.session_state.lt_current_q = 0
    if 'lt_score' not in st.session_state: st.session_state.lt_score = 0
    if 'lt_user_answers' not in st.session_state: st.session_state.lt_user_answers = []
    
    if 'current_week' not in st.session_state: st.session_state.current_week = 1
    if 'current_day' not in st.session_state: st.session_state.current_day = 1
    if 'dq_current_q' not in st.session_state: st.session_state.dq_current_q = 0
    if 'dq_total_q' not in st.session_state: st.session_state.dq_total_q = 0
    if 'dq_score' not in st.session_state: st.session_state.dq_score = 0
    if 'all_incorrect_answers' not in st.session_state: st.session_state.all_incorrect_answers = []
    if 'chat_messages' not in st.session_state: st.session_state.chat_messages = []

# --- 2. 페이지 렌더링 함수들 ---
def render_home_page():
    st.title("AI 금융 교육 챗봇 🤖")
    st.markdown("---")
    st.subheader("금융 지식, AI와 함께 쉽고 재미있게!")
    st.write("먼저 간단한 레벨 테스트를 통해 당신의 금융 지식 수준을 확인하고, 맞춤형 학습 계획을 설계해 보세요.")
    if st.button("레벨 테스트 시작하기", type="primary", use_container_width=True):
        st.session_state.lt_current_q, st.session_state.lt_score, st.session_state.lt_user_answers = 0, 0, []
        st.session_state.current_page = 'level_test'
        st.rerun()

def render_level_test_page():
    level_test_data = load_json_data('data/level_test_questions.json')
    if not level_test_data: st.error("레벨 테스트 문제 파일을 찾을 수 없습니다."); return
    
    total_q, q_index = len(level_test_data), st.session_state.lt_current_q
    st.title("금융 지식 레벨 테스트")
    st.progress(q_index / total_q, text=f"진행률: {q_index}/{total_q}")
    
    question_data = level_test_data[q_index]
    st.subheader(f"Q{q_index + 1}. {question_data['question']}")
    
    with st.form(key=f"lt_form_{q_index}"):
        user_answer = st.radio("답:", question_data["options"], index=None)
        if st.form_submit_button("제출", use_container_width=True):
            if user_answer:
                is_correct = (user_answer == question_data["answer"])
                if is_correct: st.session_state.lt_score += 1
                # [수정됨] 카테고리 데이터 함께 저장
                st.session_state.lt_user_answers.append({
                    "q": question_data["question"], 
                    "sel": user_answer, 
                    "ans": question_data["answer"], 
                    "correct": is_correct,
                    "category": question_data.get("category", "기본")
                })
                
                if q_index < total_q - 1: st.session_state.lt_current_q += 1
                else: st.session_state.current_page = 'result'
                st.rerun()
            else: st.warning("답을 선택해주세요!")

def render_result_page():
    score, total_q = st.session_state.lt_score, len(load_json_data('data/level_test_questions.json'))
    percentage = (score / total_q) * 100
    
    st.title("레벨 테스트 결과")

    if percentage >= 80: display_level, folder = "고급자", "advanced"
    elif percentage >= 50: display_level, folder = "중급자", "intermediate"
    else: display_level, folder = "초급자", "beginner"
    
    st.session_state.level = folder
    if display_level == "고급자": st.balloons()
    
    st.subheader(f"당신의 금융 레벨은 **'{display_level}'** 입니다.")
    st.progress(percentage / 100, text=f"전체 정답률: {percentage:.1f}% ({score}/{total_q})")
    st.markdown("---")
    
    # [1번 기능 추가] 영역별 초개인화 대시보드 시각화
    st.subheader("📊 영역별 지식 성취도 분석")
    cat_data = {}
    for ans in st.session_state.lt_user_answers:
        cat = ans['category']
        if cat not in cat_data: cat_data[cat] = {'correct': 0, 'total': 0}
        cat_data[cat]['total'] += 1
        if ans['correct']: cat_data[cat]['correct'] += 1
            
    df = pd.DataFrame([
        {"영역": k, "정답률(%)": (v['correct']/v['total'])*100} 
        for k, v in cat_data.items()
    ])
    
    chart = alt.Chart(df).mark_bar(color='#4C78A8').encode(
        x=alt.X('정답률(%):Q', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y('영역:N', sort='-x'),
        tooltip=['영역', '정답률(%)']
    ).properties(height=250)
    st.altair_chart(chart, use_container_width=True)
    
    with st.expander("오답 노트 확인하기"):
        incorrects = [ans for ans in st.session_state.lt_user_answers if not ans['correct']]
        if not incorrects: st.success("모든 문제를 맞혔습니다! 🥳")
        else:
            for ans in incorrects:
                st.error(f"[{ans['category']}] Q. {ans['q']}\n\n- 나의 답: {ans['sel']}\n- 정답: {ans['ans']}")
    
    if st.button("나의 맞춤 학습 시작하기", type="primary", use_container_width=True):
        st.session_state.current_page = 'learning'
        st.rerun()

def render_learning_page():
    level, week, day = st.session_state.level, st.session_state.current_week, st.session_state.current_day
    content = load_markdown_content(f"/{level}/w{week}d{day}_content.md")

    st.title(f"[{level.capitalize()}] {week}주차 {day}일차 학습")
    with st.container(height=300):
        st.markdown(content)
    st.markdown("---")
    st.subheader("무엇이든 물어보세요! AI 튜터 💬")

    # [2번 기능 추가] 학습자의 오답 기록을 모아 프롬프트에 주입 (Context 확장)
    lt_incorrects = [ans['q'] for ans in st.session_state.lt_user_answers if not ans['correct']]
    dq_incorrects = [ans['question'] for ans in st.session_state.all_incorrect_answers]
    all_weaknesses = list(set(lt_incorrects + dq_incorrects))
    
    weakness_context = ""
    if all_weaknesses:
        weakness_context = "\n\n[학습자 취약점 분석]\n이 학생은 다음 개념들에 관한 문제에서 오답을 기록했습니다:\n- " + "\n- ".join(all_weaknesses) + "\n\n(지시사항: 답변 시 위 취약 개념과 연관된 내용이 있다면 더 친절하게 비유를 들어 설명하고, 학생 수준에 맞춰 눈높이를 낮춰주세요.)"

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("오늘 학습 내용에 대해 질문해보세요..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("AI 튜터가 답변을 생각하고 있어요..."):
                system_prompt = f"당신은 대학생 금융 교육 전문가입니다. 아래 학습 내용을 기반으로만 답변해주세요.\n\n--- 학습 내용 ---\n{content}\n--------------------{weakness_context}"
                try:
                    response = openai.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}])
                    ai_response = response.choices[0].message.content
                except Exception as e: ai_response = f"API 요청 오류: {e}"
                st.markdown(ai_response)
        st.session_state.chat_messages.append({"role": "assistant", "content": ai_response})

    st.markdown("---")
    if content != "학습 콘텐츠를 준비 중입니다.":
        if st.button("학습 완료! 퀴즈 풀기", type="primary", use_container_width=True):
            st.session_state.dq_current_q, st.session_state.dq_score = 0, 0
            st.session_state.current_page = 'daily_quiz'
            st.rerun()

def render_daily_quiz_page():
    level, week, day = st.session_state.level, st.session_state.current_week, st.session_state.current_day
    quiz_data = load_json_data(f"{level}/w{week}d{day}_quiz.json")

    st.title(f"[{level.capitalize()}] {week}주차 {day}일차 복습 퀴즈 📝")
    if not quiz_data: st.error("퀴즈 데이터를 찾을 수 없습니다."); return

    total_q, q_index = len(quiz_data), st.session_state.dq_current_q
    st.session_state.dq_total_q = total_q

    st.progress(q_index / total_q, text=f"퀴즈 진행률: {q_index}/{total_q}")
    q_data = quiz_data[q_index]
    st.subheader(f"Q{q_index + 1}. {q_data['question']}")
    
    with st.form(key=f"dq_form_{q_index}"):
        user_answer = st.radio("답:", q_data["options"], index=None)
        if st.form_submit_button("제출", use_container_width=True):
            if user_answer:
                is_correct = (user_answer == q_data["answer"])
                if is_correct: st.session_state.dq_score += 1
                else: 
                    if q_data not in st.session_state.all_incorrect_answers:
                        st.session_state.all_incorrect_answers.append(q_data)
                
                if q_index < total_q - 1: st.session_state.dq_current_q += 1
                else: st.session_state.current_page = 'quiz_result'
                st.rerun()
            else: st.warning("답을 선택해주세요!")

def render_quiz_result_page():
    week, day = st.session_state.current_week, st.session_state.current_day
    st.title(f"{week}주차 {day}일차 학습 완료! 🎉")
    st.success("오늘의 학습과 퀴즈를 모두 마쳤습니다.")
    st.metric(label="퀴즈 결과", value=f"{st.session_state.dq_score} / {st.session_state.dq_total_q} 점")
    st.markdown("---")

    is_last_day = (week == 4 and day == 5)
    if is_last_day:
        if st.button("4주 완성! 최종 복습 하러가기", type="primary", use_container_width=True):
            st.session_state.current_page = 'final_review'
            st.rerun()
    else:
        if st.button("다음 차시 학습하기", type="primary", use_container_width=True):
            if st.session_state.current_day < 5: st.session_state.current_day += 1
            elif st.session_state.current_week < 4:
                st.session_state.current_week += 1
                st.session_state.current_day = 1
            st.session_state.chat_messages = []
            st.session_state.current_page = 'learning'
            st.rerun()

def render_final_review_page():
    st.title("총정리: 오답 다시 풀기 🧠")
    st.write("4주간의 학습 중 틀렸던 모든 문제들을 다시 풀어보는 최종 복습 시간입니다.")
    st.markdown("---")
    
    incorrect_qs = st.session_state.all_incorrect_answers
    if not incorrect_qs:
        st.success("대단합니다! 4주간의 퀴즈에서 틀린 문제가 하나도 없어요. 🏆")
        st.balloons()
    else:
        for i, q_data in enumerate(incorrect_qs):
            st.subheader(f"오답 {i + 1}. {q_data['question']}")
            st.info(f"정답: **{q_data['answer']}**")
            st.markdown("---")
            
    if st.button("모든 과정 초기화하고 처음으로 돌아가기", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

def main():
    initialize_session_state()
    pages = {
        'home': render_home_page, 'level_test': render_level_test_page,
        'result': render_result_page, 'learning': render_learning_page,
        'daily_quiz': render_daily_quiz_page, 'quiz_result': render_quiz_result_page,
        'final_review': render_final_review_page
    }
    page_to_render = pages.get(st.session_state.current_page, render_home_page)
    page_to_render()

if __name__ == "__main__":
    main()
