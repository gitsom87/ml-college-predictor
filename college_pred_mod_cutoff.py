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

# 🔥 QUOTA FIX
def map_quota(x):
    x = str(x).upper()
    if 'STATE' in x:
        return 'SQ'
    elif 'MANAGEMENT' in x:
        return 'MQ'
    elif 'NRI' in x:
        return 'NRI'
    else:
        return 'OTHER'

df['Quota'] = df['Quota'].apply(map_quota)

# PH numeric
df['PH'] = pd.to_numeric(df['PH'], errors='coerce')

# Drop bad rows
df = df.dropna(subset=['Rank', 'College'])

print("After cleaning:", df.shape)

# ==============================
# 4. 🔥 CUTOFF FEATURE (GAME CHANGER)
# ==============================
cutoff_df = df.groupby(
    ['Year', 'College', 'Category', 'Quota', 'RoundNo']
)['Rank'].max().reset_index()

cutoff_df.rename(columns={'Rank': 'Cutoff_Rank'}, inplace=True)

# shift to next year
cutoff_df['Year'] = cutoff_df['Year'] + 1

# merge
df = df.merge(
    cutoff_df,
    on=['Year', 'College', 'Category', 'Quota', 'RoundNo'],
    how='left'
)

df['Cutoff_Rank'] = df['Cutoff_Rank'].fillna(df['Rank'].max())
df['Rank_vs_Cutoff'] = df['Rank'] - df['Cutoff_Rank']

# ==============================
# 5. FEATURE ENGINEERING
# ==============================
df['Year_Index'] = df['Year'] - df['Year'].min()
df['Rank_Log'] = np.log1p(df['Rank'])

df['Rank_Bin'] = pd.cut(
    df['Rank'],
    bins=[0,500,1000,2000,3000,5000,8000,12000,20000,50000,1000000],
    labels=[
        '0-500','500-1k','1k-2k','2k-3k','3k-5k',
        '5k-8k','8k-12k','12k-20k','20k-50k','50k+'
    ]
)

df['Category_Quota'] = df['Category'] + "_" + df['Quota']
df['Category_Rank'] = df['Category'] + "_" + df['Rank_Bin'].astype(str)

df['Rank_Year'] = df['Rank'] / (df['Year_Index'] + 1)
df['Round_Year'] = df['RoundNo'] * (df['Year_Index'] + 1)

# ==============================
# 6. HANDLE RARE COLLEGES
# ==============================
min_samples = 40
college_counts = df['College'].value_counts()
rare = college_counts[college_counts < min_samples].index
df['College'] = df['College'].replace(rare, 'Other')

print("Unique colleges:", df['College'].nunique())

# ==============================
# 7. FEATURES & TARGET
# ==============================
X = df[[
    'Rank','Rank_Log','Rank_Bin','Year_Index','RoundNo',
    'Quota','Course','Category','Category_Quota','Category_Rank',
    'PH','Rank_Year','Round_Year',
    'Cutoff_Rank','Rank_vs_Cutoff'
]]

y = df['College']

le = LabelEncoder()
y_encoded = le.fit_transform(y)

# ==============================
# 8. SPLIT
# ==============================
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded,
    test_size=0.2,
    random_state=42,
    stratify=y_encoded
)

# ==============================
# 9. PREPROCESSOR
# ==============================
categorical_cols = [
    'Rank_Bin','RoundNo','Quota','Course',
    'Category','Category_Quota','Category_Rank'
]

numeric_cols = [
    'Rank','Rank_Log','PH','Year_Index',
    'Rank_Year','Round_Year',
    'Cutoff_Rank','Rank_vs_Cutoff'
]

preprocessor = ColumnTransformer([
    ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols),
    ('num', 'passthrough', numeric_cols)
])

# ==============================
# 10. MODELS
# ==============================
rf_model = RandomForestClassifier(
    n_estimators=600,
    max_depth=30,
    min_samples_split=4,
    min_samples_leaf=2,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)

xgb_base = XGBClassifier(
    n_estimators=1000,
    learning_rate=0.02,
    max_depth=12,
    subsample=0.9,
    colsample_bytree=0.9,
    gamma=0.2,
    min_child_weight=3,
    objective='multi:softprob',
    eval_metric='mlogloss',
    random_state=42,
    n_jobs=-1
)

xgb_model = CalibratedClassifierCV(xgb_base, method='sigmoid', cv=3)

models = {
    "RandomForest": rf_model,
    "XGBoost": xgb_model
}

results = {}

# ==============================
# 11. TRAIN LOOP
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
# 12. 2026 PREDICTION
# ==============================

future_year_index = df['Year_Index'].max() + 1

rank_val = 25000
quota_val = 'SQ'
category_val = 'UR'
course_val = 'MBBS'
round_val = 2

rank_bin = pd.cut(
    [rank_val],
    bins=[0,500,1000,2000,3000,5000,8000,12000,20000,50000,1000000],
    labels=[
        '0-500','500-1k','1k-2k','2k-3k','3k-5k',
        '5k-8k','8k-12k','12k-20k','20k-50k','50k+'
    ]
)[0]

sample = pd.DataFrame({
    'Rank': [rank_val],
    'Rank_Log': [np.log1p(rank_val)],
    'Rank_Bin': [rank_bin],
    'Year_Index': [future_year_index],
    'RoundNo': [round_val],
    'Quota': [quota_val],
    'Course': [course_val],
    'Category': [category_val],
    'Category_Quota': [f'{category_val}_{quota_val}'],
    'Category_Rank': [f'{category_val}_{rank_bin}'],
    'PH': [0],
    'Rank_Year': [rank_val / (future_year_index + 1)],
    'Round_Year': [round_val * (future_year_index + 1)],
    'Cutoff_Rank': [30000],   # approx cutoff
    'Rank_vs_Cutoff': [rank_val - 30000]
})

best_model = results["XGBoost"]

probs = best_model.predict_proba(sample)[0]
classes = le.inverse_transform(np.arange(len(probs)))

top_idx = np.argsort(probs)[-5:][::-1]

top_probs = probs[top_idx]
top_probs = np.power(top_probs, 1.3)
top_probs = top_probs / top_probs.sum()

print("\n🎯 Top 5 Colleges for 2026:\n")

for i, idx in enumerate(top_idx):
    prob = top_probs[i] * 100

    if prob > 35:
        tag = "SAFE"
    elif prob > 20:
        tag = "TARGET"
    else:
        tag = "DREAM"

    print(f"{i+1}. {classes[idx]} → {prob:.2f}% ({tag})")