"""
Merge grouped questions and remove exact duplicates from the Excel/CSV file.

This script:
1. Merges grouped questions (those with should_group_with filled)
2. Identifies and removes exact duplicates
3. Reports statistics on reductions
"""

import csv
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict


def detect_delimiter(file_path: str) -> str:
    """Detect CSV delimiter (comma or semicolon)."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        if ';' in first_line and first_line.count(';') > first_line.count(','):
            return ';'
        return ','


def parse_years(years_str: str) -> Set[int]:
    """Parse years string into a set of integers."""
    if not years_str or not years_str.strip():
        return set()
    
    years = set()
    parts = [p.strip() for p in years_str.split(',')]
    
    for part in parts:
        if '-' in part:
            start, end = part.split('-', 1)
            try:
                start_year = int(start.strip())
                end_year = int(end.strip())
                years.update(range(start_year, end_year + 1))
            except ValueError:
                pass
        else:
            try:
                years.add(int(part.strip()))
            except ValueError:
                pass
    
    return years


def format_years(years: Set[int]) -> str:
    """Format a set of years into a compact string representation."""
    if not years:
        return ""
    
    sorted_years = sorted(years)
    ranges = []
    i = 0
    
    while i < len(sorted_years):
        start = sorted_years[i]
        end = start
        
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
    """Parse should_group_with string to extract question IDs."""
    if not should_group_str or not should_group_str.strip():
        return []
    
    text = should_group_str.strip()
    if text.startswith("Auto: "):
        text = text[6:].strip()
    
    ids = []
    for part in text.split(','):
        part = part.strip()
        numbers = re.findall(r'\d+', part)
        for num in numbers:
            try:
                ids.append(int(num))
            except ValueError:
                pass
    
    return ids


def normalize_for_duplicate_check(row: Dict) -> Tuple[str, str, str, str]:
    """Create a normalized key for duplicate detection.
    
    Returns: (question_text, parent_question, item, response_alternatives)
    """
    question_text = row.get('question_text', '').strip().lower()
    parent_question = row.get('parent_question', '').strip().lower()
    item = row.get('item', '').strip().lower()
    response_alternatives = row.get('response_alternatives', '').strip().lower()
    
    # Normalize response alternatives (sort them)
    if response_alternatives:
        alts = [alt.strip() for alt in response_alternatives.split('|') if alt.strip()]
        alts.sort()
        response_alternatives = '|'.join(alts)
    
    return (question_text, parent_question, item, response_alternatives)


def merge_and_deduplicate(input_file: str = 'grouping_worksheet_full_merged.csv',
                         output_file: str = None,
                         in_place: bool = True):
    """Merge grouped questions and remove exact duplicates."""
    
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
    
    original_count = len(valid_rows)
    print(f"Found {original_count} questions with valid IDs")
    
    # Step 1: Identify canonical questions and source questions to remove
    canonical_questions = {}
    source_question_ids = set()
    
    for i, row in valid_rows:
        qid = int(row.get('question_id', '').strip())
        should_group = row.get('should_group_with', '').strip()
        
        if should_group:
            source_ids = parse_should_group_with(should_group)
            canonical_questions[qid] = {
                'index': i,
                'row': row,
                'source_ids': source_ids
            }
            source_question_ids.update(source_ids)
    
    print(f"\nStep 1: Merging grouped questions")
    print(f"  - Found {len(canonical_questions)} canonical questions")
    print(f"  - Will merge {len(source_question_ids)} source questions")
    
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
    
    # Step 2: Remove source questions and build initial list
    rows_to_remove = set(source_question_ids)
    remaining_rows = []
    
    for i, row in enumerate(rows):
        qid_str = row.get('question_id', '').strip()
        if qid_str and qid_str.isdigit():
            qid = int(qid_str)
            if qid in rows_to_remove:
                continue
        
        remaining_rows.append(row)
    
    after_grouping_count = len([r for r in remaining_rows if r.get('question_id', '').strip().isdigit()])
    print(f"  - After merging: {after_grouping_count} questions")
    
    # Step 3: Identify exact duplicates
    print(f"\nStep 2: Identifying exact duplicates")
    duplicate_groups = defaultdict(list)
    
    for i, row in enumerate(remaining_rows):
        qid_str = row.get('question_id', '').strip()
        if qid_str and qid_str.isdigit():
            # Create normalized key for duplicate detection
            key = normalize_for_duplicate_check(row)
            duplicate_groups[key].append((i, row))
    
    # Find groups with duplicates (2+ questions)
    duplicate_question_ids = set()
    duplicate_count = 0
    
    for key, group in duplicate_groups.items():
        if len(group) > 1:
            # Keep the first one (lowest question_id), mark others as duplicates
            group.sort(key=lambda x: int(x[1].get('question_id', '999999').strip()))
            kept = group[0]
            
            # Mark all others as duplicates
            for idx, dup_row in group[1:]:
                dup_qid = int(dup_row.get('question_id', '').strip())
                duplicate_question_ids.add(dup_qid)
                duplicate_count += 1
            
            # Merge years from all duplicates into the kept one
            kept_idx, kept_row = kept
            all_years = parse_years(kept_row.get('years', ''))
            
            for idx, dup_row in group[1:]:
                dup_years = parse_years(dup_row.get('years', ''))
                all_years.update(dup_years)
            
            # Update kept row with merged years
            kept_row['years'] = format_years(all_years)
            kept_row['num_years'] = str(len(all_years))
    
    print(f"  - Found {len(duplicate_groups)} unique question patterns")
    print(f"  - Found {duplicate_count} exact duplicate questions")
    print(f"  - Will remove {duplicate_count} duplicates")
    
    # Step 4: Remove duplicates
    final_rows = []
    for i, row in enumerate(remaining_rows):
        qid_str = row.get('question_id', '').strip()
        if qid_str and qid_str.isdigit():
            qid = int(qid_str)
            if qid in duplicate_question_ids:
                continue
        
        final_rows.append(row)
    
    final_count = len([r for r in final_rows if r.get('question_id', '').strip().isdigit()])
    
    print(f"\nSummary:")
    print(f"  - Started with: {original_count} questions")
    print(f"  - After merging groupings: {after_grouping_count} questions")
    print(f"  - After removing duplicates: {final_count} questions")
    print(f"  - Total reduction: {original_count - final_count} questions")
    print(f"    * From groupings: {len(source_question_ids)}")
    print(f"    * From duplicates: {duplicate_count}")
    
    # Determine output file
    if output_file is None:
        if in_place:
            output_file = input_file
        else:
            import os
            base, ext = os.path.splitext(input_file)
            output_file = f"{base}_deduped{ext}"
    
    # Write output
    print(f"\nWriting to {output_file}...")
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(final_rows)
    
    print("Done!")
    
    return {
        'original': original_count,
        'after_grouping': after_grouping_count,
        'final': final_count,
        'groupings_merged': len(source_question_ids),
        'duplicates_removed': duplicate_count,
        'total_reduction': original_count - final_count
    }


if __name__ == '__main__':
    merge_and_deduplicate()

