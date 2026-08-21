import streamlit as st
import json
import os
import openai
import pandas as 
import altair as alt
import datetime
import traceback


# =========================================================
# 1. 초기 설정 및 함수 정의
# =========================================================

st.set_page_config(
    page_title="AI 금융 교육 챗봇",
    page_icon="🤖",
    layout="centered"
)


# ---------------------------------------------------------
# OpenAI API 설정
# ---------------------------------------------------------

try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]

except (FileNotFoundError, KeyError):
    st.error(
        "'.streamlit/secrets.toml' 파일에 "
        "OPENAI_API_KEY를 설정해주세요."
    )
    st.stop()


# ---------------------------------------------------------
# JSON 데이터 불러오기
# ---------------------------------------------------------

@st.cache_data
def load_json_data(file_path):

    target_path = (
        file_path
        if os.path.exists(file_path)
        else os.path.join("data", file_path)
    )

    if not os.path.exists(target_path):
        return None

    with open(
        target_path,
        'r',
        encoding='utf-8'
    ) as f:

        return json.load(f)


# ---------------------------------------------------------
# Markdown 학습자료 불러오기
# ---------------------------------------------------------

@st.cache_data
def load_markdown_content(file_path):

    clean_path = file_path.lstrip('/')

    target_path = (
        clean_path
        if os.path.exists(clean_path)
        else os.path.join(
            "curriculum",
            clean_path
        )
    )

    if not os.path.exists(target_path):

        return "학습 콘텐츠를 준비 중입니다."

    with open(
        target_path,
        'r',
        encoding='utf-8'
    ) as f:

        return f.read()


# =========================================================
# 2. Session State 초기화
# =========================================================

def initialize_session_state():

    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'home'

    if 'level' not in st.session_state:
        st.session_state.level = None

    if 'lt_current_q' not in st.session_state:
        st.session_state.lt_current_q = 0

    if 'lt_score' not in st.session_state:
        st.session_state.lt_score = 0

    if 'lt_user_answers' not in st.session_state:
        st.session_state.lt_user_answers = []

    if 'user_id' not in st.session_state:
        st.session_state.user_id = None

    if 'user_gender' not in st.session_state:
        st.session_state.user_gender = None

    if 'user_grade' not in st.session_state:
        st.session_state.user_grade = None

    if 'current_week' not in st.session_state:
        st.session_state.current_week = 1

    if 'current_day' not in st.session_state:
        st.session_state.current_day = 1

    if 'dq_current_q' not in st.session_state:
        st.session_state.dq_current_q = 0

    if 'dq_total_q' not in st.session_state:
        st.session_state.dq_total_q = 0

    if 'dq_score' not in st.session_state:
        st.session_state.dq_score = 0

    if 'all_incorrect_answers' not in st.session_state:
        st.session_state.all_incorrect_answers = []

    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []

    if 'db_saved' not in st.session_state:
        st.session_state.db_saved = False


# =========================================================
# 3. 기존 사용자 확인 함수
# =========================================================

def get_existing_user(user_id):

    try:

        from streamlit_gsheets import GSheetsConnection

        conn = st.connection(
            "gsheets",
            type=GSheetsConnection
        )

        df = conn.read(
            worksheet="시트1",
            ttl=5
        )

        if df is None or df.empty:
            return None

        # ID 열이 없으면 신규 사용자
        if "ID" not in df.columns:
            return None

        # ID를 문자열로 통일
        df["ID"] = (
            df["ID"]
            .astype(str)
            .str.strip()
        )

        user_id = str(user_id).strip()

        user_data = df[
            df["ID"] == user_id
        ]

        if user_data.empty:
            return None

        # 같은 ID가 여러 번 있다면 가장 최근 기록 사용
        user = user_data.iloc[-1]

        return {
            "ID": user_id,
            "성별": user.get("성별", "미상"),
            "학년": user.get("학년", "미상"),
            "점수": user.get("점수", 0),
            "배치수준": user.get(
                "배치수준",
                "초급자"
            )
        }

    except Exception as e:

        st.error(
            f"기존 사용자 확인 중 오류가 발생했습니다: {e}"
        )

        return None


# =========================================================
# 4. 배치수준 → 폴더명 변환
# =========================================================

def convert_level_to_folder(display_level):

    if display_level == "고급자":
        return "advanced"

    elif display_level == "중급자":
        return "intermediate"

    else:
        return "beginner"


