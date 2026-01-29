import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from joblib import dump

# Load symptom severity dataset
df = pd.read_csv("../data/Symptom-severity.csv")

# Generate synthetic patient data
np.random.seed(42)

severity_scores = []
risk_labels = []

for _ in range(500):
    sampled_symptoms = df.sample(np.random.randint(1, 4))
    total_score = sampled_symptoms["weight"].sum()
    severity_scores.append(total_score)

    # Risk threshold
    risk_labels.append(1 if total_score >= 10 else 0)

# Prepare ML data
X = np.array(severity_scores).reshape(-1, 1)
y = np.array(risk_labels)

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train Logistic Regression model
model = LogisticRegression()
model.fit(X_train, y_train)

# Save trained model
dump(model, "risk_model.pkl")

print("✅ Risk prediction model trained and saved successfully.")
