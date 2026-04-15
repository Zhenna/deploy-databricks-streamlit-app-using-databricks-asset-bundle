# deploy-databricks-streamlit-app-using-databricks-asset-bundle

This is tutorial demo to deploy a text-to-scatterplot app to databricks through either CLI or UI.

## What it does
- Takes natural language input
- Parses into scatterplot
- Queries Databricks table
- Displays and allows download

## Example inputs
- Hours_Studied vs Final_Exam_Score
- Sleep_Hours against Final_Exam_Score
- Previous_Scores vs Final_Exam_Score color by Motivation_Level

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```