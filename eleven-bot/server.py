from fastmcp import FastMCP
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
import os
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pickle

server = FastMCP(name="DataScienceTools")
STATE_FILE = "server_state.pkl"
MODEL_DIR = "saved_models"
PLOTS_DIR = os.path.join(os.getcwd(), "static", "plots")


os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)

def save_state():
    with open(STATE_FILE, "wb") as f:
        pickle.dump({"datasets": datasets, "models": models}, f)

def load_state():
    global datasets, models
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "rb") as f:
            state = pickle.load(f)
            datasets.update(state.get("datasets", {}))
            models.update(state.get("models", {}))


datasets = {}
models = {}
load_state()

@server.tool()
def load_csv(file_path: str):
    df = pd.read_csv(file_path)
    datasets[file_path] = df
    save_state()
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
    save_state()
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

@server.tool()
def list_datasets():
    return list(datasets.keys())

@server.tool()
def list_models():
    return list(models.keys())

@server.tool()
def plot_data(file_path: str, x_col: str = None, y_col: str = None, plot_type: str = "scatter"):
    """
    Plot data from a loaded dataset.
    
    Args:
        file_path: The dataset file path used in load_csv.
        x_col: The column for the x-axis.
        y_col: The column for the y-axis (optional for histogram).
        plot_type: "scatter" or "hist"
    """
    if file_path not in datasets:
        return {"error": "Dataset not loaded. Call load_csv first."}
    
    df = datasets[file_path]
    plot_path = os.path.join(PLOTS_DIR, f"{os.path.basename(file_path).replace('.csv', '')}_{plot_type}.png")

    plt.figure(figsize=(6, 4))
    if plot_type == "scatter":
        if not x_col or not y_col:
            return {"error": "For scatter plots, both x_col and y_col are required."}
        plt.scatter(df[x_col], df[y_col], alpha=0.7)
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.title(f"Scatter Plot: {x_col} vs {y_col}")

    elif plot_type == "hist":
        if not x_col:
            return {"error": "For hist plots, x_col is required."}
        plt.hist(df[x_col], bins=20, alpha=0.7)
        plt.xlabel(x_col)
        plt.title(f"Histogram of {x_col}")

    else:
        return {"error": "Invalid plot_type. Choose 'scatter' or 'hist'."}

    plt.tight_layout()
    file_id = uuid.uuid4().hex
    filename = f"{plot_created}_{file_id}.png"
    plot_path = os.path.join(PLOTS_DIR, filename)
    plt.savefig(plot_path)
    plt.close()

    url_path = "/static/plots/" + filename
    return {
        "status": "plot_created",
        "plot_path": plot_path,
        "plot_url": url_path
    }

if __name__ == "__main__":
    server.run()