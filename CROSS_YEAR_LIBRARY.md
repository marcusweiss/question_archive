# Cross-Year Question Library

This document describes the cross-year searchable question library that groups questions across multiple years (2023, 2024, and eventually 1986-2024).

## Structure

The `question_library_cross_year.json` file contains:

### Top Level
- `years`: List of all years included (e.g., [2023, 2024])
- `total_unique_questions`: Number of unique questions (grouped across years)
- `total_unique_batteries`: Number of unique batteries (grouped across years)
- `questions`: Array of question objects
- `batteries`: Array of battery objects

### Question Objects

Each question can be one of two types:

#### 1. Cross-Year Questions (`type: "cross_year"`)
Questions that appear in multiple years (may have variations):

```json
{
  "question_text": "Main question text (most complete version)",
  "years": [2023, 2024],
  "year_details": {
    "2023": {
      "variable": "f7",
      "question_text": "Exact question text from 2023",
      "response_alternatives": ["Ja", "Nej"]
    },
    "2024": {
      "variable": "f7",
      "question_text": "Exact question text from 2024",
      "response_alternatives": ["Ja", "Nej"]
    }
  },
  "type": "cross_year"
}
```

#### 2. Single-Year Questions (`type: "single_year"`)
Questions that only appear in one year:

```json
{
  "question_text": "Question text",
  "years": [2024],
  "year_details": {
    "2024": {
      "variable": "empstat",
      "question_text": "Anställningsstatus (baserad på f150)",
      "response_alternatives": ["Selfemployed 10+", ...]
    }
  },
  "type": "single_year"
}
```

### Battery Objects

Batteries are grouped by variable name (e.g., f1, f2) across years:

```json
{
  "variable": "f1",
  "question_text": "Common question stem",
  "years": [2023, 2024],
  "year_details": {
    "2023": {
      "question_text": "Hur ofta ta del av -",
      "sub_items": ["Lokala nyheter från Sveriges Radio", ...],
      "response_alternatives": ["Dagligen", "5-6 dagar vecka", ...]
    },
    "2024": {
      "question_text": "Hur ofta brukar du ta del av -",
      "sub_items": ["Lokala nyheter från Sveriges Radio", ...],
      "response_alternatives": ["Dagligen", "5-6 dagar vecka", ...]
    }
  },
  "type": "battery"
}
```

## Features

1. **Cross-Year Grouping**: Questions with similar text are automatically grouped together
2. **Year-Specific Details**: Each year's exact variable name, question text, and response alternatives are preserved
3. **Variation Tracking**: Differences in wording, items, or alternatives between years are visible
4. **Searchable**: The structure makes it easy to:
   - Find questions by text
   - See which years a question appears in
   - Compare variations across years
   - Identify questions unique to specific years

## Usage

### Finding Questions Across Years

To find a question and see all years it appears in:
```python
import json

with open('question_library_cross_year.json', encoding='utf-8') as f:
    library = json.load(f)

# Search for a question
search_term = "förtroende"
matching = [q for q in library['questions'] 
           if search_term.lower() in q['question_text'].lower()]

for q in matching:
    print(f"Question: {q['question_text']}")
    print(f"Years: {q['years']}")
    print(f"Type: {q['type']}")
```

### Comparing Variations

To see how a question varies across years:
```python
# Find cross-year questions
cross_year = [q for q in library['questions'] if q['type'] == 'cross_year']

for q in cross_year:
    print(f"\n{q['question_text']}")
    for year in q['years']:
        details = q['year_details'][str(year)]
        print(f"  {year}: {details['question_text']}")
        print(f"    Variable: {details['variable']}")
```

## Statistics (2023-2024)

- **Total unique questions**: 105
- **Questions in multiple years**: 78
- **Questions in single year**: 27
- **Total unique batteries**: 156
- **Batteries in multiple years**: ~80 (estimated)

## Adding More Years

To add more years (e.g., 2022, 2021, etc.):

1. Place the SPSS file in the folder: `Riks-SOM YYYY.sav`
2. Run: `python build_cross_year_library.py`
3. The script will automatically:
   - Detect all SPSS files
   - Extract questions from each year
   - Group similar questions across all years
   - Update the library

## Notes

- Questions with 20+ response alternatives are marked as `["öppen fråga"]`
- Battery sub-questions are excluded from regular questions
- Questions are sorted alphabetically by question text
- Batteries are sorted by variable name

