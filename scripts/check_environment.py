import sys

import pandas as pd
import streamlit as st
import sqlalchemy
import plotly

print("InsightPilot AI - Environment Check")
print("-" * 40)

print("Python:", sys.version.split()[0])
print("Pandas:", pd.__version__)
print("Streamlit:", st.__version__)
print("SQLAlchemy:", sqlalchemy.__version__)
print("Plotly:", plotly.__version__)

print("-" * 40)
print("Environment ready!")