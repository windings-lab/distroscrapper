import json
from dataclasses import asdict


def dump_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([item.to_dict() for item in data], f, indent=2)

def dump_dataclass_to_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(item) for item in data], f, indent=2)

def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data

def read_html(path):
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    return html

def split_words(text: str):
    return text.split(" ")