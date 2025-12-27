# cookie_manager.py
import os
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

def get_cookie_manager():
    cookies = EncryptedCookieManager(
        prefix="hxassist_",
        password=os.getenv(
            "COOKIE_PASSWORD",
            "x7$9kP!mQwZ2vN8rT5jYhL3pF9bXqW2zR4tY6u"
        )
    )
    if not cookies.ready():
        st.info("🔄 Syncing cookies...")
        st.stop()
    return cookies