# =========================================================
# 5. 홈 페이지
# =========================================================

def render_home_page():

    st.title("AI 금융 교육 챗봇 🤖")

    st.markdown("---")

    st.subheader(
        "금융 지식, AI와 함께 쉽고 재미있게!"
    )

    st.write(
        "학습자 ID를 입력하면 기존 학습 기록을 확인합니다."
    )

    user_id = st.text_input(
        "학습자 ID (고유값을 입력하세요)",
        key="login_user_id"
    )

    if st.button(
        "학습 시작하기",
        type="primary",
        use_container_width=True
    ):

        if not user_id.strip():

            st.warning("ID를 입력하세요!")
            return

        user_id = user_id.strip()

        st.session_state.user_id = user_id

        # -------------------------------------------------
        # 기존 사용자 확인
        # -------------------------------------------------

        existing_user = get_existing_user(
            user_id
        )

        # =================================================
        # 기존 사용자
        # =================================================

        if existing_user is not None:

            # 기존 개인정보
            st.session_state.user_gender = (
                existing_user["성별"]
            )

            st.session_state.user_grade = (
                existing_user["학년"]
            )

            # 기존 레벨
            display_level = (
                existing_user["배치수준"]
            )

            st.session_state.level = (
                convert_level_to_folder(
                    display_level
                )
            )

            # ---------------------------------------------
            # 기존 사용자는 레벨테스트 생략
            # ---------------------------------------------

            st.session_state.current_page = (
                'learning'
            )

            # 학습 시작 상태
            st.session_state.current_week = 1
            st.session_state.current_day = 1

            # 챗봇 초기화
            st.session_state.chat_messages = []

            # 레벨테스트 관련 값 초기화
            st.session_state.lt_current_q = 0
            st.session_state.lt_score = 0
            st.session_state.lt_user_answers = []

            st.session_state.db_saved = True

            st.rerun()

        # =================================================
        # 신규 사용자
        # =================================================

        else:

            # 레벨테스트 초기화
            st.session_state.lt_current_q = 0
            st.session_state.lt_score = 0
            st.session_state.lt_user_answers = []

            st.session_state.db_saved = False

            st.session_state.current_page = (
                'survey'
            )

            st.rerun()


# =========================================================
# 6. 참여자 정보 입력
# =========================================================

def render_survey_page():

    st.title("📋 참여자 정보 입력")

    with st.form("survey_form"):

        gender = st.radio(
            "성별",
            ["남성", "여성"],
            horizontal=True
        )

        grade = st.selectbox(
            "학년 및 상태",
            [
                "1학년",
                "2학년",
                "3학년",
                "4학년",
                "졸업생",
                "기타"
            ]
        )

        submitted = st.form_submit_button(
            "레벨 테스트 시작",
            type="primary",
            use_container_width=True
        )

        if submitted:

            st.session_state.user_gender = gender
            st.session_state.user_grade = grade

            # 레벨테스트 시작 시 초기화
            st.session_state.lt_current_q = 0
            st.session_state.lt_score = 0
            st.session_state.lt_user_answers = []

            st.session_state.current_page = (
                'level_test'
            )

            st.rerun()


# =========================================================
# 7. 레벨 테스트
# =========================================================

def render_level_test_page():

    level_test_data = load_json_data(
        'level_test_questions.json'
    )

    if not level_test_data:

        st.error(
            "레벨 테스트 문제 파일을 찾을 수 없습니다."
        )

        return

    total_q = len(
        level_test_data
    )

    q_index = (
        st.session_state.lt_current_q
    )

    st.title(
        "금융 지식 레벨 테스트"
    )

    st.progress(
        q_index / total_q,
        text=f"진행률: {q_index}/{total_q}"
    )

    q_data = level_test_data[
        q_index
    ]

    st.subheader(
        f"Q{q_index + 1}. "
        f"{q_data['question']}"
    )

    with st.form(
        key=f"lt_{q_index}"
    ):

        user_answer = st.radio(
            "답:",
            q_data["options"],
            index=None
        )

        submitted = st.form_submit_button(
            "제출",
            use_container_width=True
        )

        if submitted:

            if not user_answer:

                st.warning(
                    "답을 선택해주세요!"
                )

                return

            is_correct = (
                user_answer ==
                q_data["answer"]
            )

            if is_correct:

                st.session_state.lt_score += 1

            st.session_state.lt_user_answers.append({

                "q": q_data["question"],

                "sel": user_answer,

                "ans": q_data["answer"],

                "correct": is_correct,

                "category": q_data.get(
                    "category",
                    "기본"
                )

            })

            # ---------------------------------------------
            # 다음 문제
            # ---------------------------------------------

            if q_index < total_q - 1:

                st.session_state.lt_current_q += 1

                st.rerun()

            # ---------------------------------------------
            # 마지막 문제
            # ---------------------------------------------

            else:

                st.session_state.current_page = (
                    'result'
                )

                st.rerun()


