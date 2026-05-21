import streamlit as st
import json
import os
import pandas as pd

# ==================== 配置区 ====================
# 设置网页基础信息，必须放在最前面
st.set_page_config(page_title="初中道法专属刷题系统", page_icon="📚", layout="centered")

# 定义本地文件路径
DB_FILE = "mistakes_db.json"
CSV_FILE = "daofa_questions.csv"

# ==================== 🛠️ 错题本持久化工具 ====================
def load_mistakes():
    """从本地读取专属错题本"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_mistakes(mistakes):
    """保存错题本到本地"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(mistakes, f, ensure_ascii=False, indent=4)
# ==================== 📚 题库加载模块 ====================
@st.cache_data
def load_questions_from_csv(file_path):
    """读取 CSV 题库并按章节分类"""
    if not os.path.exists(file_path):
        # 防呆设计：如果没有题库文件，提供一条占位测试题
        st.warning(f"⚠️ 找不到题库文件 {file_path}，请确保它与 app.py 在同一文件夹下。")
        return {
            "等待加载题库": [{
                "id": 999, "question": "这只是一道测试题，请准备好 csv 题库文件。", 
                "options": ["选项A", "选项B", "选项C", "选项D"], "answer": "选项A", "analysis": "快去让 AI 生成题库吧！"
            }]
        }
    
    df = pd.read_csv(file_path, encoding='utf-8')
    questions_dict = {}
    
    for index, row in df.iterrows():
        chapter = str(row['章节'])
        if chapter not in questions_dict:
            questions_dict[chapter] = []
            
        q = {
            "id": index + 1,  # 使用表格行号作为唯一ID
            "question": str(row['题干']),
            "options": [str(row['选项A']), str(row['选项B']), str(row['选项C']), str(row['选项D'])],
            "answer": str(row['正确答案']),
            "analysis": str(row['解析'])
        }
        questions_dict[chapter].append(q)
        
    return questions_dict

# 立即加载题库
QUESTIONS = load_questions_from_csv(CSV_FILE)
# ==================== 🧠 初始化 Session 状态 ====================
# 加载持久化错题本
if 'mistakes' not in st.session_state:
    st.session_state.mistakes = load_mistakes()

# 基础状态变量
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'show_analysis' not in st.session_state:
    st.session_state.show_analysis = {} # 用于错题本的解析展示控制

# 页面主标题
st.title("📚 初中道法专属刷题系统")

# ==================== 🧭 侧边栏导航 ====================
st.sidebar.header("导航控制台")
chapter = st.sidebar.selectbox("选择学习章节", list(QUESTIONS.keys()))
nav = st.sidebar.radio("功能切换", ["📝 章节高效练习", "📓 智能错题本"])

# 处理切换菜单和章节时的重置逻辑
if 'last_nav' not in st.session_state or st.session_state.last_nav != nav:
    st.session_state.last_nav = nav
    st.session_state.show_analysis = {}

if 'last_chapter' not in st.session_state or st.session_state.last_chapter != chapter:
    st.session_state.last_chapter = chapter
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.submitted = False

