from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)
from argparse import ArgumentParser, Namespace
from pathlib import Path
import numpy as np 

def classifier(mail):    
    tokenizer = AutoTokenizer.from_pretrained("hfl/chinese-macbert-large")
    text = mail['subject'] + mail.body()
    print(text)
    tokens = tokenizer(text, padding='max_length', max_length=128, truncation=True, return_tensors='pt')
    print(tokens)
    # Preparing model
    model = AutoModelForSequenceClassification.from_pretrained("/home/team7/test_project/best.ckpt", num_labels=2)
    logits = model(**tokens)
    prediction = np.argmax(logits, axis=-1)
    print(prediction)
    return prediction