# =========================================================
# 8. 레벨 테스트 결과
# =========================================================

def render_result_page():

    score = (
        st.session_state.lt_score
    )

    total_q = len(
        load_json_data(
            'level_test_questions.json'
        )
    )

    percentage = (
        score / total_q
    )

    # -----------------------------------------------------
    # 레벨 결정
    # -----------------------------------------------------

    if percentage >= 0.8:

        display_level = "고급자"

    elif percentage >= 0.5:

        display_level = "중급자"

    else:

        display_level = "초급자"

    st.session_state.level = (
        convert_level_to_folder(
            display_level
        )
    )

    # =====================================================
    # Google Sheet 저장
    # =====================================================

    if not st.session_state.db_saved:

        try:

            from streamlit_gsheets import GSheetsConnection

            conn = st.connection(
                "gsheets",
                type=GSheetsConnection
            )

            now = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            new_row = pd.DataFrame([{

                "ID":
                    st.session_state.user_id,

                "일시":
                    now,

                "성별":
                    st.session_state.get(
                        "user_gender",
                        "미상"
                    ),

                "학년":
                    st.session_state.get(
                        "user_grade",
                        "미상"
                    ),

                "점수":
                    score,

                "배치수준":
                    display_level

            }])

            existing_data = conn.read(
                worksheet="시트1",
                ttl=5
            ).dropna(
                how="all"
            )

            updated_data = pd.concat(
                [
                    existing_data,
                    new_row
                ],
                ignore_index=True
            )

            conn.update(
                worksheet="시트1",
                data=updated_data
            )

            st.session_state.db_saved = True

        except Exception as e:

            st.error(
                f"저장 실패: {type(e).__name__}"
            )

            st.code(
                traceback.format_exc()
            )

            return

    # =====================================================
    # 결과 화면
    # =====================================================

    st.title(
        "🎉 테스트 결과"
    )

    st.write(
        f"당신의 레벨은 "
        f"**'{display_level}'** 입니다."
    )

    st.progress(
        percentage,
        text=(
            f"전체 정답률: "
            f"{percentage * 100:.1f}% "
            f"({score}/{total_q})"
        )
    )

    # -----------------------------------------------------
    # 영역별 지식 성취도
    # -----------------------------------------------------

    st.markdown("---")

    st.subheader(
        "📊 영역별 지식 성취도 분석"
    )

    cat_data = {}

    for ans in st.session_state.lt_user_answers:

        cat = ans["category"]

        if cat not in cat_data:

            cat_data[cat] = {
                "correct": 0,
                "total": 0
            }

        cat_data[cat]["total"] += 1

        if ans["correct"]:

            cat_data[cat]["correct"] += 1

    if cat_data:

        df = pd.DataFrame([

            {
                "영역": k,
                "정답률(%)":
                    (
                        v["correct"] /
                        v["total"]
                    ) * 100
            }

            for k, v
            in cat_data.items()

        ])

        chart = alt.Chart(
            df
        ).mark_bar(
            color="#4C78A8"
        ).encode(

            x=alt.X(
                "정답률(%):Q",
                scale=alt.Scale(
                    domain=[0, 100]
                )
            ),

            y=alt.Y(
                "영역:N",
                sort="-x"
            ),

            tooltip=[
                "영역",
                "정답률(%)"
            ]

        ).properties(
            height=250
        )

        st.altair_chart(
            chart,
            use_container_width=True
        )

    # -----------------------------------------------------
    # 오답 노트
    # -----------------------------------------------------

    with st.expander(
        "오답 노트 확인하기"
    ):

        incorrects = [

            ans
            for ans
            in st.session_state.lt_user_answers
            if not ans["correct"]

        ]

        if not incorrects:

            st.success(
                "모든 문제를 맞혔습니다! 🥳"
            )

        else:

            for ans in incorrects:

                st.error(
                    f"[{ans['category']}] "
                    f"Q. {ans['q']}\n\n"
                    f"- 나의 답: {ans['sel']}\n"
                    f"- 정답: {ans['ans']}"
                )

    # -----------------------------------------------------
    # 학습 시작
    # -----------------------------------------------------

    if st.button(
        "나의 맞춤 학습 시작하기",
        type="primary",
        use_container_width=True
    ):

        st.session_state.current_page = (
            'learning'
        )

        st.rerun()


