# Instructions: Training & Integrating the ML Trend Classifier

This document explains how to train a Machine Learning model to automatically classify safety observation descriptions into safety `Trend` categories (e.g. PPE, Work at Height, Housekeeping, Electrical, etc.) on Google Colab, and then integrate it here.

## Step 1: Open Google Colab and Upload the Training Data
1. Go to [Google Colab](https://colab.research.google.com/).
2. Create a new notebook.
3. Upload your `CSFA Accumilative data.xlsx` to the session storage.

## Step 2: Write & Run the Training Script in Colab

Copy and execute the following Python code in your Colab notebook to train a TF-IDF + Logistic Regression model on your historical data:

```python
import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report

# 1. Load historical cleaned data
df = pd.read_excel("CSFA Accumilative data.xlsx", sheet_name="CSFA Accumilative data")
df = df[df['Observation Discription '].notna()]
df = df[df['Trend'].notna()]
df = df[~df['Trend'].astype(str).str.lower().str.strip().isin(['nan', 'all', 'common area', 'general'])]

# 2. Get Features and Labels
X = df['Observation Discription '].astype(str)
y = df['Trend'].astype(str).str.strip()

print(f"Total training samples: {len(X)}")
print(f"Unique categories: {y.nunique()}")

# 3. Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42, stratify=y)

# 4. Create a Pipeline (TF-IDF Vectorizer + Logistic Regression Classifier)
model_pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2), stop_words='english')),
    ('classifier', LogisticRegression(class_weight='balanced', max_iter=1000))
])

# 5. Train Model
print("Training model...")
model_pipeline.fit(X_train, y_train)

# 6. Evaluate Model
y_pred = model_pipeline.predict(X_test)
print(classification_report(y_test, y_pred))

# 7. Save Model File
model_filename = 'trend_model.pkl'
with open(model_filename, 'wb') as f:
    pickle.dump(model_pipeline, f)
print(f"Model saved successfully to {model_filename}!")
```

## Step 3: Save the Trained Model File
1. Once the cell completes execution, you will see a file named `trend_model.pkl` in your Colab file explorer on the left.
2. Download `trend_model.pkl` to your computer.
3. Save `trend_model.pkl` in **this dashboard folder** (i.e. alongside `app.py`).

## Step 4: Activating ML Classification in the Dashboard
Once the file `trend_model.pkl` is saved in the directory, you can uncomment/integrate the ML prediction code inside `trend_classifier_ml.py` to automatically suggest categories for newly synchronized observations!
