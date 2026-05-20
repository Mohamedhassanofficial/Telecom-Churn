"""PHASE 1 hello-world — Streamlit Cloud bisect.

If you can read this in the browser, the Streamlit Cloud build + entry
point are healthy and we'll grow the dashboard back one dependency at a
time. If "Oh no" persists even with this file, the cause is at the
Streamlit Cloud account / build-cache level and needs a UI-side
intervention (Manage app -> Reboot -> Clear cache).
"""
import streamlit as st

st.title("Hello from Streamlit Cloud")
st.write("If you can read this, the build + entry-point are healthy.")
st.write("Next step: add the dashboard back one dependency at a time.")
st.success("Phase 1 OK")