# =========================================================
# 9. 학습 페이지 + AI 챗봇
# =========================================================

def render_learning_page():

    level = (
        st.session_state.level
    )

    week = (
        st.session_state.current_week
    )

    day = (
        st.session_state.current_day
    )

    # -----------------------------------------------------
    # 학습 콘텐츠
    # -----------------------------------------------------

    content = load_markdown_content(
        f"{level}/w{week}d{day}_content.md"
    )

    st.title(
        f"[{level.capitalize()}] "
        f"{week}주차 {day}일차 학습"
    )

    # 학습 내용
    with st.container(height=300):

        st.markdown(content)

    st.markdown("---")

    # =====================================================
    # AI 튜터
    # =====================================================

    st.subheader(
        "무엇이든 물어보세요! AI 튜터 💬"
    )

    # -----------------------------------------------------
    # 취약점 분석
    # -----------------------------------------------------

    lt_incorrects = [

        ans["q"]
        for ans
        in st.session_state.lt_user_answers
        if not ans["correct"]

    ]

    dq_incorrects = [

        ans["question"]
        for ans
        in st.session_state.all_incorrect_answers

    ]

    all_weaknesses = list(
        set(
            lt_incorrects +
            dq_incorrects
        )
    )

    weakness_context = ""

    if all_weaknesses:

        weakness_context = (
            "\n\n"
            "[학습자 취약점 분석]\n"
            "이 학생은 다음 개념들에 관한 문제에서 "
            "오답을 기록했습니다:\n"
            "- "
            + "\n- ".join(
                all_weaknesses
            )
            + "\n\n"
            "(지시사항: 답변 시 위 취약 개념과 "
            "연관된 내용이 있다면 더 친절하게 "
            "비유를 들어 설명하고, 학생 수준에 "
            "맞춰 눈높이를 낮춰주세요.)"
        )

    # -----------------------------------------------------
    # 기존 채팅 메시지 출력
    # -----------------------------------------------------

    for msg in st.session_state.chat_messages:

        with st.chat_message(
            msg["role"]
        ):

            st.markdown(
                msg["content"]
            )

    # -----------------------------------------------------
    # 사용자 질문
    # -----------------------------------------------------

    if prompt := st.chat_input(
        "오늘 학습 내용에 대해 질문해보세요..."
    ):

        st.session_state.chat_messages.append({

            "role": "user",

            "content": prompt

        })

        with st.chat_message("user"):

            st.markdown(prompt)

        # -------------------------------------------------
        # AI 응답
        # -------------------------------------------------

        with st.chat_message("assistant"):

            with st.spinner(
                "AI 튜터가 답변을 생각하고 있어요..."
            ):

                system_prompt = f"""
당신은 대학생 금융 교육 전문가입니다.

아래의 오늘 학습 내용을 기반으로 답변해주세요.

--- 학습 내용 ---
{content}
----------------

{weakness_context}

답변 시 다음 원칙을 지켜주세요.

1. 오늘 학습 내용과 관련된 질문은
   학습 내용을 기반으로 답변하세요.

2. 대학생이 이해하기 쉬운 표현을 사용하세요.

3. 어려운 금융 용어는 쉽게 풀어서 설명하세요.

4. 학습자의 취약 개념과 관련된 질문이라면
   더 친절하고 자세하게 설명하세요.

5. 학습 내용에 없는 내용을 임의로 만들어내지 마세요.
"""

                try:

                    response = (
                        openai
                        .chat
                        .completions
                        .create(

                            model="gpt-4o",

                            messages=[

                                {
                                    "role": "system",
                                    "content":
                                        system_prompt
                                },

                                {
                                    "role": "user",
                                    "content":
                                        prompt
                                }

                            ]
                        )
                    )

                    ai_response = (
                        response
                        .choices[0]
                        .message
                        .content
                    )

                except Exception as e:

                    ai_response = (
                        f"API 요청 오류: {e}"
                    )

                st.markdown(
                    ai_response
                )

        st.session_state.chat_messages.append({

            "role": "assistant",

            "content": ai_response

        })

    # =====================================================
    # 학습 완료 → 퀴즈
    # =====================================================

    st.markdown("---")

    if content != "학습 콘텐츠를 준비 중입니다.":

        if st.button(
            "학습 완료! 퀴즈 풀기",
            type="primary",
            use_container_width=True
        ):

            st.session_state.dq_current_q = 0
            st.session_state.dq_score = 0

            st.session_state.current_page = (
                'daily_quiz'
            )

            st.rerun()



