# import sys
import os

# from pathlib import Path

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
import pandas as pd
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import sql as dbsql

from text2scatter import parse_instruction, build_scatterplot, figure_to_png_bytes


# ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv()  # dotenv_path=ENV_PATH)

st.set_page_config(page_title="NL Scatterplot", layout="centered")
st.title("Text To Scatterplot App Demo")

WAREHOUSE_ID = os.getenv("WAREHOUSE_ID")
CATALOG = os.getenv("CATALOG")
SCHEMA = os.getenv("SCHEMA")
TABLE = os.getenv("TABLE")
PROFILE = os.getenv("DATABRICKS_CONFIG_PROFILE")


if not all([WAREHOUSE_ID, CATALOG, SCHEMA, TABLE]):
    raise ValueError("Missing required environment variables")


@st.cache_data
def load_data():

    client = WorkspaceClient(profile=PROFILE) if PROFILE else WorkspaceClient()

    query = f"SELECT * FROM {CATALOG}.{SCHEMA}.{TABLE}"

    res = client.statement_execution.execute_statement(
        statement=query,
        warehouse_id=WAREHOUSE_ID,
        wait_timeout="30s",
    )

    state = res.status.state if res.status else None
    error_msg = res.status.error.message if res.status and res.status.error else None

    if state != dbsql.StatementState.SUCCEEDED:
        raise RuntimeError(f"Query failed. State={state}. Message={error_msg}")

    if not res.manifest or not res.manifest.schema or not res.manifest.schema.columns:
        raise RuntimeError("Query succeeded but schema metadata is missing.")

    cols = [c.name for c in res.manifest.schema.columns]
    data = res.result.data_array if res.result and res.result.data_array else []

    df = pd.DataFrame(data, columns=cols)

    # Cast columns based on Databricks SQL types
    type_map = {
        c.name: c.type_text.lower() for c in res.manifest.schema.columns if c.type_text
    }

    numeric_types = {
        "tinyint",
        "smallint",
        "int",
        "integer",
        "bigint",
        "float",
        "double",
        "decimal",
        "long",
        "short",
    }

    for col, dtype in type_map.items():
        if dtype in numeric_types or dtype.startswith("decimal"):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


df = load_data()

instruction = st.text_input("Instruction", value="Hours_Studied vs Final_Exam_Score")

if st.button("Generate"):
    try:
        spec = parse_instruction(instruction, df)
        fig = build_scatterplot(df, spec)
        png = figure_to_png_bytes(fig)

        st.pyplot(fig)

        st.download_button("Download", data=png, file_name="plot.png", mime="image/png")
    except Exception as e:
        st.error(str(e))
