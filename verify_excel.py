import pandas as pd

df = pd.read_excel("produtos_capilares.xlsx")
print("Columns:", df.columns.tolist())
print("\nFirst row sample:")
print(df.iloc[0][["product_name", "cronograma_fase", "cronograma_scores", "adequacao_cabelos_finos", "score_cabelos_finos"]])