# =====================================================
# 10. 일일 복습 퀴즈
# =====================================================

def render_daily_quiz_page():

    level = st.session_state.level
    week = st.session_state.current_week
    day = st.session_state.current_day

    quiz_data = load_json_data(
        f"{level}/w{week}d{day}_quiz.json"
    )

    st.title(
        f"[{level.capitalize()}] "
        f"{week}주차 {day}일차 복습 퀴즈 📝"
    )

    if not quiz_data:
        st.error("퀴즈 데이터를 찾을 수 없습니다.")
        return

    total_q = len(quiz_data)

    q_index = st.session_state.dq_current_q

    st.session_state.dq_total_q = total_q

    st.progress(
        q_index / total_q,
        text=f"퀴즈 진행률: {q_index}/{total_q}"
    )

    q_data = quiz_data[q_index]

    st.subheader(
        f"Q{q_index + 1}. {q_data['question']}"
    )

    with st.form(
        key=f"dq_form_{q_index}"
    ):

        user_answer = st.radio(
            "답:",
            q_data["options"],
            index=None
        )

        submitted = st.form_submit_button(
            "제출",
            use_container_width=True
        )

        if submitted:

            if not user_answer:

                st.warning(
                    "답을 선택해주세요!"
                )

                return

            # 정답 여부 확인
            is_correct = (
                user_answer == q_data["answer"]
            )

            # 정답이면 점수 증가
            if is_correct:

                st.session_state.dq_score += 1

            # -----------------------------------------
            # 오답이면 오답노트에 저장
            # -----------------------------------------

            else:

                incorrect_data = {
                    "week": week,
                    "day": day,
                    "question": q_data["question"],
                    "options": q_data["options"],
                    "answer": q_data["answer"],
                    "user_answer": user_answer
                }

                # 같은 차시에서 같은 문제 중복 저장 방지
                already_saved = any(
                    item.get("week") == week
                    and item.get("day") == day
                    and item.get("question") == q_data["question"]
                    for item in st.session_state.all_incorrect_answers
                )

                if not already_saved:

                    st.session_state.all_incorrect_answers.append(
                        incorrect_data
                    )

            # -----------------------------------------
            # 다음 문제
            # -----------------------------------------

            if q_index < total_q - 1:

                st.session_state.dq_current_q += 1

            else:

                st.session_state.current_page = (
                    'quiz_result'
                )

            st.rerun()


# =========================================================
# 11. 퀴즈 결과
# =========================================================

