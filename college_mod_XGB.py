import pandas as pd
import pyodbc
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV

from xgboost import XGBClassifier

# ==============================
# 1. CONNECT DB
# ==============================
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=10.173.17.46,1400;"
    "DATABASE=WBMCC2024_Main;"
    "Trusted_Connection=yes;"
)

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
df['College'] = df['College'].astype(str).str.strip()
df['Category'] = df['Category'].astype(str).str.strip()
df['Quota'] = df['Quota'].astype(str).str.strip()
df['Course'] = df['Course'].astype(str).str.strip()

df['PH'] = pd.to_numeric(df['PH'], errors='coerce')

df = df.dropna(subset=['Rank', 'College'])

print("After cleaning:", df.shape)

# ==============================
# 4. FEATURE ENGINEERING
# ==============================

# Year Trend
df['Year_Index'] = df['Year'] - df['Year'].min()

# Rank features
df['Rank_Log'] = np.log1p(df['Rank'])

# 🔥 BETTER RANK BIN
df['Rank_Bin'] = pd.cut(
    df['Rank'],
    bins=[0,500,1000,2000,3000,5000,8000,12000,20000,50000,1000000],
    labels=[
        '0-500','500-1k','1k-2k','2k-3k','3k-5k',
        '5k-8k','8k-12k','12k-20k','20k-50k','50k+'
    ]
)

# Feature combos
df['Category_Quota'] = df['Category'] + "_" + df['Quota']
df['Category_Rank'] = df['Category'] + "_" + df['Rank_Bin'].astype(str)

# Interactions
df['Rank_Year'] = df['Rank'] / (df['Year_Index'] + 1)
df['Round_Year'] = df['RoundNo'] * (df['Year_Index'] + 1)

# ==============================
# 5. HANDLE RARE COLLEGES
# ==============================
min_samples = 25
college_counts = df['College'].value_counts()
rare = college_counts[college_counts < min_samples].index
df['College'] = df['College'].replace(rare, 'Other')

print("Unique colleges:", df['College'].nunique())

# ==============================
# 6. FEATURES & TARGET
# ==============================
X = df[[
    'Rank',
    'Rank_Log',
    'Rank_Bin',
    'Year_Index',
    'RoundNo',
    'Quota',
    'Course',
    'Category',
    'Category_Quota',
    'Category_Rank',
    'PH',
    'Rank_Year',
    'Round_Year'
]]

y = df['College']

# Encode target
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# ==============================
# 7. TRAIN TEST SPLIT
# ==============================
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded,
    test_size=0.2,
    random_state=42,
    stratify=y_encoded
)

# ==============================
# 8. PREPROCESSOR
# ==============================
categorical_cols = [
    'Rank_Bin',
    'RoundNo',
    'Quota',
    'Course',
    'Category',
    'Category_Quota',
    'Category_Rank'
]

numeric_cols = [
    'Rank',
    'Rank_Log',
    'PH',
    'Year_Index',
    'Rank_Year',
    'Round_Year'
]

preprocessor = ColumnTransformer([
    ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols),
    ('num', 'passthrough', numeric_cols)
])

# ==============================
# 9. MODELS
# ==============================

# Random Forest
rf_model = RandomForestClassifier(
    n_estimators=500,
    max_depth=25,
    min_samples_split=4,
    min_samples_leaf=2,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)

# XGBoost (base)
xgb_base = XGBClassifier(
    n_estimators=600,
    learning_rate=0.03,
    max_depth=10,
    subsample=0.85,
    colsample_bytree=0.85,
    objective='multi:softprob',
    eval_metric='mlogloss',
    random_state=42,
    n_jobs=-1
)

# 🔥 Calibration (KEY IMPROVEMENT)
xgb_model = CalibratedClassifierCV(xgb_base, method='sigmoid', cv=3)

models = {
    "RandomForest": rf_model,
    "XGBoost": xgb_model
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

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)

    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_pred)

    acc = accuracy_score(y_test_labels, y_pred_labels)
    print(f"Accuracy: {acc:.4f}")

    print("\nClassification Report:")
    print(classification_report(y_test_labels, y_pred_labels, zero_division=0))

    joblib.dump(pipeline, f"{name}_pipeline.pkl")

    results[name] = pipeline

# ==============================
# 11. 2026 PREDICTION
# ==============================
future_year_index = df['Year_Index'].max() + 1

sample = pd.DataFrame({
    'Rank': [5000],
    'Rank_Log': [np.log1p(5000)],
    'Rank_Bin': ['3k-5k'],
    'Year_Index': [future_year_index],
    'RoundNo': [2],
    'Quota': ['SO'],
    'Course': ['MBBS'],
    'Category': ['UR'],
    'Category_Quota': ['UR_SO'],
    'Category_Rank': ['UR_3k-5k'],
    'PH': [0],
    'Rank_Year': [5000 / (future_year_index + 1)],
    'Round_Year': [2 * (future_year_index + 1)]
})

# Use best model
best_model = results["XGBoost"]

probs = best_model.predict_proba(sample)[0]
classes = le.inverse_transform(np.arange(len(probs)))

top_idx = np.argsort(probs)[-5:][::-1]

# 🔥 Normalize top-5 probabilities
top_probs = probs[top_idx]
top_probs = top_probs / top_probs.sum()

print("\n🎯 Top 5 Colleges for 2026:")

for i, idx in enumerate(top_idx):
    prob = top_probs[i] * 100

    if prob > 40:
        tag = "SAFE"
    elif prob > 20:
        tag = "TARGET"
    else:
        tag = "DREAM"

    print(f"{i+1}. {classes[idx]} → {prob:.2f}% ({tag})")