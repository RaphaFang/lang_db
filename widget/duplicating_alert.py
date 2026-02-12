import pandas as pd
import json

df = pd.read_csv("cleaned_voc.csv")
df['word'] = df['word'].str.lower()
df["sentences"] = df["sentences"].map(json.dumps)  # map 這邊做的就是逐行處理
df.drop_duplicates(subset=['word', 'lang'], keep='first', inplace=True)
df.to_csv("new_c.csv", index=False, header=1, mode='a')