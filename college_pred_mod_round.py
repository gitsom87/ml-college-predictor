import pandas as pd
import pyodbc
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

# ==============================
# 1. CONNECT TO DATABASE
# ==============================
try:
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=10.173.17.46,1400;"
        "DATABASE=WBMCC2024_Main;"
        "Trusted_Connection=yes;"
    )
except Exception as e:
    print(f"Connection failed: {e}")
    exit()

# ==============================
# 2. LOAD DATA
# ==============================
query = """
SELECT 
    [Year],
    RoundNo,
    [Rank],
    College,
    Quota,
    Course,
    Category,
    PH
FROM ML_CollegeAdmissionRoundWise
"""
df = pd.read_sql(query, conn)
conn.close()

print("Initial shape:", df.shape)

# ==============================
# 3. CLEAN DATA
# ==============================
df['PH'] = df['PH'].map({'Y': 1, 'N': 0})
df.dropna(inplace=True)

# ==============================
# 4. RANK BIN (VERY IMPORTANT)
# ==============================
df['Rank_Bin'] = pd.cut(
    df['Rank'],
    bins=[0, 1000, 3000, 5000, 10000, 20000, 50000, 1000000],
    labels=['0-1k','1k-3k','3k-5k','5k-10k','10k-20k','20k-50k','50k+']
)

# ==============================
# 5. HANDLE RARE COLLEGES
# ==============================
min_samples = 10
college_counts = df['College'].value_counts()
rare = college_counts[college_counts < min_samples].index
df['College'] = df['College'].replace(rare, 'Other')

print("Unique colleges:", df['College'].nunique())

# ==============================
# 6. FEATURES & TARGET
# ==============================
X = df[[
    'Rank',
    'Rank_Bin',
    'Year',
    'RoundNo',
    'Quota',
    'Course',
    'Category',
    'PH'
]]

y = df['College']

# ==============================
# 7. TRAIN TEST SPLIT
# ==============================
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ==============================
# 8. PREPROCESSOR
# ==============================
categorical_cols = [
    'Rank_Bin',
    'Year',
    'RoundNo',
    'Quota',
    'Course',
    'Category'
]

numeric_cols = ['Rank', 'PH']

preprocessor = ColumnTransformer([
    ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols),
    ('num', 'passthrough', numeric_cols)
])

# ==============================
# 9. MODELS
# ==============================
models = {
    "DecisionTree": DecisionTreeClassifier(
        max_depth=10,
        class_weight='balanced',
        random_state=42
    ),
    
    "RandomForest": RandomForestClassifier(
        n_estimators=400,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    ),
    
    "GradientBoosting": GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.1,
        max_depth=5
    )
}

results = {}

# ==============================
# 10. TRAIN LOOP
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
    
    results[name] = {
        "model": pipeline,
        "accuracy": acc,
        "y_pred": y_pred
    }
    
    # ==============================
    # TOP-5 PREDICTION
    # ==============================
    sample = pd.DataFrame({
        'Rank': [5000],
        'Rank_Bin': ['3k-5k'],
        'Year': [2023],
        'RoundNo': [2],
        'Quota': ['SO'],
        'Course': ['MBBS'],
        'Category': ['UR'],
        'PH': [0]
    })
    
    probs = pipeline.predict_proba(sample)[0]
    classes = pipeline.classes_
    
    top_idx = np.argsort(probs)[-5:][::-1]
    
    print("\nTop 5 Predictions:")
    for i in top_idx:
        print(f"{classes[i]} -> {probs[i]*100:.2f}%")

# ==============================
# 11. MODEL COMPARISON
# ==============================
print("\n📊 Model Comparison:")
for name, res in results.items():
    print(f"{name}: {res['accuracy']:.4f}")

# ==============================
# 12. TOP-3 ACCURACY (BEST METRIC)
# ==============================
def top_n_accuracy(model, X, y, n=3):
    probs = model.predict_proba(X)
    top_n = np.argsort(probs, axis=1)[:, -n:]
    
    correct = 0
    for i in range(len(y)):
        if y.iloc[i] in model.classes_[top_n[i]]:
            correct += 1
    
    return correct / len(y)

rf_model = results["RandomForest"]["model"]
top3 = top_n_accuracy(rf_model, X_test, y_test, 3)

print(f"\n🔥 RandomForest Top-3 Accuracy: {top3:.4f}")