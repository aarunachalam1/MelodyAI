from fastmcp import FastMCP
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
import os
import joblib
import matplotlib.pyplot as plt
import numpy as np

server = FastMCP(name="DataScienceTools")
datasets = {}
models = {}

MODEL_DIR = "saved_models"
os.makedirs(MODEL_DIR, exist_ok=True)

@server.tool()
def load_csv(file_path: str):
    df = pd.read_csv(file_path)
    datasets[file_path] = df
    return {
        "columns": df.columns.tolist(), 
        "num_rows": len(df),
        "status": "loaded"
    }

@server.tool()
def summarize_data(file_path: str):
    if file_path not in datasets:
        return {"error": "Dataset not loaded. Call load_csv first."}
    df = datasets[file_path]
    return df.describe().to_dict()
# Add plot=true field
@server.tool()
def run_linear_regression(file_path: str, x_cols, y_col: str, model_name: str = None):
    if file_path not in datasets:
        return {"error": "Dataset not loaded. Call load_csv first."}
    
    if isinstance(x_cols, str):
        x_cols = [x_cols]
    df = datasets[file_path]
    X = df[x_cols]
    y = df[y_col]

    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)

    results = {
        "coef": model.coef_.tolist(),
        "intercept": model.intercept_.item() if hasattr(model.intercept_, "item") else model.intercept_,
        "R2": r2_score(y, y_pred),
        "MSE": mean_squared_error(y, y_pred)
    }

    model_name = model_name or f"model_{os.path.basename(file_path).replace('.csv','')}_{y_col}"
    models[model_name] = model

    joblib.dump(model, os.path.join(MODEL_DIR, f"{model_name}.pkl"))

    return {"model_name": model_name, "results": results}

@server.tool()
def predict_linear_regression(model_name: str, x_values):
    model = models.get(model_name)
    if model is None:
        model_path = os.path.join(MODEL_DIR, f"{model_name}.pkl")
        if os.path.exists(model_path):
            model = joblib.load(model_path)
            models[model_name] = model
        else:
            return {"error": f"Model '{model_name}' not found."}
        
    if isinstance(x_values[0], (int, float)):
        x_values = [x_values]
    
    preds = model.predict(x_values).tolist()
    return {"predictions": preds}

'''@server.tool()
def plot_linear_regression(model_name: str)'''
if __name__ == "__main__":
    server.run()