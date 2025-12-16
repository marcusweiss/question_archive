import json

with open(r'Kodböcker\cleaned\combined_pdf_spss.json', encoding='utf-8') as f:
    data = json.load(f)

f17 = [q for q in data if q.get('variable') == 'f17' and 'radiokanaler' in q.get('question', '').lower()]
if f17:
    print('f17 items:')
    for i, item in enumerate(f17[0]['items'], 1):
        print(f'  {i}. "{item}"')

f20 = [q for q in data if q.get('variable') == 'f20' and 'använt internet' in q.get('question', '').lower()]
if f20:
    print('\nf20 first 5 items:')
    for i, item in enumerate(f20[0]['items'][:5], 1):
        print(f'  {i}. "{item}"')





