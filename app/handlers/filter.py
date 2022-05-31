from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)
from argparse import ArgumentParser, Namespace
from pathlib import Path
import numpy as np 

def softmax(x):
    f_x = np.exp(x) / np.sum(np.exp(x))
    return f_x

def classifier(mail):    
    intent2idx = {'ham': 0, 'spam': 1}
    idx2intent = {idx: intent for intent, idx in intent2idx.items()}

    tokenizer = AutoTokenizer.from_pretrained("ckiplab/albert-tiny-chinese")
    text = mail['subject'] + mail.body()
    print(text)
    tokens = tokenizer(text, padding='max_length', max_length=128, truncation=True, return_tensors='pt')
    print(tokens)
    # Preparing model
    model = AutoModelForSequenceClassification.from_pretrained("/home/team7/test_project/best_smooth.ckpt", num_labels=2)
    logits = softmax(model(**tokens)['logits'].detach().numpy())[0]
    prediction = 1 if logits[1] >= 0.85 else 0
    print(f"prediction: {idx2intent[prediction]}")
    return prediction


