import pandas as pd
from agents_LLM_RAG import process_content
from sklearn.metrics import classification_report

df = pd.read_csv("politifact.csv")

assert 'text' in df.columns, "'text' column not found"
assert 'label' in df.columns, "'label' column not found"

predicted_labels = []
explanations = []

for i, row in df.iterrows():
    print(f"\nProcessing row {i+1}/{len(df)}")
    result, explanation = process_content(row['text'])
    predicted_labels.append(result.get('decision', 'NEI'))
    explanations.append(str(explanation))

df['predicted_label'] = predicted_labels
df['explanation'] = explanations

filtered_df = df[df['predicted_label'].isin(['real', 'fake'])]
df.to_csv("politifact_results_with_predictions.csv", index=False)


print("\nClassification Report (excluding NEI):")
print(classification_report(filtered_df['label'], filtered_df['predicted_label'], target_names=["fake", "real"]))