def render_quiz_result_page():

    week = st.session_state.current_week
    day = st.session_state.current_day

    st.title(
        f"{week}주차 {day}일차 학습 완료! 🎉"
    )

    st.success(
        "오늘의 학습과 퀴즈를 모두 마쳤습니다."
    )

    # ---------------------------------------------
    # 퀴즈 점수
    # ---------------------------------------------

    st.metric(
        label="퀴즈 결과",
        value=(
            f"{st.session_state.dq_score} / "
            f"{st.session_state.dq_total_q} 점"
        )
    )

    st.markdown("---")

    # =====================================================
    # 오늘의 오답 노트
    # =====================================================

    st.subheader("📝 오늘의 오답 노트")

    # 현재 주차/차시에서 틀린 문제만 가져오기
    today_incorrects = [

        item

        for item in st.session_state.all_incorrect_answers

        if item.get("week") == week
        and item.get("day") == day

    ]

    # ---------------------------------------------
    # 오답이 없는 경우
    # ---------------------------------------------

    if not today_incorrects:

        st.success(
            "오늘은 모든 문제를 맞혔습니다! 🎉"
        )

    # ---------------------------------------------
    # 오답이 있는 경우
    # ---------------------------------------------

    else:

        st.warning(
            f"오늘 틀린 문제는 "
            f"총 **{len(today_incorrects)}개**입니다."
        )

        for i, q_data in enumerate(
            today_incorrects
        ):

            with st.expander(
                f"❌ 오답 {i + 1}. "
                f"{q_data['question']}"
            ):

                # 내가 선택한 답
                st.markdown(
                    f"**내가 선택한 답:** "
                    f"❌ {q_data['user_answer']}"
                )

                # 정답
                st.markdown(
                    f"**정답:** "
                    f"✅ {q_data['answer']}"
                )

                st.markdown("---")

                # 선택지 확인
                st.markdown("**선택지**")

                for option in q_data["options"]:

                    if option == q_data["answer"]:

                        st.success(
                            f"✅ {option} ← 정답"
                        )

                    elif option == q_data["user_answer"]:

                        st.error(
                            f"❌ {option} ← 내가 선택한 답"
                        )

                    else:

                        st.write(
                            f"○ {option}"
                        )

    st.markdown("---")

    # =====================================================
    # 다음 차시 이동
    # =====================================================

    # ---------------------------------------------
    # 마지막 차시 여부
    # ---------------------------------------------

    is_last_day = (
        week == 4 and
        day == 5
    )

    if is_last_day:

        if st.button(
            "4주 완성! 최종 복습 하러가기",
            type="primary",
            use_container_width=True
        ):

            st.session_state.current_page = (
                'final_review'
            )

            st.rerun()

    else:

        if st.button(
            "다음 차시 학습하기",
            type="primary",
            use_container_width=True
        ):

            # -----------------------------------------
            # 같은 주차의 다음 차시
            # -----------------------------------------

            if st.session_state.current_day < 5:

                st.session_state.current_day += 1

            # -----------------------------------------
            # 다음 주차
            # -----------------------------------------

            elif st.session_state.current_week < 4:

                st.session_state.current_week += 1

                st.session_state.current_day = 1

            # -----------------------------------------
            # 다음 학습으로 이동
            # -----------------------------------------

            st.session_state.chat_messages = []

            st.session_state.current_page = (
                'learning'
            )

            st.rerun()


# =========================================================
# 12. 최종 오답 복습
# =========================================================

def render_final_review_page():

    st.title(
        "총정리: 오답 다시 풀기 🧠"
    )

    st.write(
        "4주간의 학습 중 틀렸던 모든 문제들을 "
        "다시 풀어보는 최종 복습 시간입니다."
    )

    st.markdown("---")

    incorrect_qs = (
        st.session_state
        .all_incorrect_answers
    )

    # -----------------------------------------------------
    # 오답 없음
    # -----------------------------------------------------

    if not incorrect_qs:

        st.success(
            "대단합니다! 4주간의 퀴즈에서 "
            "틀린 문제가 하나도 없어요. 🏆"
        )

        st.balloons()

    # -----------------------------------------------------
    # 오답 출력
    # -----------------------------------------------------

    else:

        for i, q_data in enumerate(
            incorrect_qs
        ):

            st.subheader(
                f"오답 {i + 1}. "
                f"{q_data['question']}"
            )

            st.info(
                f"정답: **{q_data['answer']}**"
            )

            st.markdown("---")

    # -----------------------------------------------------
    # 전체 초기화
    # -----------------------------------------------------

    if st.button(
        "모든 과정 초기화하고 처음으로 돌아가기",
        use_container_width=True
    ):

        for key in list(
            st.session_state.keys()
        ):

            del st.session_state[key]

        st.rerun()


# =========================================================
# 13. 메인 로직
# =========================================================

def main():

    initialize_session_state()

    pages = {

        'home':
            render_home_page,

        'survey':
            render_survey_page,

        'level_test':
            render_level_test_page,

        'result':
            render_result_page,

        'learning':
            render_learning_page,

        'daily_quiz':
            render_daily_quiz_page,

        'quiz_result':
            render_quiz_result_page,

        'final_review':
            render_final_review_page

    }

    page_to_render = pages.get(
        st.session_state.current_page,
        render_home_page
    )

    page_to_render()


# =========================================================
# 14. 실행
# =========================================================

if __name__ == "__main__":
    main()
