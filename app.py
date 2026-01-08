import streamlit as st
import uuid
import time
import random
from openai import OpenAI
from chat import smart_chat

# ==============================================================================
# 1. 后端逻辑接入区 (Backend Integration)
#    请将你之前编写的 "smart_chat" 及其依赖函数粘贴或导入到这里
# ==============================================================================
api_key = st.secrets["DEEPSEEK_API_KEY"]
client = OpenAI(api_key=api_key,
base_url="https://api.deepseek.com")

def get_smart_response_mock(user_query, chat_history):
    """
    [模拟后端函数]
    在实际使用中，请用你之前的 'smart_chat' 函数替换此处的逻辑。
    你可以在这里：
    1. 计算用户特征 (LTP, 情感分析等)
    2. 调用 DeepSeek API
    """
    user_features = {'syntax': 'high', 'novelty': 'low', 'intensity': 'low'}
    # user_features = {'syntax': 'low', 'novelty': 'high', 'intensity': 'low'}
    
    # --- 模拟：为了演示前端效果，这里使用简单的随机回复 ---
    # 实际代码中，你应该在这里调用你的 deepseek_api_function(user_query)
    
    time.sleep(1)
    return smart_chat(user_query, user_features, client)


# ==============================================================================
# 2. 前端界面逻辑 (Frontend UI)
# ==============================================================================

# --- 页面配置 ---
st.set_page_config(
    page_title="动态人智交互系统 Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State 初始化 (用于存储多会话数据) ---
if "conversations" not in st.session_state:
    # 结构: { 'chat_id': {'title': '会话标题', 'messages': []} }
    st.session_state.conversations = {} 

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# --- 侧边栏：会话管理 ---
with st.sidebar:
    st.title("🗂️ 历史会话")
    
    # [新建会话按钮]
    if st.button("➕ 新建对话", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        st.session_state.conversations[new_id] = {
            "title": f"新对话 {len(st.session_state.conversations) + 1}",
            "messages": [] # 初始为空，或者加一句开场白
        }
        st.session_state.current_chat_id = new_id
        st.rerun() # 刷新页面

    st.divider()

    # [会话列表]
    # 倒序显示，让最新的在最上面
    chat_ids = list(st.session_state.conversations.keys())
    
    if not chat_ids:
        st.info("暂无历史会话，请点击上方按钮新建。")
    else:
        # 使用 radio 或 button 列表来切换会话
        # 为了美观，这里使用 radio 组件来做导航
        display_options = {cid: data['title'] for cid, data in st.session_state.conversations.items()}
        
        selected_id = st.radio(
            "选择会话：",
            options=chat_ids,
            format_func=lambda x: display_options[x],
            key="chat_selector",
            index=chat_ids.index(st.session_state.current_chat_id) if st.session_state.current_chat_id in chat_ids else 0
        )
        
        # 如果用户切换了选项，更新当前 ID
        if selected_id != st.session_state.current_chat_id:
            st.session_state.current_chat_id = selected_id
            st.rerun()

# --- 主界面：聊天窗口 ---
st.title("🎓 基于用户状态感知的动态人智交互系统")
st.caption("Master Thesis Demo | Powered by DeepSeek & Streamlit")

# 检查是否有当前会话
current_id = st.session_state.current_chat_id

if current_id and current_id in st.session_state.conversations:
    current_chat = st.session_state.conversations[current_id]
    
    # 1. 渲染历史消息
    for msg in current_chat["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 2. 处理用户输入
    if prompt := st.chat_input("请输入您的问题..."):
        # 2.1 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 2.2 存入历史
        current_chat["messages"].append({"role": "user", "content": prompt})
        
        # 2.3 获取系统回复（调用你的后端）
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🔄 系统思考中... (正在分析用户特征)")
            
            # --- 关键调用点 ---
            # 这里传入 history 是为了让大模型有上下文（如果你的后端支持）
            full_response = get_smart_response_mock(prompt, current_chat["messages"])
            # -----------------
            
            message_placeholder.markdown(full_response)
        
        # 2.4 存入历史
        current_chat["messages"].append({"role": "assistant", "content": full_response})

        # 2.5 自动更新会话标题（仅在第一轮对话结束时刷新）
        # 注意：此时历史记录里应该有2条消息（1条用户，1条系统）
        if len(current_chat["messages"]) == 2:
            current_chat["title"] = prompt[:10] + "..." if len(prompt) > 10 else prompt
            st.rerun() # 此时回复已生成并保存，可以安全刷新

else:
    # 引导页
    st.markdown(
        """
        <div style='text-align: center; margin-top: 50px;'>
            <h3>👋 欢迎使用</h3>
            <p>请点击左侧侧边栏的 <b>"➕ 新建对话"</b> 按钮开始交互。</p>
        </div>
        """,
        unsafe_allow_html=True
    )