"""
Build the final question library from the manually edited Excel/CSV file.

This script:
- Reads grouping_worksheet_full.csv (or grouping_worksheet_full_auto_grouped.csv)
- Parses should_group_with to identify groupings
- For canonical questions (those with should_group_with filled):
  - Merges years from all source questions
  - Removes source questions from final output
  - Formats question_text with combined year range
  - Preserves manual edits to question_text and response_alternatives
- Builds the final JSON library
"""

import csv
import json
import re
from typing import Dict, List, Set, Optional
from collections import defaultdict


def detect_delimiter(file_path: str) -> str:
    """Detect CSV delimiter (comma or semicolon)."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        if ';' in first_line and first_line.count(';') > first_line.count(','):
            return ';'
        return ','


def parse_years(years_str: str) -> Set[int]:
    """Parse years string into a set of integers.
    
    Handles formats like:
    - "1986, 1988, 1990"
    - "1986, 1988-1990"
    - "1986-1990"
    """
    if not years_str or not years_str.strip():
        return set()
    
    years = set()
    parts = [p.strip() for p in years_str.split(',')]
    
    for part in parts:
        if '-' in part:
            # Range like "1988-1990"
            start, end = part.split('-', 1)
            try:
                start_year = int(start.strip())
                end_year = int(end.strip())
                years.update(range(start_year, end_year + 1))
            except ValueError:
                pass
        else:
            # Single year
            try:
                years.add(int(part.strip()))
            except ValueError:
                pass
    
    return years


def format_years(years: Set[int]) -> str:
    """Format a set of years into a compact string representation.
    
    Examples:
    - {1986, 1988, 1989, 1990} -> "1986, 1988-1990"
    - {1986, 1987, 1988} -> "1986-1988"
    - {1986, 1988, 1990} -> "1986, 1988, 1990"
    """
    if not years:
        return ""
    
    sorted_years = sorted(years)
    
    # Find consecutive ranges
    ranges = []
    i = 0
    while i < len(sorted_years):
        start = sorted_years[i]
        end = start
        
        # Find consecutive years
        j = i + 1
        while j < len(sorted_years) and sorted_years[j] == sorted_years[j-1] + 1:
            end = sorted_years[j]
            j += 1
        
        if start == end:
            ranges.append(str(start))
        elif end == start + 1:
            ranges.append(f"{start}, {end}")
        else:
            ranges.append(f"{start}-{end}")
        
        i = j
    
    return ", ".join(ranges)


def remove_year_prefix(text: str) -> str:
    """Remove year prefix from question text if present.
    
    Examples:
    - "1986, 1988-1990: aktuellt" -> "aktuellt"
    - "2005: aktuellt" -> "aktuellt"
    """
    if not text:
        return text
    
    # Remove year prefix pattern
    text = re.sub(r'^\d{4}(?:,\s*\d{4}(?:-\d{4})?)*:\s*', '', text).strip()
    return text


def add_year_prefix(text: str, years: Set[int]) -> str:
    """Add year prefix to question text.
    
    Examples:
    - "aktuellt" + {1986, 1988-1990} -> "1986, 1988-1990: aktuellt"
    """
    if not text:
        return text
    
    years_str = format_years(years)
    if years_str:
        return f"{years_str}: {text}"
    return text


def parse_should_group_with(should_group_str: str) -> List[int]:
    """Parse should_group_with string to extract question IDs.
    
    Handles formats like:
    - "Auto: 123, 456, 789"
    - "123, 456, 789"
    - "Auto: 123"
    """
    if not should_group_str or not should_group_str.strip():
        return []
    
    # Remove "Auto: " prefix if present
    text = should_group_str.strip()
    if text.startswith("Auto: "):
        text = text[6:].strip()
    
    # Split by comma and extract IDs
    ids = []
    for part in text.split(','):
        part = part.strip()
        # Extract numbers from the part
        numbers = re.findall(r'\d+', part)
        for num in numbers:
            try:
                ids.append(int(num))
            except ValueError:
                pass
    
    return ids


def build_from_excel(input_file: str = 'grouping_worksheet_full_auto_grouped.csv',
                    output_file: str = 'question_library_from_excel.json'):
    """Build the final question library from the Excel/CSV file."""
    
    print(f"Reading from {input_file}...")
    delimiter = detect_delimiter(input_file)
    
    # Read all rows
    rows = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    print(f"Loaded {len(rows)} rows")
    
    # Create mapping of question_id to row
    qid_to_row = {}
    valid_rows = []
    
    for row in rows:
        qid_str = row.get('question_id', '').strip()
        if qid_str and qid_str.isdigit():
            qid = int(qid_str)
            qid_to_row[qid] = row
            valid_rows.append(row)
    
    print(f"Found {len(valid_rows)} questions with valid IDs")
    
    # Identify canonical questions (those with should_group_with filled)
    canonical_questions = {}
    source_question_ids = set()  # Questions that should be removed
    
    for row in valid_rows:
        qid = int(row.get('question_id', '').strip())
        should_group = row.get('should_group_with', '').strip()
        
        if should_group:
            # This is a canonical question
            source_ids = parse_should_group_with(should_group)
            canonical_questions[qid] = {
                'row': row,
                'source_ids': source_ids
            }
            source_question_ids.update(source_ids)
    
    print(f"Found {len(canonical_questions)} canonical questions")
    print(f"Will merge {len(source_question_ids)} source questions")
    
    # Build final questions list
    final_questions = []
    processed_canonical = set()
    
    for row in valid_rows:
        qid = int(row.get('question_id', '').strip())
        
        # Skip source questions (they'll be merged into canonical)
        if qid in source_question_ids:
            continue
        
        # Check if this is a canonical question
        if qid in canonical_questions:
            canonical_info = canonical_questions[qid]
            canonical_row = canonical_info['row']
            source_ids = canonical_info['source_ids']
            
            # Collect years from canonical and all source questions
            all_years = parse_years(canonical_row.get('years', ''))
            
            for source_id in source_ids:
                if source_id in qid_to_row:
                    source_row = qid_to_row[source_id]
                    source_years = parse_years(source_row.get('years', ''))
                    all_years.update(source_years)
            
            # Get question text (remove existing year prefix if present, then add new one)
            question_text = canonical_row.get('question_text', '').strip()
            question_text = remove_year_prefix(question_text)
            question_text = add_year_prefix(question_text, all_years)
            
            # Get response alternatives (preserve manual edits)
            response_alternatives_str = canonical_row.get('response_alternatives', '').strip()
            if response_alternatives_str:
                response_alternatives = [alt.strip() for alt in response_alternatives_str.split('|') if alt.strip()]
            else:
                response_alternatives = []
            
            # Build final question entry
            final_question = {
                'question_id': qid,
                'question_text': question_text,
                'parent_question': canonical_row.get('parent_question', '').strip(),
                'item': canonical_row.get('item', '').strip(),
                'years': format_years(all_years),
                'years_list': sorted(all_years),
                'num_years': len(all_years),
                'response_alternatives': response_alternatives,
                'num_responses': len(response_alternatives),
                'grouped_from': source_ids if source_ids else None
            }
            
            final_questions.append(final_question)
            processed_canonical.add(qid)
        
        else:
            # Regular question (not grouped)
            question_text = row.get('question_text', '').strip()
            question_text = remove_year_prefix(question_text)  # Remove year prefix if present
            
            years = parse_years(row.get('years', ''))
            if years:
                question_text = add_year_prefix(question_text, years)
            
            response_alternatives_str = row.get('response_alternatives', '').strip()
            if response_alternatives_str:
                response_alternatives = [alt.strip() for alt in response_alternatives_str.split('|') if alt.strip()]
            else:
                response_alternatives = []
            
            final_question = {
                'question_id': qid,
                'question_text': question_text,
                'parent_question': row.get('parent_question', '').strip(),
                'item': row.get('item', '').strip(),
                'years': format_years(years),
                'years_list': sorted(years),
                'num_years': len(years),
                'response_alternatives': response_alternatives,
                'num_responses': len(response_alternatives),
                'grouped_from': None
            }
            
            final_questions.append(final_question)
    
    # Sort by question_id
    final_questions.sort(key=lambda x: x['question_id'])
    
    print(f"\nFinal library contains {len(final_questions)} questions")
    print(f"Reduced from {len(valid_rows)} questions by {len(valid_rows) - len(final_questions)} groupings")
    
    # Build output structure
    output = {
        'source_file': input_file,
        'total_questions': len(final_questions),
        'questions': final_questions
    }
    
    # Write JSON
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("Done!")
    
    return output


if __name__ == '__main__':
    build_from_excel()


