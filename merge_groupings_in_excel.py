"""
Update the Excel/CSV file by merging grouped questions directly in the file.

This script:
- Reads the CSV file (grouping_worksheet_full_auto_grouped.csv or grouping_worksheet_full.csv)
- For each canonical question (with should_group_with filled):
  - Merges years from all source questions into the canonical question's years column
  - Removes the source question rows
- Keeps only the canonical question row for each group
- Writes the updated file back (overwrites the input file or creates a new one)

WARNING: This modifies the Excel file! Only run when explicitly requested.
"""

import csv
import re
from typing import Dict, List, Set
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


def merge_groupings_in_excel(input_file: str = 'grouping_worksheet_full_auto_grouped.csv',
                            output_file: str = None,
                            in_place: bool = False):
    """
    Merge grouped questions directly in the Excel/CSV file.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file (if None and in_place=False, creates backup)
        in_place: If True, overwrites input_file. If False, writes to output_file or creates backup.
    """
    
    if output_file is None and not in_place:
        # Create backup filename
        import os
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_merged{ext}"
    
    if in_place:
        output_file = input_file
    
    print(f"Reading from {input_file}...")
    delimiter = detect_delimiter(input_file)
    
    # Read all rows
    rows = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    print(f"Loaded {len(rows)} rows")
    
    # Create mapping of question_id to row index
    qid_to_index = {}
    valid_rows = []
    
    for i, row in enumerate(rows):
        qid_str = row.get('question_id', '').strip()
        if qid_str and qid_str.isdigit():
            qid = int(qid_str)
            qid_to_index[qid] = i
            valid_rows.append((i, row))
    
    print(f"Found {len(valid_rows)} questions with valid IDs")
    
    # Identify canonical questions and source questions to remove
    canonical_questions = {}
    source_question_ids = set()
    
    for i, row in valid_rows:
        qid = int(row.get('question_id', '').strip())
        should_group = row.get('should_group_with', '').strip()
        
        if should_group:
            # This is a canonical question
            source_ids = parse_should_group_with(should_group)
            canonical_questions[qid] = {
                'index': i,
                'row': row,
                'source_ids': source_ids
            }
            source_question_ids.update(source_ids)
    
    print(f"Found {len(canonical_questions)} canonical questions")
    print(f"Will merge {len(source_question_ids)} source questions")
    
    # Update canonical questions with merged years
    for qid, canonical_info in canonical_questions.items():
        canonical_row = canonical_info['row']
        source_ids = canonical_info['source_ids']
        
        # Collect years from canonical and all source questions
        all_years = parse_years(canonical_row.get('years', ''))
        
        for source_id in source_ids:
            if source_id in qid_to_index:
                source_index = qid_to_index[source_id]
                source_row = rows[source_index]
                source_years = parse_years(source_row.get('years', ''))
                all_years.update(source_years)
        
        # Update canonical row with merged years
        canonical_row['years'] = format_years(all_years)
        canonical_row['num_years'] = str(len(all_years))
        
        # Clear should_group_with (grouping is now applied)
        # Or keep it for reference - user's choice. Let's clear it for now.
        # canonical_row['should_group_with'] = ''
    
    # Build new rows list (excluding source questions)
    new_rows = []
    rows_to_remove = set(source_question_ids)
    
    for i, row in enumerate(rows):
        qid_str = row.get('question_id', '').strip()
        if qid_str and qid_str.isdigit():
            qid = int(qid_str)
            if qid in rows_to_remove:
                # Skip source questions
                continue
        
        # Keep this row (either canonical, updated, or non-question row)
        new_rows.append(row)
    
    print(f"\nRemoved {len(rows_to_remove)} source question rows")
    print(f"Final file contains {len(new_rows)} rows (down from {len(rows)})")
    
    # Write updated file
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(new_rows)
    
    print("Done!")
    print(f"\nUpdated file: {output_file}")
    print(f"  - Removed {len(rows_to_remove)} source question rows")
    print(f"  - Merged years into {len(canonical_questions)} canonical questions")
    print(f"  - Final row count: {len(new_rows)}")
    
    return output_file


if __name__ == '__main__':
    import sys
    
    # Default behavior: create new file (don't overwrite original)
    input_file = 'grouping_worksheet_full_auto_grouped.csv'
    in_place = False
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2].lower() == '--in-place':
        in_place = True
        print("WARNING: This will overwrite the input file!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    merge_groupings_in_excel(input_file=input_file, in_place=in_place)


