import streamlit as st
import pandas as pd
import json
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode
from utils.get_data import get_ref_products
from utils.get_data import get_clients
from utils.invoice_maker import invoice_maker

# Function to handle changes in the DataFrame
def df_on_change():
    # Get modified dataframe
    state = st.session_state["df_editor"]
    for index, updates in state["edited_rows"].items():
        # modify each changed value by the user in the session_state df
        for key, value in updates.items():
            st.session_state["df"].loc[st.session_state["df"].index == index, key] = (
                value
            )
        # Get the pr for changed lines
        for key, value in updates.items():
            if (
                key == "Produit"
                and value in product["nom"].tolist()
                and product.loc[product["nom"] == value, "prix"] is not None
            ):
                st.session_state["df"].loc[
                    st.session_state["df"].index == index, "Prix unitaire"
                ] = product.loc[product["nom"] == value, "prix"].iat[0]
            if (
                key == "Produit"
                and value in product["nom"].tolist()
                and product.loc[product["nom"] == value, "tva"] is not None
            ):
                st.session_state["df"].loc[
                    st.session_state["df"].index == index, "TVA"
                ] = product.loc[product["nom"] == value, "tva"].iat[0]

        # # Update the result column based on the input column
        if not (pd.isna(st.session_state["df"].loc[index, "Prix unitaire"])):
            st.session_state["df"].loc[index, "Prix total HT"] = int(
                st.session_state["df"].loc[index, "Quantité"]
            ) * float(st.session_state["df"].loc[index, "Prix unitaire"])

        # st.session_state["df"].loc[st.session_state["df"].index == index, "result"] = 2
        #     float(
        #         st.session_state["df"].loc[
        #             st.session_state["df"].index == index, "Prix Unit"
        #         ][0]
        #     )
        #     * st.session_state["df"].loc[st.session_state["df"].index == index, "q"][0]
        # )

    for ins in state["added_rows"]:
        print(ins)
        st.session_state["df"].loc[len(st.session_state["df"])] = {
            "Produit": "",
            "Quantité": 1,
            "Prix unitaire": None,
            "Prix total HT": None,
        }
    for index in state["deleted_rows"]:
        st.session_state["df"] = st.session_state["df"].drop(index=index)

    st.session_state["df"] = st.session_state["df"].reset_index(drop=True)



st.set_page_config(layout="wide", page_title="Facturation AG-Grid")

product = get_ref_products()



st.header("Produits")
product = st.data_editor(product, key="product", num_rows="dynamic", hide_index=True,column_order=["nom","prix","tva"])



# Initial DataFrame
df = pd.DataFrame(
    columns=[
        "Produit",
        "Quantité",
        "Prix unitaire",
        "TVA",
        "Prix total HT",
    ]
)

clients = get_clients()
client = st.selectbox("Client",options=clients["nom"])

data_presta = st.date_input(
    "Date de la prestation",
    value=None,                      # pas de valeur par défaut
    min_value=None,
    max_value=None,
    key="data_presta"
)


st.header("Facture")

if "df" not in st.session_state:
    st.session_state["df"] = df
st.data_editor(
    st.session_state["df"],
    key="df_editor",
    on_change=df_on_change,
    num_rows="dynamic",
    hide_index=True,
    column_config={
        "Produit": st.column_config.SelectboxColumn(options=product["nom"])
    },
    column_order=["Produit","Quantité", "Prix unitaire", "TVA", "Prix total HT"]
)
print(st.session_state["df"])
print(st.session_state["df_editor"])


st.write(st.session_state["df"])
total_ht = pd.to_numeric(st.session_state["df"]["Prix total HT"], errors='coerce').sum()

mont_ttc= st.session_state["df"]["Prix total HT"]  * (st.session_state["df"]["TVA"] / 100 +1)
total_ttc = mont_ttc.sum()
st.write(f"Total HT : {total_ht:.2f} €")
st.write(f"Total TTC : {total_ttc:.2f} €")


if st.button("Générer la facture") : 
    pdf_filename, insert = invoice_maker(r"template_facture_ASD11.xlsx","data/test.xlsx",st.session_state["df"],clients.loc[clients["nom"] == client].iloc[0],data_presta,
                                         total_ttc, total_ht)
    st.write(insert)
    st.success("Facture générée")
    with open('data/temp.pdf', 'rb') as pdf_file:
        pdf_data = pdf_file.read()
    print(pdf_filename)
    st.write(pdf_filename)
    st.download_button(
        label="Télécharger PDF",
        data=pdf_data,
        file_name=pdf_filename,
        mime="application/pdf"
        )

