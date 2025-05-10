import streamlit as st
import pandas as pd
import os

st.title("📊 Visualisation de la production")

if os.path.exists("production.xlsx"):
    df_prod = pd.read_excel("production.xlsx")
    st.subheader("Historique des productions")
    st.dataframe(df_prod)

    st.line_chart(df_prod.groupby("Date")["Quantité"].sum())

else:
    st.warning("Aucune donnée de production disponible.")

if os.path.exists("stock_boutique.xlsx"):
    df_stock = pd.read_excel("stock_boutique.xlsx")
    st.subheader("Stock boutique")
    st.dataframe(df_stock)
else:
    st.warning("Aucune donnée de stock disponible.")
