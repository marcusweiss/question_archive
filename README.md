# Question Library - 2024 Extraction

This folder contains the extracted question library from the 2024 Riks-SOM survey.

## Files

- **kodbok 2024.pdf** - Original codebook PDF
- **Riks-SOM 2024.dta** - Original Stata data file
- **extract_question_library.py** - Extraction script
- **question_library_2024.json** - Extracted question library (output)

## Extraction Results

- **Total questions**: 336 (after filtering invalid entries and excluding battery sub-questions)
- **Questions with response alternatives**: 253
- **Battery groups identified**: 100

## Data Structure

The `question_library_2024.json` file contains:

```json
{
  "year": 2024,
  "source_files": {
    "pdf": "kodbok 2024.pdf",
    "stata": "Riks-SOM 2024.dta"
  },
  "total_questions": 336,
  "questions_with_alternatives": 253,
  "batteries": [
    {
      "variable": "f1",
      "question_text": "Hur ofta brukar du ta del av -",
      "sub_items": [
        "Lokala nyheter från Sveriges Radio",
        "Ekonyheter från SR",
        "P3 Nyheter från SR",
        "Aktuellt/Rapport från SVT",
        "Lokala nyheter från SVT",
        "TV4 Nyheterna"
      ],
      "response_alternatives": [
        "Dagligen",
        "5-6 dagar vecka",
        "3-4 dagar/vecka",
        "1-2 dagar/vecka",
        "Mer sällan",
        "Aldrig"
      ]
    }
  ],
  "questions": [
    {
      "variable": "f7",
      "question_text": "f7. Prenumererar du eller någon i ditt hushåll på någon morgontidning?",
      "response_alternatives": [
        "Ja",
        "Nej"
      ]
    }
  ]
}
```

## Features

### Questions
- All questions extracted from both PDF codebook and Stata file
- Variable names preserved
- Question text from Stata variable labels (more reliable than PDF extraction)
- Response alternatives as a simple list of label strings (no values stored)
- Missing codes (94-99) excluded from response alternatives
- Clean, efficient structure: just variable, question_text, and response_alternatives array

### Batteries
- Battery questions identified by variable naming pattern (e.g., f1a, f1b, f1c)
- Simplified structure: common question stem + list of sub-items + shared response alternatives
- Variable names of sub-questions (f1a, f1b, etc.) are not stored - only the base variable (f1)
- 100 battery groups identified
- Battery sub-questions are excluded from the regular questions list

### Filtering
- Invalid entries filtered out (metadata lines, author information, etc.)
- Questions with just "-" or very short text removed
- Author/affiliation lines excluded

## Running the Extraction

```bash
cd question-library
python extract_question_library.py
```

This will:
1. Extract questions from the PDF codebook
2. Extract variable labels and value labels from the Stata file
3. Merge the data sources
4. Identify battery questions
5. Filter invalid entries
6. Save to `question_library_2024.json`

## Next Steps

This is a first attempt. Areas for refinement:
- Improve PDF extraction to better capture question text formatting
- Better handling of complex battery structures
- Extract sub-question text for batteries from PDF
- Handle special question types (grids, matrices, etc.)

