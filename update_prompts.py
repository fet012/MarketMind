import json

with open('prompts/few_shot_examples.json', 'r', encoding='utf-8') as f:
    examples = json.load(f)

for ex in examples:
    if "assistant" in ex:
        ast = json.loads(ex["assistant"])
        if "data" in ast and "item" in ast["data"]:
            old_data = ast["data"]
            # Convert to new schema
            if old_data.get("item") is not None or old_data.get("amount") is not None:
                ast["data"] = {"transactions": [old_data]}
            else:
                ast["data"] = {"transactions": []}
            
            ex["assistant"] = json.dumps(ast, ensure_ascii=False)

with open('prompts/few_shot_examples.json', 'w', encoding='utf-8') as f:
    json.dump(examples, f, indent=2, ensure_ascii=False)

print("Updated few_shot_examples.json")
