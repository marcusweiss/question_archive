# Changes Made to Fix Question Grouping

## 1. Removed F Prefixes from Questions
- Updated `normalize_question_text()` to remove variable prefixes like "F77a.:", "F99a.:", etc.
- This is applied when questions are first extracted and during grouping

## 2. Fixed Cross-Year Grouping
- Removed `year` from the matching key in `group_questions_across_years()`
- Now matches questions based only on normalized text + response alternatives
- This means identical questions across different years (like F77a and F99a) will be grouped together

## 3. Normalized All Question Text
- Questions are normalized when first extracted from SPSS files
- Battery sub-items are also normalized
- Full question text and parent questions are normalized for display

## To Run:
```powershell
cd C:\Users\xwmarc\Desktop\AI-test\question-library
python build_cross_year_library.py
```

This will take several minutes to process all 15 years of data. The script will show progress as it processes each year.

