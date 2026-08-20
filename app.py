import streamlit as st
import json
import os
import openai
import pandas as pd
import altair as alt
import datetime
import traceback

# =========================================================
# 1. 초기 설정
# =========================================================

st.set_page_config(
    page_title="AI 금융 교육 챗봇",
    page_icon="🤖",
    layout="centered"
)

try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("'.streamlit/secrets.toml' 파일에 OpenAI API 키를 설정해주세요.")
    st.stop()


# =========================================================
# 2. 데이터 불러오기 함수
# =========================================================

@st.cache_data
def load_json_data(file_path):
    target_path = (
        file_path
        if os.path.exists(file_path)
        else os.path.join("data", file_path)
    )

    if not os.path.exists(target_path):
        return None

    with open(target_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@st.cache_data
def load_markdown_content(file_path):
    clean_path = file_path.lstrip('/')

    target_path = (
        clean_path
        if os.path.exists(clean_path)
        else os.path.join("curriculum", clean_path)
    )

    if not os.path.exists(target_path):
        return "학습 콘텐츠를 준비 중입니다."

    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()


# =========================================================
# 3. Session State 초기화
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

    if 'dq_score' not in st.session_state:
        st.session_state.dq_score = 0

    if 'all_incorrect_answers' not in st.session_state:
        st.session_state.all_incorrect_answers = []

    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []

    if 'db_saved' not in st.session_state:
        st.session_state.db_saved = False


# =========================================================
# 4. Google Sheet에서 기존 사용자 확인
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

        # ID 컬럼이 없는 경우
        if "ID" not in df.columns:
            return None

        # ID를 문자열로 변환해서 비교
        df["ID"] = df["ID"].astype(str).str.strip()

        user_id = str(user_id).strip()

        user_data = df[df["ID"] == user_id]

        if user_data.empty:
            return None

        # 해당 ID의 가장 마지막 기록
        user = user_data.iloc[-1]

        return {
            "ID": user_id,
            "성별": user.get("성별", "미상"),
            "학년": user.get("학년", "미상"),
            "점수": user.get("점수", 0),
            "배치수준": user.get("배치수준", "초급자")
        }

    except Exception as e:

        st.error(
            f"기존 사용자 확인 중 오류가 발생했습니다: {e}"
        )

        return None


# =========================================================
# 5. 레벨 문자열 변환
# =========================================================

def convert_level_to_folder(display_level):

    if display_level == "고급자":
        return "advanced"

    elif display_level == "중급자":
        return "intermediate"

    else:
        return "beginner"


# =========================================================
# 6. 홈 화면
# =========================================================

def render_home_page():

    st.title("AI 금융 교육 챗봇 🤖")

    st.markdown("---")

    st.subheader("금융 지식, AI와 함께 쉽고 재미있게!")

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

        # 현재 사용자 ID 저장
        st.session_state.user_id = user_id

        # -------------------------------------------------
        # Google Sheet에서 기존 사용자 확인
        # -------------------------------------------------

        existing_user = get_existing_user(user_id)

        # =================================================
        # 기존 사용자
        # =================================================

        if existing_user is not None:

            # 기존 정보 불러오기
            st.session_state.user_gender = existing_user["성별"]
            st.session_state.user_grade = existing_user["학년"]

            # 기존 레벨 불러오기
            display_level = existing_user["배치수준"]

            st.session_state.level = convert_level_to_folder(
                display_level
            )

            # 기존 사용자는 레벨테스트를 다시 하지 않음
            st.session_state.current_page = 'learning'

            # 학습 세션 초기화
            st.session_state.current_week = 1
            st.session_state.current_day = 1

            st.session_state.chat_messages = []

            st.session_state.lt_current_q = 0
            st.session_state.lt_score = 0
            st.session_state.lt_user_answers = []

            st.success(
                f"{user_id}님, 기존 학습 기록을 확인했습니다!"
            )

            st.rerun()

        # =================================================
        # 신규 사용자
        # =================================================

        else:

            # 새로운 레벨테스트를 시작할 때 초기화
            st.session_state.lt_current_q = 0
            st.session_state.lt_score = 0
            st.session_state.lt_user_answers = []

            st.session_state.db_saved = False

            st.session_state.current_page = 'survey'

            st.rerun()


# =========================================================
# 7. 참여자 정보 입력
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

            # 레벨테스트 시작 시 반드시 초기화
            st.session_state.lt_current_q = 0
            st.session_state.lt_score = 0
            st.session_state.lt_user_answers = []

            st.session_state.current_page = 'level_test'

            st.rerun()


# =========================================================
# 8. 레벨 테스트
# =========================================================

def render_level_test_page():

    level_test_data = load_json_data(
        'level_test_questions.json'
    )

    if not level_test_data:

        st.error("레벨 테스트 문제를 불러올 수 없습니다.")
        return

    total_q = len(level_test_data)

    q_index = st.session_state.lt_current_q

    st.title("금융 지식 레벨 테스트")

    st.progress(
        q_index / total_q,
        text=f"진행률: {q_index}/{total_q}"
    )

    q_data = level_test_data[q_index]

    st.subheader(
        f"Q{q_index + 1}. {q_data['question']}"
    )

    with st.form(key=f"lt_{q_index}"):

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

                st.warning("답을 선택해주세요!")
                return

            is_correct = (
                user_answer == q_data["answer"]
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

            # -------------------------------------------------
            # 다음 문제
            # -------------------------------------------------

            if q_index < total_q - 1:

                st.session_state.lt_current_q += 1

                st.rerun()

            # -------------------------------------------------
            # 마지막 문제
            # -------------------------------------------------

            else:

                # 테스트 완료
                st.session_state.current_page = 'result'

                st.rerun()


# =========================================================
# 9. 레벨 테스트 결과
# =========================================================

def render_result_page():

    score = st.session_state.lt_score

    total_q = len(
        load_json_data(
            'level_test_questions.json'
        )
    )

    percentage = score / total_q

    # 레벨 결정
    if percentage >= 0.8:
        display_level = "고급자"

    elif percentage >= 0.5:
        display_level = "중급자"

    else:
        display_level = "초급자"

    st.session_state.level = convert_level_to_folder(
        display_level
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

                "ID": st.session_state.user_id,

                "일시": now,

                "성별": st.session_state.get(
                    "user_gender",
                    "미상"
                ),

                "학년": st.session_state.get(
                    "user_grade",
                    "미상"
                ),

                "점수": score,

                "배치수준": display_level

            }])

            existing_data = conn.read(
                worksheet="시트1",
                ttl=5
            ).dropna(how="all")

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

    st.title("🎉 테스트 결과")

    st.write(
        f"당신의 레벨은 **'{display_level}'** 입니다."
    )

    st.progress(
        percentage,
        text=f"정답률: {percentage * 100:.1f}%"
    )

    st.write(
        f"총 {total_q}문제 중 {score}문제를 맞혔습니다."
    )

    st.markdown("---")

    if st.button(
        "나의 맞춤 학습 시작하기",
        type="primary",
        use_container_width=True
    ):

        st.session_state.current_page = 'learning'

        st.rerun()


# =========================================================
# 10. 학습 페이지
# =========================================================

def render_learning_page():

    level = st.session_state.level

    week = st.session_state.current_week

    day = st.session_state.current_day

    # -----------------------------------------------------
    # 학습 콘텐츠
    # -----------------------------------------------------

    content = load_markdown_content(
        f"{level}/w{week}d{day}_content.md"
    )

    st.title(
        f"{week}주차 {day}일차 학습"
    )

    st.markdown("---")

    st.markdown(content)

    st.markdown("---")

    st.success(
        f"{st.session_state.user_id}님의 "
        f"현재 레벨: {level}"
    )


# =========================================================
# 11. 메인 로직
# =========================================================

def main():

    initialize_session_state()

    pages = {

        'home': render_home_page,

        'survey': render_survey_page,

        'level_test': render_level_test_page,

        'result': render_result_page,

        'learning': render_learning_page

    }

    page = pages.get(
        st.session_state.current_page,
        render_home_page
    )

    page()


if __name__ == "__main__":
    main()
