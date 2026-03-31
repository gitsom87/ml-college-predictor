import pandas as pd
import pyodbc
import numpy as np
import joblib
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

# ==============================
# 1. CONNECT TO DATABASE
# ==============================
try:
    # conn = pyodbc.connect(
    #     "DRIVER={ODBC Driver 17 for SQL Server};"
    #     "SERVER=10.173.17.46,1400;"
    #     "DATABASE=WBMCC2024_Main;"
    #     "Trusted_Connection=yes;"
    # )
    conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=LAPTOP-9UCJFBPD\MSSQLSERVER2022;"
    "DATABASE=UR_R2;"
    "Trusted_Connection=yes;"
)
except Exception as e:
    print(f"Connection failed: {e}")
    exit()

# ==============================
# 2. LOAD DATA
# ==============================
query = """
SELECT Rank, Category, Quota, PH,
(select id from MD_Institute where description=c.College)College
FROM ML_CollegeData c
"""
df = pd.read_sql(query, conn)
conn.close()

# ==============================
# 3. CLEAN DATA
# ==============================
df['PH'] = df['PH'].map({'Y': 1, 'N': 0})
df.dropna(inplace=True)

print("Initial shape:", df.shape)

# ==============================
# 4. HANDLE RARE CLASSES (IMPORTANT)
# ==============================
min_samples = 10
college_counts = df['College'].value_counts()
rare = college_counts[college_counts < min_samples].index
df['College'] = df['College'].replace(rare, 'Other')

print("Unique colleges after grouping:", df['College'].nunique())

# ==============================
# 5. SPLIT DATA
# ==============================
X = df[['Rank', 'Category', 'Quota', 'PH']]
y = df['College']

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ==============================
# 6. PREPROCESSOR
# ==============================
categorical_cols = ['Category', 'Quota']
numeric_cols = ['Rank', 'PH']

preprocessor = ColumnTransformer([
    ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols),
    ('num', 'passthrough', numeric_cols)
])

# ==============================
# 7. MODELS
# ==============================
models = {
    "DecisionTree": DecisionTreeClassifier(
        max_depth=5,
        class_weight='balanced',
        random_state=42
    ),
    
    "RandomForest": RandomForestClassifier(
        n_estimators=200,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    ),
    
    "LogisticRegression": LogisticRegression(
        max_iter=3000,
        class_weight='balanced'
    )
}

results = {}

# ==============================
# 8. LOOP THROUGH MODELS
# ==============================
for name, model in models.items():
    print(f"\n{'='*20} {name} {'='*20}")
    
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', model)
    ])
    
    # Train
    pipeline.fit(X_train, y_train)
    
    # Predict
    y_pred = pipeline.predict(X_test)
    
    # Accuracy
    acc = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {acc:.4f}")
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    
    # Save model
    joblib.dump(pipeline, f"{name}_pipeline.pkl")
    
    # Store results
    results[name] = {
        "model": pipeline,
        "accuracy": acc,
        "y_pred": y_pred
    }
    
    # ==============================
    # FEATURE IMPORTANCE
    # ==============================
    if hasattr(model, "feature_importances_"):
        clf = pipeline.named_steps['classifier']
        onehot = pipeline.named_steps['preprocessor'].named_transformers_['cat']
        
        feature_names = (
            onehot.get_feature_names_out(categorical_cols).tolist()
            + numeric_cols
        )
        
        importances = clf.feature_importances_
        
        print("\nTop Features:")
        for fname, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)[:10]:
            print(f"{fname}: {imp:.4f}")
    
    # ==============================
    # TOP-5 PREDICTION
    # ==============================
    sample = pd.DataFrame({
        'Rank': [5000],
        'Category': ['UR'],
        'Quota': ['SO'],
        'PH': [0]
    })
    
    if hasattr(pipeline, "predict_proba"):
        probs = pipeline.predict_proba(sample)[0]
        classes = pipeline.classes_
        
        top_idx = np.argsort(probs)[-5:][::-1]
        
        print("\nTop 5 Predictions:")
        for i in top_idx:
            print(f"{classes[i]} -> {probs[i]*100:.2f}%")

# ==============================
# 9. MODEL COMPARISON
# ==============================
print("\n📊 Model Comparison:")
for name, res in results.items():
    print(f"{name}: {res['accuracy']:.4f}")

# ==============================
# 10. CONFIDENCE ANALYSIS (RF)
# ==============================
print("\n🔍 High Confidence Accuracy (RandomForest)")

rf_model = results["RandomForest"]["model"]
y_pred_rf = results["RandomForest"]["y_pred"]

probs = rf_model.predict_proba(X_test)
probs_df = pd.DataFrame(probs, columns=rf_model.classes_)

probs_df["max_prob"] = probs_df.max(axis=1)

mask = probs_df['max_prob'] >= 0.9
pos = np.where(mask)[0]

y_test_subset = y_test.iloc[pos]
y_pred_subset = y_pred_rf[pos]

if len(pos) > 0:
    acc = accuracy_score(y_test_subset, y_pred_subset)
    print(f"High Confidence Accuracy: {acc:.4f}")
else:
    print("No predictions above confidence threshold")