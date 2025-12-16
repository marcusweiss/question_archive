import json

with open(r'Kodböcker\cleaned\spss_questions.json', encoding='utf-8') as f:
    data = json.load(f)

keys = list(data.keys())
print('First 20 keys:')
for i, k in enumerate(keys[:20]):
    items_count = len(data[k].get('items', []))
    print(f'{i+1}. {k} - items: {items_count}')

print(f'\nHas f1? {"f1" in data}')
if 'f1' in data:
    print(f'f1 items: {len(data["f1"].get("items", []))}')
    print(f'f1 question: {data["f1"].get("question", "")[:80]}...')
else:
    print('f1a exists:', 'f1a' in data)





