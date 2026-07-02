import os
import pickle
import pandas as pd

# Path to the trained model pickle file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "trend_model.pkl")


def load_ml_model():
    """
    Attempts to load the trained ML model pipeline.
    """
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, 'rb') as f:
                model = pickle.load(f)
            return model
        except Exception as e:
            print(f"Warning: Failed to load ML model from '{MODEL_PATH}': {e}")
            return None
    return None

# Load model globally on module import
_trend_model = load_ml_model()

def predict_trend(description):
    """
    Predicts the safety trend category for a given observation description.
    
    If the ML model is trained and 'trend_model.pkl' is present:
        It uses the ML model for classification.
    Otherwise:
        It returns an empty string (allowing manual classification in Excel).
    """
    global _trend_model
    
    # Reload model if it was added after starting the app
    if _trend_model is None:
        _trend_model = load_ml_model()
        
    if _trend_model is not None:
        try:
            # Predict category
            pred = _trend_model.predict([str(description)])
            return str(pred[0]).strip()
        except Exception as e:
            print(f"Error predicting trend with ML model: {e}")
            return ""
            
    # Default fallback: return empty string (let user classify manually)
    return ""
