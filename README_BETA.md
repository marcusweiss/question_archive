# SOM Question Library - Beta Version

A searchable cross-year question library for the Riks-SOM survey (1986-2024), containing 15,991 unique questions after intelligent merging and deduplication.

## 🚀 Quick Start

1. **View the library online:**
   ```bash
   cd question-library
   python -m http.server 8000
   ```
   Then open http://localhost:8000/search.html in your browser.

2. **Build the library from merged data:**
   ```bash
   cd question-library
   python build_library_from_merged_csv.py
   ```

## 📊 What's Included

- **15,991 unique questions** from 39 years of surveys (1986-2024)
- **4,085 questions** appearing in multiple years
- **15,607 questions** with response alternatives
- Intelligent merging of duplicate/similar questions across years
- Searchable web interface

## 📁 Key Files

### Core Scripts
- `build_library_from_merged_csv.py` - Builds the JSON library from merged CSV
- `extract_question_library.py` - Extracts questions from SPSS files
- `build_cross_year_library.py` - Alternative builder from SPSS files

### Data Files
- `grouping/grouping_worksheet_full_merged.csv` - Main merged question database
- `question_library_cross_year.json` - Final searchable library (generated)

### Web Interface
- `search.html` - Searchable web interface for browsing questions

### Grouping Tools (Advanced)
- `grouping/apply_and_merge.py` - Applies merge decisions
- `grouping/split_merge_suggestions.py` - Splits merge suggestions by year overlap
- `grouping/merge_suggestions_noyears.csv` - Merge suggestions without year overlap
- `grouping/merge_suggestions_yesyears.csv` - Merge suggestions with year overlap

## 🔍 Features

### Search Interface
- Full-text search across all question texts
- Filter by years
- Filter by response alternatives
- View question history across years
- Export results

### Data Quality
- Questions merged across years when text and responses match
- Years combined for identical questions
- Response alternatives normalized and deduplicated
- Invalid entries filtered out

## 📈 Statistics

- **Total years covered:** 39 (1986-2024)
- **Unique questions:** 15,991
- **Questions in multiple years:** 4,085
- **Questions with alternatives:** 15,607

## 🛠️ Technical Details

### Data Structure
Each question in the library includes:
- `question_text`: Core question text (for search/grouping)
- `full_question_text`: Complete question wording with year range
- `response_alternatives`: Array of response options
- `years`: Object mapping years to variable names
- `type`: "cross_year" or "single_year"
- `question_id`: Unique identifier
- `num_years`: Number of years the question appears in

### Merging Process
1. Questions are extracted from SPSS files or CSV
2. Similar questions are identified based on:
   - Normalized question text
   - Matching response alternatives
3. Questions are merged, combining years
4. Duplicate questions are removed

## 📝 Notes for Beta Reviewers

This is a **beta version** - some features may still be refined:

- Question text normalization may need adjustment
- Some merge suggestions may need manual review
- Response alternative matching could be improved
- Additional filtering options may be added

## 🔄 Updating the Library

To update the library with new merges:

1. Review merge suggestions in `grouping/merge_suggestions_noyears.csv`
2. Mark merges with '0' (no merge) or '1' (merge)
3. Run `grouping/apply_and_merge.py` to apply decisions
4. Rebuild the library: `python build_library_from_merged_csv.py`

## 📧 Feedback

Please provide feedback on:
- Search functionality
- Question grouping accuracy
- Missing questions
- Interface improvements
- Data quality issues

---

**Version:** Beta 1.0  
**Last Updated:** December 2024  
**Data Source:** Riks-SOM Survey 1986-2024

