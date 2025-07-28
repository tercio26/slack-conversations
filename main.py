import streamlit as st
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import re
from datetime import datetime

st.markdown("""
<style>
[data-testid="stChatMessageContent"] p { 
    margin-bottom: 4px !important;
    word-break: break-all;
}
[data-testid="stChatMessageContent"] hr { margin: .75rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# Lấy token từ secrets.toml
SLACK_TOKEN = st.secrets["slack"]["user_token"]
client = WebClient(token=SLACK_TOKEN)

INTERNAL_USERS = [
    "U050Z4P6PGW",  # anh Van
    "U03H7QQAN75",  # anh Phu
    "U07PYEYE4R5",  # Trong Dat
]

USER_MAP = {
    "U050Z4P6PGW": {
        "name": "Van Phan",
        "avatar": "https://ui-avatars.com/api/?name=Van+Phan",
    },
    "U03H7QQAN75": {
        "name": "Phu Nguyen",
        "avatar": "https://ca.slack-edge.com/T03H0BP73A9-U03H7QQAN75-76144472a79b-512",
    },
    "U07PYEYE4R5": {
        "name": "Trong Dat",
        "avatar": "https://ca.slack-edge.com/T03H0BP73A9-U07PYEYE4R5-9e832953ff27-512",
    },
    "U0322QW0UNT": {
        "name": "KABURAKI",
        "avatar": "https://ca.slack-edge.com/T01Q8FA80N9-U0322QW0UNT-27fd004dddbf-512",
    },
    "U030J0CKKLM": {
        "name": "Yoshimura",
        "avatar": "https://ca.slack-edge.com/T01Q8FA80N9-U030J0CKKLM-ea50addcdf62-512",
    },
    "U0811H8L6JK": {
        "name": "Yamaguchi",
        "avatar": "https://ca.slack-edge.com/T01Q8FA80N9-U0811H8L6JK-7bab4bdca1d9-512",
    }
}

st.set_page_config(page_title="Slack Conversation Viewer", layout="centered")
st.title("🧵 Xem nội dung Slack Conversation")

st.markdown("Dán link Slack conversation vào ô bên dưới.")

# Hàm parse Slack message URL
def extract_slack_conversation_info(url: str):
    match = re.search(r"/archives/([A-Z0-9]+)/p(\d{16})", url)
    if match:
        channel_id = match.group(1)
        raw_ts = match.group(2)
        conversation_ts = f"{raw_ts[:10]}.{raw_ts[10:]}"
        return channel_id, conversation_ts
    return None, None


def replace_mentions(text):
    def repl(match):
        user_id = match.group(1)
        return f"@{USER_MAP.get(user_id, user_id).get("name")}"

    return re.sub(r"<@([A-Z0-9]+)>", repl, text)

def format_slack_ts(ts_str: str) -> str:
    try:
        ts_float = float(ts_str)
        dt = datetime.fromtimestamp(ts_float)
        return dt.strftime("%Y/%m/%d %H:%M:%S")
    except:
        return ""

def fetch_messages(channel_id, ts, cursor=None):
    try:
        params = {
            "channel": channel_id,
            "ts": ts,
            "limit": 15,
            "inclusive": False
        }
        if cursor:
            params["cursor"] = cursor

        response = client.conversations_replies(**params)
        return response["messages"], response.get("response_metadata", {}).get("next_cursor")
    except SlackApiError as e:
        st.error(f"Lỗi Slack API: {e.response['error']}")
        return [], None

# Nhập link Slack
with st.form("fetch_conversation"):
    slack_url = st.text_input("Slack Conversation URL", placeholder="https://.../archives/Cxxx/pXXXXXXXXXXXXXX")
    submitted = st.form_submit_button("🔍 Xem nội dung")

conversation_ts = None

# Xử lý sau khi nhấn
if submitted:
    channel_id, conversation_ts = extract_slack_conversation_info(slack_url.strip())

    if not channel_id or not conversation_ts:
        st.error("❌ Không thể trích xuất thông tin từ link.")
    else:
        # Reset state nếu là conversation mới
        if st.session_state.get("current_conversation") != conversation_ts:
            st.session_state["messages"] = []
            st.session_state["next_cursor"] = None
            st.session_state["current_conversation"] = conversation_ts

        # Fetch initial messages
        with st.spinner("🔄 Đang tải tin nhắn..."):
            new_messages, cursor = fetch_messages(channel_id, conversation_ts)
            st.session_state["messages"] = new_messages
            st.session_state["next_cursor"] = cursor


# --- Hiển thị tin nhắn (nếu có) ---
if "messages" in st.session_state and st.session_state["messages"]:
    st.write(f"🎯 {len(st.session_state['messages']) - 1} replies")

    for msg in reversed(st.session_state["messages"]):
        ts = msg.get("ts", "")
        is_root = ts == conversation_ts

        if is_root and st.session_state.get("next_cursor"):
            st.write('...')

        user_id = msg.get("user", "")
        user = USER_MAP.get(user_id, {"name": user_id, "avatar": None})
        user_name = user["name"]
        user_avatar = user["avatar"]

        text = replace_mentions(msg.get("text", ""))
        is_internal = user_id in INTERNAL_USERS
        timestamp = format_slack_ts(ts)

        role = "assistant" if is_internal else "user"
        with st.chat_message(role, avatar=user_avatar):
            st.markdown(f"**{user_name}** <span style='font-size:12px;color:gray;'>({timestamp})</span>",
                        unsafe_allow_html=True)
            st.markdown(text, unsafe_allow_html=True)


# --- Button tải thêm ---
if st.session_state.get("next_cursor"):
    if st.button("⬇️ Tải thêm tin cũ"):
        with st.spinner("🔄 Đang tải thêm..."):
            channel_id = extract_slack_conversation_info(slack_url)[0]
            conversation_ts = st.session_state["current_conversation"]
            new_messages, cursor = fetch_messages(channel_id, conversation_ts, st.session_state["next_cursor"])
            st.session_state["messages"].extend(new_messages)
            st.session_state["next_cursor"] = cursor
            st.rerun()