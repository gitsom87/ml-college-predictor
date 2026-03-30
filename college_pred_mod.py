import pandas as pd
import pyodbc

from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
from sklearn.ensemble import RandomForestClassifier

# -------------------------------
# 1. Connect to SQL Server
# -------------------------------
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=LAPTOP-9UCJFBPD\MSSQLSERVER2022;"
    "DATABASE=UR_R2;"
    "Trusted_Connection=yes;"
)

# -------------------------------
# 2. Load Data
# -------------------------------
query = """
SELECT Rank, Category, Quota, PH, College
FROM ML_CollegeData
"""

df = pd.read_sql(query, conn)

print("Data Loaded:", df.shape)

# -------------------------------
# 3. Encode Categorical Data
# -------------------------------
le_cat = LabelEncoder()
le_quota = LabelEncoder()
le_college = LabelEncoder()

df["Category"] = le_cat.fit_transform(df["Category"])
df["Quota"] = le_quota.fit_transform(df["Quota"])
df["College"] = le_college.fit_transform(df["College"])

# PH already Y/N → convert to 1/0
df["PH"] = df["PH"].map({"Y": 1, "N": 0})

# -------------------------------
# 4. Features & Target
# -------------------------------
X = df[["Rank", "Category", "Quota", "PH"]]
y = df["College"]

# -------------------------------
# 5. Train-Test Split
# -------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# -------------------------------
# 6. Train Model
# -------------------------------
model = DecisionTreeClassifier(max_depth=5)  # keep small for now
model.fit(X_train, y_train)


from sklearn.tree import plot_tree
import matplotlib.pyplot as plt

plt.figure(figsize=(70,35))
plot_tree(
    model,
    feature_names=["Rank", "Category", "Quota", "PH"],
    filled=True
)
plt.show()

# from sklearn.tree import export_text

# tree_rules = export_text(model, feature_names=["Rank", "Category", "Quota", "PH"])
# print(tree_rules)

# -------------------------------
# Random Forest Model
# -------------------------------
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)

rf_model.fit(X_train, y_train)

# -------------------------------
# 7. Evaluate Model
# -------------------------------
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print("Model Accuracy:", accuracy)

rf_pred = rf_model.predict(X_test)
rf_accuracy = accuracy_score(y_test, rf_pred)
print("\nRandom Forest Accuracy:", rf_accuracy)

# -------------------------------
# 8. Test Prediction
# -------------------------------
# Example input:
# Rank = 100000, Category = SC, Quota = SO, PH = N

sample = pd.DataFrame([{
    "Rank": 200000,
    "Category": le_cat.transform(["UR"])[0],
    "Quota": le_quota.transform(["SO"])[0],
    "PH": 1
}])

pred = model.predict(sample)

print("Predicted College:",
      le_college.inverse_transform(pred)[0])

# Random Forest prediction
rf_pred = rf_model.predict(sample)

print("Random Forest Prediction:",
      le_college.inverse_transform(rf_pred)[0])

print("\nRandom Forest Feature Importance:")
print(rf_model.feature_importances_)




node_indicator = model.decision_path(sample)

print("\nDecision Path for given input:\n")

for node_id in node_indicator.indices:
    print(f"Visited node {node_id}")

print(model.feature_importances_)