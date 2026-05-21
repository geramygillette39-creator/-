import streamlit as st
import pandas as pd
import random
import re

# ==========================================
# 1. 页面基本配置与强制浅色主题
# ==========================================
st.set_page_config(
    page_title="初中道法智能刷题系统", 
    page_icon="📚", 
    layout="centered"
)

# 强制锁死浅色模式（白底黑字）
st.markdown("""
    <style>
    .stApp {
        background-color: #FFFFFF !important;
        color: #31333F !important;
    }
    h1, h2, h3, p, span, label {
        color: #31333F !important;
    }
    div[data-testid="stMarkdownContainer"] p {
        color: #31333F !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据加载与超级清洗
# ==========================================
def clean_option_text(text, prefix):
    """如果选项内容开头已经包含了 'A.' 'A、' 等，自动将其剔除，防止前端重复显示"""
    text = str(text).strip()
    # 匹配以 A. A、 A  或 小写 a. a、 等开头的文本
    pattern = rf'^{prefix}\s*[\.\、\s]?\s*'
    return re.sub(pattern, '', text, flags=re.IGNORECASE)

def load_data(filename="questions.xlsx"):
    try:
        df = pd.read_excel(filename, dtype=str)
        df.columns = df.columns.str.strip()
        df.rename(columns={'选项a': '选项A', '选项b': '选项B', '选项c': '选项C', '选项d': '选项D'}, inplace=True)
        
        # 清洗掉可能由于WPS留下的多余空行
        df.dropna(subset=['题干', '正确答案'], inplace=True)
        df = df.reset_index(drop=True)
        df['ID'] = df.index
        
        # 【核心清洗逻辑】
        for idx, row in df.iterrows():
            # 1. 选项去重清洗：把 "A.①②" 变成 "①②"
            df.at[idx, '选项A'] = clean_option_text(row['选项A'], 'A')
            df.at[idx, '选项B'] = clean_option_text(row['选项B'], 'B')
            df.at[idx, '选项C'] = clean_option_text(row['选项C'], 'C')
            df.at[idx, '选项D'] = clean_option_text(row['选项D'], 'D')
            
            # 2. 提取正确答案的首字母：不管Excel里写 "C.②④" 还是 "C"，统统只拿 "C"
            ans_str = str(row['正确答案']).strip().upper()
            match = re.match(r'([A-D])', ans_str)
            if match:
                df.at[idx, '正确答案_干净'] = match.group(1)
            else:
                # 备用容错：如果实在没匹配到，全角转半角提取
                full_to_half = {"Ａ": "A", "Ｂ": "B", "Ｃ": "C", "Ｄ": "D"}
                first_char = ans_str[0] if len(ans_str) > 0 else 'A'
                df.at[idx, '正确答案_干净'] = full_to_half.get(first_char, first_char)
                
        return df
    except FileNotFoundError:
        st.error(f"找不到题库文件 `{filename}`！请确保文件存在且和代码在同一目录下。")
        st.stop()

df = load_data()

# ==========================================
# 3. 初始化 Session 状态
# ==========================================
def init_session():
    if 'mistakes' not in st.session_state:
        st.session_state.mistakes = {}
    if 'progress' not in st.session_state:
        st.session_state.progress = {chapter: set() for chapter in df['章节'].unique() if pd.notna(chapter)}
    if 'current_q_id' not in st.session_state:
        st.session_state.current_q_id = None
    if 'answered' not in st.session_state:
        st.session_state.answered = False
    if 'is_correct' not in st.session_state:
        st.session_state.is_correct = None
    if 'selected_option' not in st.session_state:
        st.session_state.selected_option = None

init_session()

# ==========================================
# 4. 核心逻辑函数
# ==========================================
def get_next_question(mode, chapter=None):
    st.session_state.answered = False
    st.session_state.selected_option = None
    
    if mode == "章节练习":
        chapter_df = df[df['章节'] == chapter]
        if chapter_df.empty:
            st.session_state.current_q_id = None
            return
        st.session_state.current_q_id = random.choice(chapter_df['ID'].tolist())
    else: 
        if not st.session_state.mistakes:
            st.session_state.current_q_id = None
            return
        st.session_state.current_q_id = random.choice(list(st.session_state.mistakes.keys()))

def submit_answer(q_id, user_ans, correct_ans_clean, chapter):
    st.session_state.answered = True
    st.session_state.selected_option = user_ans
    
    # 此时进行纯净的单字母对齐比对
    if user_ans == correct_ans_clean:
        st.session_state.is_correct = True
        if chapter in st.session_state.progress:
            st.session_state.progress[chapter].add(q_id)
        
        if q_id in st.session_state.mistakes:
            st.session_state.mistakes[q_id] += 1
            if st.session_state.mistakes[q_id] >= 3:
                del st.session_state.mistakes[q_id]
                st.toast("🎉 这道错题你已经答对3次，已将其移出错题本！")
    else:
        st.session_state.is_correct = False
        st.session_state.mistakes[q_id] = 0

# ==========================================
# 5. UI界面渲染
# ==========================================
st.title("📚 初中道法智能刷题系统")

with st.sidebar:
    st.header("⚙️ 刷题设置")
    mode = st.radio("选择模式", ["章节练习", "错题本模式"])
    
    chapter_selected = None
    valid_chapters = [ch for ch in df['章节'].unique() if pd.notna(ch)]
    
    if mode == "章节练习":
        chapter_selected = st.selectbox("选择章节", valid_chapters)
        
        total_q = len(df[df['章节'] == chapter_selected])
        mastered_q = len(st.session_state.progress.get(chapter_selected, set()))
        progress_pct = int((mastered_q / total_q) * 100) if total_q > 0 else 0
        
        st.markdown("---")
        st.subheader("📊 章节学习进度")
        st.progress(progress_pct)
        st.caption(f"当前章节已掌握：{progress_pct}%")
        
    st.markdown("---")
    st.subheader("📓 错题本状态")
    if len(st.session_state.mistakes) > 0:
        st.info("⚠️ 错题本中有需要复习的题目")
        st.caption("提示：在错题本中累计答对3次即可自动消灭错题。")
    else:
        st.success("✨ 暂无错题，继续保持！")

if st.session_state.current_q_id is None:
    get_next_question(mode, chapter_selected)

if st.session_state.current_q_id is not None and st.session_state.current_q_id in df['ID'].values:
    q_data = df[df['ID'] == st.session_state.current_q_id].iloc[0]
    q_id = q_data['ID']
    chapter = q_data['章节']
    question = q_data['题干']
    options = {'A': q_data['选项A'], 'B': q_data['选项B'], 'C': q_data['选项C'], 'D': q_data['选项D']}
    
    # 核心数据传递
    correct_ans_raw = str(q_data['正确答案']).strip()
    correct_ans_clean = q_data['正确答案_干净']
    explanation = q_data['解析']
    
    st.caption(f"📍 章节：{chapter} {' | ⚠️ 错题复习' if mode == '错题本模式' else ''}")
    st.markdown(f"### {question}")
    
    display_options = [f"A. {options['A']}", f"B. {options['B']}", f"C. {options['C']}", f"D. {options['D']}"]
    
    if not st.session_state.answered:
        user_choice = st.radio("请选择你的答案：", display_options, index=None)
        if st.button("提交答案", type="primary"):
            if user_choice:
                user_letter = user_choice.split(".")[0]
                submit_answer(q_id, user_letter, correct_ans_clean, chapter)
                st.rerun()
            else:
                st.warning("请先选择一个答案！")
    else:
        try:
            current_index = ["A", "B", "C", "D"].index(st.session_state.selected_option)
        except ValueError:
            current_index = 0
            
        st.radio("你的选择是：", display_options, index=current_index, disabled=True)
        
        if st.session_state.is_correct:
            st.success("🎉 太棒了！回答正确！继续保持！")
            st.balloons()
        else:
            # 优雅展示：如果原答案写得太长，就直接把原答案展示出来更直观
            st.error(f"❌ 回答错误。正确答案是：**{correct_ans_raw}**")
            with st.expander("📝 查看解析", expanded=True):
                st.write(explanation)
                
        if st.button("下一题", type="primary"):
            get_next_question(mode, chapter_selected)
            st.rerun()
else:
    if mode == "错题本模式":
        st.success("🎉 恭喜你！错题本空空如也，你已经掌握了所有错题！")
    else:
        st.info("当前章节没有题目，请切换其他章节。")