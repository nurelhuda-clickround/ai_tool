import streamlit as st
import os
import json
import uuid
import plotly.io as pio
from streamlit.components.v1 import html
# from streamlit_cookies_manager import EncryptedCookieManager
from chat_history import init_db, save_message, load_all_conversations,load_conversations, load_conversation_messages, delete_conversation, save_file_metadata, save_chart_metadata, load_file_metadata, load_chart_metadata, save_session, load_session, delete_session
from utils import initialize_session_state,build_index, get_multi_agent, generate_document, determine_file_generation, generate_chart, load_excel_to_db
# Replace the existing cookie initialization
from cookie_utils import get_cookie_manager


# -------------------------
# Page Configuration
# -------------------------
st.set_page_config(
    page_title="HXAssist - ERP Chat",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# -------------------------
# Custom CSS
# -------------------------
st.markdown("""
    <style>
    .stApp { background-color: #f0f4f8; font-family: 'Inter', sans-serif; }
    .main-title { color: #006d77; font-size: 2.3em; text-align: start; margin-bottom: 0.2em; }
    .subtitle { color: #4a5568; font-size: 1.1em; text-align: start; margin-bottom: 1.5em; }
    .chat-message-user {
        background-color: #83c5be; color: #ffffff; border-radius: 12px 12px 0 12px;
        padding: 12px 16px; margin: 8px 8px 10px auto; max-width: 70%;
        word-wrap: break-word; animation: fadeIn 0.3s ease-in;
    }
    .chat-message-assistant {
        background-color: #ffffff; 
        color: #2d3748; 
        border-radius: 0 12px 12px 12px;
        padding: 12px 16px; 
        margin: 8px 10px 8px 0;
        max-width: 80%;
        word-wrap: break-word; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        animation: fadeIn 0.3s ease-in;
    }
    .stButton > button {
        background-color: #006d77; color: white; border-radius: 8px; padding: 8px 16px;
        transition: background-color 0.3s; margin: 10px auto; display: block;
    }
    .stButton > button:hover { background-color: #008b94; }
    .stTextInput > div > input { border-radius: 12px; border: 1px solid #83c5be; padding: 10px; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); }
                        to { opacity: 1; transform: translateY(0); } }
    .stdownload-button {     
        width: 100%;
        margin: 0 10%; 
    }
    .stdownload-button button{
        margin: 8px 50%;
    }  
    [data-testid="stFileUploader"] {
        margin-top: 10px;
        padding: 8px;
        border: 1px dashed #83c5be;
        border-radius: 12px;
        background-color: #f9fafa;
    }
    .delete-button {
        background-color: #e53e3e !important;
        color: white !important;
        padding: 4px 8px !important;
        margin-left: 5px !important;
        font-size: 0.8em !important;
    }
    .delete-button:hover {
        background-color: #c53030 !important;
    }
    .st-emotion-cache-159b5ki {
        justify-content: center;
    }
    .st-emotion-cache-1u02ojh {
        gap: 0.2rem;
    }
    .st-emotion-cache-1permvm {
        gap: 0.1rem;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------
# Initialize Cookie Manager
# -------------------------
cookies = get_cookie_manager()
if not cookies.ready():
    st.error("⚠️ Cookie manager is not ready. Please refresh the page or check your configuration.")
    st.stop()


# -------------------------
# Session State Initialization
# -------------------------
initialize_session_state()

init_db()

# -------------------------
# Restore Login Session
# -------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    session_id = cookies.get("session_id")
    if session_id:
        session = load_session(session_id)
        if session:
            st.session_state["authenticated"] = True
            st.session_state["user"] = session["username"]

if not st.session_state["authenticated"]:
    st.switch_page("pages/login.py")
    st.stop()

# if not st.session_state.get("authenticated", False):
#     try:
#         st.switch_page("pages/login.py")  # redirect to login
#     except Exception:
#         st.warning("🔐 Please log in to continue.")
#         st.stop()

# -------------------------
# Header with Login/Logout
# -------------------------
col1, col2 = st.columns([4,1])
with col1:
    st.markdown('<div class="main-title">👋 Welcome to your AI Assistant!</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">How can I assist you today? Your smart assistant for quick, reliable answers - Just ask.</div>', unsafe_allow_html=True)
with col2:
    if st.session_state.get("authenticated", False):
        if st.button("Logout"):
            try:
                if st.session_state.get("user") and st.session_state.get("session_id"):
                    delete_session(st.session_state["session_id"])
                    cookies["session_id"] = ""
                    cookies.save()
                # Clear session state and reinitialize
                for key in list(st.session_state.keys()):
                    if key not in ("session_id",):
                        del st.session_state[key]
                if "history" in st.session_state:
                    del st.session_state["history"]  # clear guest chat if any
                st.session_state["session_id"] = str(uuid.uuid4())
                initialize_session_state()
                st.session_state.clear()
                cookies["session_id"] = ""
                cookies.save()
                st.rerun()
            except Exception as e:
                st.error(f"Error during logout: {e}")
    else:
        if st.button("Login"):
            try:
                st.switch_page("pages/login.py")
            except Exception as e:
                st.error(f"Error redirecting to login: {e}")

# -------------------------
# Conversation Initialization
# -------------------------
username = st.session_state.get("user")
if username:
    if username not in st.session_state.conversations:
        st.session_state.conversations[username] = load_conversations(username)
    if username not in st.session_state.active_conv:
        new_conv_id = str(uuid.uuid4())
        st.session_state.active_conv[username] = new_conv_id
        st.session_state.conversations[username].insert(0, new_conv_id)

# -------------------------
# Conversation History Helpers
# -------------------------
def build_full_user_history(username):
    """Load all messages across all conversations for a user, sorted by time."""
    if not username:
        return []
    return load_all_conversations(username)

def get_conversation_history():
    """Return appropriate conversation history based on authentication state."""
    if st.session_state.get("authenticated", False) and st.session_state.get("user"):
        username = st.session_state["user"]
        active_conv_id = st.session_state.active_conv.get(username)
        if active_conv_id:
            return load_conversation_messages(username, active_conv_id)
        return []
    else:
        if "history" not in st.session_state:
            st.session_state.history = []
        return st.session_state.history

# -------------------------
# Determine agent history
# -------------------------
if st.session_state.get("authenticated", False) and username:
    all_history = build_full_user_history(username)
else:
    all_history = st.session_state.get("history", [])

# -------------------------
# Sidebar (for logged-in users only)
# -------------------------
with st.sidebar:
    st.markdown("""
    <style>
    /* Sidebar background */
    [data-testid="stSidebar"] {
        background-color: #f5f7fa;
        padding: 1rem;
    }

    /* Section Title */
    .sidebar-section-title {
        font-weight: 600;
        color: #333;
        font-size: 15px;
        margin-bottom: 10px;
    }

    /* Conversation item container */
    .conv-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 10px;
        border-radius: 8px;
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        margin-bottom: 8px;
        transition: all 0.2s ease;
    }

    .conv-item:hover {
        background-color: #eef2fd;
        border-color: #cdd7ff;
    }

    /* Conversation label */
    .conv-label {
        color: #333;
        font-size: 14px;
        font-weight: 400;
        text-overflow: ellipsis;
        overflow: hidden;
        white-space: nowrap;
    }

    /* Delete button */
    .delete-btn {
        background: none;
        border: none;
        color: #777;
        font-size: 16px;
        cursor: pointer;
        padding: 0;
        margin: 0;
    }

    .delete-btn:hover {
        color: #e74c3c;
    }

    /* New Conversation button */
    .new-btn {
        width: 100%;
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .new-btn:hover {
        background-color: #0056b3;
    }

    /* Divider */
    .sidebar-divider {
        border-top: 1px solid #ddd;
        margin: 1rem 0;
    }

    /* Streamlit button styling for delete */
    .stButton > button.delete-btn {
        background: none;
        border: none;
        color: #777;
        font-size: 16px;
        padding: 0;
        margin: 0;
        min-height: 20px;
        line-height: 1;
    }

    .stButton > button.delete-btn:hover {
        color: #e74c3c;
    }
    .stButton > button {
        background-color: #006d77;
        color: white;
        border-radius: 8px;
        padding: 5px 5px;
        transition: background-color 0.3s;
        margin: 10px auto;
        display: block;
        text-overflow: ellipsis;
        overflow: hidden;
        white-space: nowrap;
        /* color: #333; */
        font-size: 14px;
        font-weight: 400;
        display: flex
    ;
        justify-content: space-between;
        align-items: center;
        padding: 8px 10px;
        border-radius: 8px;
        /* background-color: #ffffff; */
        border: 1px solid #e0e0e0;
        margin-bottom: 8px;
        transition: all 0.2s 
    ease;
    }
    .st-emotion-cache-zh2fnc {
        width: 100%;
                }
    </style>
    """, unsafe_allow_html=True)
    if username:
        st.subheader("💬 Conversations")
        convs = st.session_state.conversations.get(username, [])
        for cid in convs:
            msgs = load_conversation_messages(username, cid, limit=1)
            label = msgs[0]["content"][:16] + "..." if msgs else "..."
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(label, key=f"conv_{cid}"):
                    st.session_state.active_conv[username] = cid
                    st.session_state.generated_files = load_file_metadata(username, cid)
                    st.session_state.generated_charts = load_chart_metadata(username, cid)
            with col2:
                if st.button("🗑️", key=f"delete_{cid}", help="Delete this conversation", type="secondary", use_container_width=True):
                    delete_conversation(username, cid)
                    st.session_state.conversations[username].remove(cid)
                    if st.session_state.active_conv.get(username) == cid:
                        if st.session_state.conversations[username]:
                            st.session_state.active_conv[username] = st.session_state.conversations[username][0]
                        else:
                            new_conv_id = str(uuid.uuid4())
                            st.session_state.active_conv[username] = new_conv_id
                            st.session_state.conversations[username].insert(0, new_conv_id)
                    st.rerun()

        if st.button("➕ New Conversation"):
            new_cid = str(uuid.uuid4())
            st.session_state.active_conv[username] = new_cid
            st.session_state.conversations[username].insert(0, new_cid)

# -------------------------
# Display Chat History
# -------------------------
display_history = get_conversation_history()

# -------------------------
# Initialize Agent
# -------------------------
if "agent" not in st.session_state:
    if os.path.exists("data") and os.listdir("data"):
        with st.spinner("🔄 Loading existing documents and initializing agent..."):
            for f in os.listdir("data"):
                file_path = os.path.join("data", f)
                if f.endswith((".xlsx", ".xls")):
                    load_excel_to_db(file_path)
            docs, meta, faiss_index = build_index("data")
            st.session_state.agent = get_multi_agent(None, docs, meta, conversation_history=all_history)
    else:
        st.info("📂 No documents uploaded yet. You can still ask general questions.")
        st.stop()

# -------------------------
# Render Messages
# -------------------------
current_user = username if username else "guest"
current_conv = (
    st.session_state.active_conv.get(username)
    if username
    else "guest_default"
)

for i, chat in enumerate(display_history):
    if chat["role"] == "user":
        with st.chat_message("user"):
            st.markdown(f'<div class="chat-message-user">{chat["content"]}</div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant"):
            st.markdown(f'<div class="chat-message-assistant">{chat["content"]}</div>', unsafe_allow_html=True)
            for file_info in st.session_state.generated_files:
                if (
                    file_info.get("username") == current_user
                    and file_info.get("conv_id") == current_conv
                    and file_info.get("history_index") == i
                ):
                    try:
                        with open(file_info["file_path"], "rb") as f:
                            file_name = os.path.basename(file_info["file_path"])
                            mime_types = {
                                "pdf": "application/pdf",
                                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            }
                            file_ext = file_name.split('.')[-1]
                            mime_type = mime_types.get(file_ext, "application/octet-stream")
                            st.download_button(
                                label=f"📥 Download {file_name}",
                                data=f,
                                file_name=file_name,
                                mime=mime_type,
                                key=f"download_{file_name}_{i}"
                            )
                    except Exception as e:
                        st.error(f"Failed to attach file: {e}")
            for chart_info in st.session_state.generated_charts:
                if (
                    chart_info.get("username") == current_user
                    and chart_info.get("conv_id") == current_conv
                    and chart_info.get("history_index") == i
                ):
                    if chart_info["chart"].get("error"):
                        st.error(chart_info["chart"]["error"])
                    elif chart_info["chart"]["render_method"] == "plotly":
                        chart_data = chart_info["chart"]["chart_data"]
                        if isinstance(chart_data, str):
                            try:
                                chart_data = json.loads(chart_data)
                            except json.JSONDecodeError:
                                st.error("⚠️ Invalid Plotly chart data format.")
                                chart_data = None
                        st.plotly_chart(chart_data, use_container_width=True)
                    elif chart_info["chart"]["render_method"] == "chartjs":
                        chartjs_html = f"""
                        <canvas id="chart_new_{i}"></canvas>
                        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                        <script>
                        new Chart(document.getElementById('chart_new_{i}'), {json.dumps(chart_info["chart"]["chart_data"])});
                        </script>
                        """
                        html(chartjs_html, height=400)

# -------------------------
# Handle New Input
# -------------------------
if query := st.chat_input("Ask a question about ERP, invoices, policies, or request a chart..."):
    with st.chat_message("user"):
        st.markdown(f'<div class="chat-message-user">{query}</div>', unsafe_allow_html=True)

    conversation_str = "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}" for msg in all_history
    )
    if conversation_str:
        conversation_str += "\n"
    conversation_str += f"User: {query}"

    generate_file, file_format, should_generate_chart = determine_file_generation(query, conversation_str)

    full_response = ""
    chart_info = None
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("🧠 Thinking..."):
            try:
                agent_response = st.session_state.agent.invoke({"input": conversation_str})
                if isinstance(agent_response, dict):
                    response_text = agent_response.get("output", agent_response.get("answer", str(agent_response)))
                else:
                    response_text = str(agent_response)

                for chunk in response_text.split():
                    full_response += chunk + " "
                    message_placeholder.markdown(
                        f'<div class="chat-message-assistant">{full_response}▌</div>',
                        unsafe_allow_html=True
                    )
                message_placeholder.markdown(
                    f'<div class="chat-message-assistant">{full_response.strip()}</div>',
                    unsafe_allow_html=True
                )
            except Exception as e:
                full_response = f"⚠️ Error generating response: {e}"
                message_placeholder.markdown(
                    f'<div class="chat-message-assistant">{full_response}</div>',
                    unsafe_allow_html=True
                )

        if should_generate_chart:
            with st.spinner("📊 Generating chart..."):
                try:
                    chart_info = generate_chart(query, agent=st.session_state.agent, retrieved_info=full_response.strip())
                    if chart_info.get("error"):
                        st.error(chart_info["error"])
                    elif chart_info["render_method"] == "plotly":
                        st.plotly_chart(chart_info["chart_data"], use_container_width=True)
                    elif chart_info["render_method"] == "chartjs":
                        chartjs_html = f"""
                        <canvas id="chart_new_{len(display_history)}"></canvas>
                        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                        <script>
                        new Chart(document.getElementById('chart_new_{len(display_history)}'), {json.dumps(chart_info["chart_data"])});
                        </script>
                        """
                        html(chartjs_html, height=400)
                except Exception as e:
                    st.error(f"Failed to generate chart: {e}")

        generated_file_path = None
        if generate_file and file_format:
            with st.spinner(f"📄 Generating {file_format.upper()} document..."):
                try:
                    generated_file_path = generate_document(
                        query,
                        file_format=file_format,
                        agent=st.session_state.agent,
                        retrieved_info=full_response.strip(),
                        # chart=chart_info
                    )
                    with open(generated_file_path, "rb") as f:
                        file_name = os.path.basename(generated_file_path)
                        mime_types = {
                            "pdf": "application/pdf",
                            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        }
                        file_ext = file_name.split('.')[-1]
                        mime_type = mime_types.get(file_ext, "application/octet-stream")
                        st.download_button(
                            label=f"📥 Download {file_name}",
                            data=f,
                            file_name=file_name,
                            mime=mime_type,
                            key=f"download_{file_name}_new_{len(display_history)}"
                        )
                except Exception as e:
                    st.error(f"Failed to attach file: {e}")

    if username:
        active_id = st.session_state.active_conv.get(username)
        if full_response.strip():
            save_message(username, active_id, "user", query)
            save_message(username, active_id, "assistant", full_response.strip())
        display_history = load_conversation_messages(username, active_id)
        history_index = len(display_history) - 1 if display_history else 0
    else:
        if "history" not in st.session_state:
            st.session_state.history = []
        st.session_state.history.append({"role": "user", "content": query})
        st.session_state.history.append({"role": "assistant", "content": full_response.strip()})
        history_index = len(st.session_state.history) - 1

    if generate_file and file_format and generated_file_path:
        file_info = {
            "username": current_user,
            "conv_id": current_conv,
            "file_path": generated_file_path,
            "query": query,
            "history_index": history_index
        }
        st.session_state.generated_files.append(file_info)
        if username:
            save_file_metadata(username, current_conv, file_path=generated_file_path, query=query, history_index=history_index)

    if should_generate_chart and chart_info is not None and not chart_info.get("error"):
        chart_data = chart_info["chart_data"]
        if chart_info["render_method"] == "plotly":
            # Only call to_json() if chart_data is a Plotly figure
            chart_data = chart_data.to_json() if hasattr(chart_data, "to_json") else chart_data
        chart_metadata = {
            "username": current_user,
            "conv_id": current_conv,
            "chart": {
                "chart_data": chart_data,
                "render_method": chart_info["render_method"]
            },
            "query": query,
            "history_index": history_index
        }
        st.session_state.generated_charts.append(chart_metadata)
        if username:
            save_chart_metadata(username, current_conv, chart_data, chart_info["render_method"], query, history_index)

# -------------------------
# Footer
# -------------------------
st.markdown(
    '<div style="text-align: center; color: #718096; margin-top: 20px; font-size: 0.9em;">HXAssist v1.0 | Powered by ClickRound Technologies</div>',
    unsafe_allow_html=True
)

# Show upload below chat input
with st.container():
    uploaded_files = st.file_uploader(
        "📤 Upload documents (PDF or Excel)",
        type=["pdf", "xlsx", "xls"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="chat_file_uploader"
    )

if uploaded_files:
    new_files = [f for f in uploaded_files if f.name not in [uf.name for uf in st.session_state.get("uploaded_files", [])]]
    if new_files:
        os.makedirs("data", exist_ok=True)
        for f in new_files:
            file_path = os.path.join("data", f.name)
            with open(file_path, "wb") as out:
                out.write(f.getbuffer())
            
            if file_path.endswith((".xlsx", ".xls")):
                with st.spinner(f"📊 Loading {f.name} into database..."):
                    load_excel_to_db(file_path)
        
        st.session_state.uploaded_files = st.session_state.get("uploaded_files", []) + new_files
        st.success("✅ Files uploaded and data loaded successfully! Re-indexing...")

        with st.spinner("🔄 Re-indexing with uploaded documents..."):
            docs, meta, faiss_index = build_index("data")
            st.session_state.agent = get_multi_agent(None, docs, meta,conversation_history=all_history)

