import streamlit as st
import requests

st.title("Diários Oficiais - Interface")

question = st.text_input("Faça sua pergunta:")

if question:
    try:
        response = requests.post(
            "http://api:8000/query",
            json={"question": question}
        )
        st.json(response.json())
    except Exception as e:
        st.error(f"Erro ao conectar com a API: {str(e)}")
