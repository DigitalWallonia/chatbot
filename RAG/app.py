import os
import asyncio
import streamlit as st

# from utils.sk_setup import initialize_kernel
from scripts.chatbox import set_chatbox_layout, run_chatbot

# Setting up environment variables and kernel
os.environ["OPENAI_API_VERSION"] = "2023-12-01-preview"
os.environ["AZURE_OPENAI_ENDPOINT"] = st.secrets["ENDPOINT"]
os.environ["AZURE_OPENAI_API_KEY"] = st.secrets["KEY"]

# set layout
st.set_page_config(layout="wide")
col1, col2, col3 = st.columns([0.15, 0.1, 0.75], gap="small")


# set function buttons
st.session_state["visualise"] = False

with col1:
    chosen_function = st.radio(label="Choisissez votre cas d'utilisation:", options=["Alignement de taxonomies", "Suggestion de nouvelles branches et catégories", "Suggestion de libellés alternatifs"], index=0)
    
# chatbox
with col3:
    set_chatbox_layout(chosen_function)
    
    if user_input := st.chat_input():
        kernel = "a" 
        asyncio.run(run_chatbot(kernel, user_input, chosen_function))


    
    

