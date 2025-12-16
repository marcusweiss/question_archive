import json

with open('question_library_merged.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Library Summary:")
print(f"  Total questions: {data['total_questions']}")
print(f"  Questions with alternatives: {data['questions_with_alternatives']}")
print(f"  Questions without alternatives: {data['total_questions'] - data['questions_with_alternatives']}")

print(f"\nSample questions:")
for q in data['questions'][:10]:
    years_str = q['years'][:30] if len(q['years']) > 30 else q['years']
    text_str = q['question_text'][:60] + '...' if len(q['question_text']) > 60 else q['question_text']
    print(f"  [{q['question_id']}] {text_str}")
    print(f"      Years: {years_str} ({q['num_years']} years)")
    if q['response_alternatives']:
        print(f"      Responses: {len(q['response_alternatives'])} alternatives")
    print()

