import os
import psycopg
import pandas as pd
import json
import ast

data = [
    {
        "word": "Caveat",
        "pronunciation": "",
        "lang": "en",
        "mastery_level": 1,
        "definition": "Caveat 指的是在陳述、建議或結論中必須特別注意的限制條件或警告事項，通常用來提醒讀者不要過度解讀。它常出現在學術、法律或專業語境中，用以保留彈性或避免誤導。此詞強調資訊並非在所有情況下都完全適用。",
        "sentences": [
            "The study supports the proposed model, with the caveat that the sample size was relatively small.",
            "Any policy recommendation must be interpreted with a caveat regarding its long-term economic impact."
        ]
    },
    {
        "word": "Insanity",
        "pronunciation": "",
        "lang": "en",
        "mastery_level": 1,
        "definition": "Insanity 原指精神失常或理性喪失的狀態，在法律與醫學中具有特定定義。於日常或修辭語境中，它也可用來形容極端不合理、瘋狂或難以理解的行為或情境。此詞往往帶有強烈情緒或批判意味。",
        "sentences": [
            "From an analytical perspective, repeating the same strategy while expecting different outcomes borders on insanity.",
            "The proposal was criticized as an act of economic insanity due to its complete disregard for empirical evidence."
        ]
    },
    {
        "word": "Revenue",
        "pronunciation": "",
        "lang": "en",
        "mastery_level": 1,
        "definition": "Revenue 指企業、組織或政府在一定期間內因正常營運活動所獲得的總收入，尚未扣除任何成本或支出。它是衡量經濟活動規模與營運表現的核心指標之一。在財務報表中，通常位於損益表的最上方。",
        "sentences": [
            "The company reported a significant increase in annual revenue following its expansion into emerging markets.",
            "Tax revenue plays a critical role in determining a government's capacity to fund public services."
        ]
    },
    {
        "word": "Exaggeration",
        "pronunciation": "",
        "lang": "en",
        "mastery_level": 1,
        "definition": "Exaggeration 指對事實、特徵或影響進行誇大描述，使其看起來比實際情況更極端或重要。它可用於修辭、說服或幽默，但在學術與專業語境中通常被視為不嚴謹。過度誇張可能削弱論點的可信度。",
        "sentences": [
            "The media portrayal was widely regarded as an exaggeration of the actual risks involved.",
            "In academic writing, any form of exaggeration can undermine the validity of the argument."
        ]
    },
    {
        "word": "Extract",
        "pronunciation": "",
        "lang": "en",
        "mastery_level": 1,
        "definition": "Extract 作為動詞時，表示從整體中有系統地取出所需的部分或資訊。作為名詞時，則指被提取出的內容或濃縮物，常見於資料分析、化學或文本研究中。此詞隱含過程具有目的性與方法性。",
        "sentences": [
            "The algorithm was designed to extract meaningful features from high-dimensional data.",
            "Researchers were asked to extract a short passage that best summarized the core argument."
        ]
    },
    {
        "word": "Polysemous",
        "pronunciation": "",
        "lang": "en",
        "mastery_level": 1,
        "definition": "Polysemous 用來形容一個詞語具有多個相關但不同的意義，是語義學中的重要概念。這些意義通常源自同一語源，並在不同語境中被激活。理解多義性有助於避免語言歧義與誤解。",
        "sentences": [
            "The term is highly polysemous, and its interpretation depends heavily on contextual cues.",
            "In linguistic analysis, a polysemous word often poses challenges for automatic text processing systems."
        ]
    }
]



def row_data_to_csv(route):
    file_exists = os.path.isfile(route)
    df = pd.DataFrame(data)
    df.to_csv(route, 
              mode='a',
              header= not file_exists,
              index=False, 
              quoting=1)

if __name__ == "__main__":
    row_data_to_csv("cleaned_voc.csv")