current_chapter_questions = QUESTIONS[chapter]
# ==================== 主功能 1：章节练习 ====================
if nav == "📝 章节高效练习":
    st.subheader(f"当前章节：{chapter}")
    
    total_q = len(current_chapter_questions)
    if st.session_state.current_index < total_q:
        # 显示进度
        progress = st.session_state.current_index / total_q
        st.progress(progress, text=f"本章进度: {st.session_state.current_index + 1} / {total_q}")
        
        # 获取当前题目
        q = current_chapter_questions[st.session_state.current_index]
        st.markdown(f"### **Q{st.session_state.current_index + 1}: {q['question']}**")
        
        with st.form(key=f"form_{q['id']}"):
            user_choice = st.radio("请选择最符合题意的选项：", q['options'], index=None)
            submit_button = st.form_submit_button(label="提交答案")
            
            if submit_button:
                if user_choice:
                    st.session_state.submitted = True
                    if user_choice == q['answer']:
                        st.session_state.is_correct = True
                        st.session_state.score += 1
                    else:
                        st.session_state.is_correct = False
                        # 答错加入本地错题本
                        q_id_str = str(q['id'])
                        if q_id_str not in st.session_state.mistakes:
                            st.session_state.mistakes[q_id_str] = {
                                "id": q['id'],
                                "question": q['question'],
                                "options": q['options'],
                                "answer": q['answer'],
                                "analysis": q['analysis'],
                                "correct_count": 0  # 追踪做对次数
                            }
                            save_mistakes(st.session_state.mistakes)
                else:
                    st.warning("⚠️ 请先选择一个选项再提交！")

        # 结果反馈
        if st.session_state.submitted:
            if st.session_state.is_correct:
                st.success("🎉 **回答正确！** 稳扎稳打，继续保持！")
                st.balloons()
            else:
                st.error("❌ **选错啦。** 没关系，已自动记入错题本！")
                with st.container(border=True):
                    st.info(f"💡 **正确答案：** {q['answer']}\n\n**【解析】**\n{q['analysis']}")
            
            if st.button("进入下一题 ➡️"):
                st.session_state.current_index += 1
                st.session_state.submitted = False
                st.rerun()
                
    else:
        # 章节完结页
        st.success(f"🏆 恭喜完成了【{chapter}】的所有练习！")
        st.metric(label="最终得分", value=f"{st.session_state.score} / {total_q}")
        if st.button("🔄 重新练习本章"):
            st.session_state.current_index = 0
            st.session_state.score = 0
            st.session_state.submitted = False
            st.rerun()
# ==================== 主功能 2：智能错题本 ====================
elif nav == "📓 智能错题本":
    st.subheader("📓 我的专属错题本")
    st.caption("💡 累计做对 3 次的题目，系统会自动将其消灭！")
    
    # 确保读取最新数据
    st.session_state.mistakes = load_mistakes()
    
    if not st.session_state.mistakes:
        st.success("✨ **太强了！本地没有任何错题！**")
    else:
        st.write(f"当前待攻克错题： **{len(st.session_state.mistakes)}** 道")
        
        for q_id in list(st.session_state.mistakes.keys()):
            mq = st.session_state.mistakes[q_id]
            
            with st.container(border=True):
                st.markdown(f"**🚧 通关进度: [{mq['correct_count']}/3] ｜ 原题重现：**")
                st.markdown(f"#### {mq['question']}")
                
                with st.form(key=f"retry_form_{mq['id']}"):
                    retry_choice = st.radio(f"请作答：", mq['options'], index=None)
                    check_btn = st.form_submit_button("提交答案")
                    
                    if check_btn:
                        if retry_choice:
                            if retry_choice == mq['answer']:
                                # 做对的情况
                                mq['correct_count'] += 1
                                st.session_state.show_analysis[q_id] = False 
                                
                                if mq['correct_count'] >= 3:
                                    del st.session_state.mistakes[q_id]
                                    save_mistakes(st.session_state.mistakes)
                                    st.toast("🎉 连续做对3次，已彻底斩草除根！")
                                    st.rerun()
                                else:
                                    save_mistakes(st.session_state.mistakes)
                                    st.toast(f"👍 做对了！进度推进至: {mq['correct_count']}/3")
                                    st.rerun()
                            else:
                                # 做错的情况
                                st.session_state.show_analysis[q_id] = True
                                st.error("😭 还是不对，请看下方解析温习！")
                        else:
                            st.warning("请选择一个答案！")
                
                # 只有答错时，才显示解析
                if st.session_state.show_analysis.get(q_id, False):
                    st.info(f"💡 **正确答案：** {mq['answer']}\n\n**【解析】**\n{mq['analysis']}")
                
        st.markdown("---")        
        if st.sidebar.button("🚨 清空所有错题(危险)"):
            st.session_state.mistakes = {}
            st.session_state.show_analysis = {}
            save_mistakes({})
            st.rerun()