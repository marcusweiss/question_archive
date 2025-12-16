"""
Automatically detect and apply groupings based on identical normalized text and response scales.

This script:
- Loads questions from grouping_worksheet_full.csv
- Normalizes question_text and response_alternatives for comparison
- Identifies groups where normalized_text and normalized_response are identical
- For each group, marks the lowest question_id as canonical and lists other IDs in should_group_with
- Writes to grouping_worksheet_full_auto_grouped.csv, preserving all original rows
"""

import csv
import re
from collections import defaultdict
from typing import Dict, List, Set


def normalize_question_text(text: str) -> str:
    """Normalize question text for comparison."""
    if not text:
        return ""
    
    # Remove variable prefix patterns
    text = re.sub(r'^[a-z]+\d+[a-z]*[.:]\s*', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'\b[a-z]+\d+[a-z]*[.:]\s*', '', text, flags=re.IGNORECASE).strip()
    
    # Remove year prefixes (e.g., "1986, 1988-1990: ")
    text = re.sub(r'^\d{4}(?:,\s*\d{4}(?:-\d{4})?)*:\s*', '', text).strip()
    
    # Common prefixes to remove
    prefixes = [
        r'^åsikt om förslag i den politiska debatten\s*[-–—]\s*',
        r'^åsikt om förslag i utrikesdebatten\s*[-–—]\s*',
        r'^åsikt om förslag\s*[-–—]\s*',
        r'^vilken är din åsikt\?\s*',
        r'^din åsikt:\s*',
        r'^din åsikt om:\s*',
        r'^åsikt om:\s*',
        r'^hur ofta under de senaste 12\s*[-:]\s*',
        r'^hur ofta under de senaste 12\s+mån\??\s*[-:]\s*',
        r'^de senaste 12 månaderna:\s*',
        r'^om:\s*',
    ]
    
    # Normalize time period variations
    text = re.sub(r'\b12\s+månaderna\b', '12 mån', text, flags=re.IGNORECASE)
    text = re.sub(r'\b12\s+mån\b', '12 mån', text, flags=re.IGNORECASE)
    text = re.sub(r'\bmånaderna\b', 'mån', text, flags=re.IGNORECASE)
    text = re.sub(r'\bmånader\b', 'mån', text, flags=re.IGNORECASE)
    
    for prefix in prefixes:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE).strip()
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()


def normalize_response_alternative(alt: str) -> str:
    """Normalize a single response alternative."""
    if not isinstance(alt, str):
        return str(alt)
    
    text = alt.strip().lower()
    
    # Remove "Ej svar -" prefixes
    if text.startswith("ej svar -"):
        return ""
    
    # Fix typo: "föslag" -> "förslag"
    text = text.replace("föslag", "förslag")
    
    # Normalize time period variations
    text = re.sub(r'\bmånaderna\b', 'mån', text)
    text = re.sub(r'\bmånader\b', 'mån', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_response_alternatives(response_str: str) -> str:
    """Normalize a pipe-separated string of response alternatives."""
    if not response_str or not response_str.strip():
        return ""
    
    # Split by pipe
    alternatives = [alt.strip() for alt in response_str.split('|') if alt.strip()]
    
    # Normalize each alternative
    normalized = []
    for alt in alternatives:
        norm_alt = normalize_response_alternative(alt)
        if norm_alt:  # Skip empty alternatives
            normalized.append(norm_alt)
    
    # Sort and join back
    normalized.sort()
    return '|'.join(normalized)


def detect_delimiter(file_path: str) -> str:
    """Detect CSV delimiter (comma or semicolon)."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        if ';' in first_line and first_line.count(';') > first_line.count(','):
            return ';'
        return ','


def auto_group_from_excel(input_file: str = 'grouping_worksheet_full.csv',
                         output_file: str = 'grouping_worksheet_full_auto_grouped.csv'):
    """Auto-detect groupings and write to new CSV file."""
    
    print(f"Reading from {input_file}...")
    delimiter = detect_delimiter(input_file)
    
    # Read all rows
    rows = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    print(f"Loaded {len(rows)} rows")
    
    # Filter to only questions with valid question_id
    valid_rows = []
    for row in rows:
        qid = row.get('question_id', '').strip()
        if qid and qid.isdigit():
            valid_rows.append(row)
    
    print(f"Found {len(valid_rows)} questions with valid IDs")
    
    # Build normalized key for each question
    question_groups = defaultdict(list)
    
    for row in valid_rows:
        question_text = row.get('question_text', '').strip()
        response_alternatives = row.get('response_alternatives', '').strip()
        question_id = row.get('question_id', '').strip()
        
        # Skip if already has manual grouping
        if row.get('should_group_with', '').strip() and not row.get('should_group_with', '').strip().startswith('Auto'):
            continue
        
        # Normalize
        normalized_text = normalize_question_text(question_text)
        normalized_response = normalize_response_alternatives(response_alternatives)
        
        # Create grouping key
        if normalized_text and normalized_response:
            key = (normalized_text, normalized_response)
            question_groups[key].append((int(question_id), row))
    
    # Identify groups with 2+ questions
    groupings_found = 0
    for key, questions in question_groups.items():
        if len(questions) > 1:
            groupings_found += len(questions) - 1  # One canonical, rest are grouped
    
    print(f"Found {groupings_found} potential auto-groupings across {len([g for g in question_groups.values() if len(g) > 1])} groups")
    
    # Create a mapping of question_id to its row index in the original list
    qid_to_row_index = {}
    for i, row in enumerate(rows):
        qid = row.get('question_id', '').strip()
        if qid and qid.isdigit():
            qid_to_row_index[int(qid)] = i
    
    # Apply groupings: mark canonical questions and fill should_group_with
    for key, questions in question_groups.items():
        if len(questions) > 1:
            # Sort by question_id to get canonical (lowest ID)
            questions.sort(key=lambda x: x[0])
            canonical_id, canonical_row = questions[0]
            
            # Get IDs to group with (all others)
            group_with_ids = [str(qid) for qid, _ in questions[1:]]
            
            # Update canonical row's should_group_with
            existing_grouping = canonical_row.get('should_group_with', '').strip()
            if existing_grouping and not existing_grouping.startswith('Auto'):
                # Preserve manual grouping and add auto-groupings
                canonical_row['should_group_with'] = existing_grouping + ', Auto: ' + ', '.join(group_with_ids)
            else:
                canonical_row['should_group_with'] = 'Auto: ' + ', '.join(group_with_ids)
            
            # Update the row in the original list
            if canonical_id in qid_to_row_index:
                rows[qid_to_row_index[canonical_id]] = canonical_row
    
    # Write output
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Done! Wrote {len(rows)} rows to {output_file}")
    print(f"Auto-grouped {groupings_found} questions")
    
    return groupings_found


if __name__ == '__main__':
    auto_group_from_excel()

