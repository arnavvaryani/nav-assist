import streamlit as st
import subprocess

st.set_page_config(page_title="LangChain Web Agent", layout="centered")

st.title("🧠 Web Automation Agent")
st.markdown("Type what you want your agent to find or do on the web!")

# Example Prompts
examples = [
    "Find the best deals on iPhones in India",
    "List all video game releases in April 2025",
    "What are the top 5 headlines in tech today?",
    "Compare prices for noise-cancelling headphones",
    "Find cheap hotels in Tokyo for next weekend"
]

task = st.text_area("📝 Enter your task prompt:", value=examples[0], height=100)

if st.button("🚀 Run Agent"):
    with st.spinner("Agent is navigating the web..."):
        try:
            result = subprocess.check_output(
                [r"D:\Nav-Assist\Agent\nav_assist_env311\Scripts\python.exe", "agent_cli.py", task],
                stderr=subprocess.STDOUT,
                text=True
            )
            st.success("✅ Task Completed")
            st.write("### 🔍 Result")
            st.code(result, language="text")
        except subprocess.CalledProcessError as e:
            st.error("💥 Agent crashed")
            st.text(e.output)
