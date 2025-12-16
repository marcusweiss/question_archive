"""
Build the final question library from grouping_worksheet_full_merged.csv
This version works with the simplified structure (no parent_question, item columns)
"""

import csv
import json
import re
from typing import Dict, List, Set
from collections import defaultdict

def parse_years(years_str: str) -> Set[int]:
    """Parse years string into a set of integers."""
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
    """Format a set of years into a compact string representation."""
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

def build_library(input_file: str = 'grouping_worksheet_full_merged.csv',
                  output_file: str = 'question_library_merged.json'):
    """Build the final question library from the merged CSV file."""
    
    print(f"Reading from {input_file}...")
    
    questions = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            qid_str = row.get('question_id', '').strip()
            if not qid_str:
                continue
            
            # Parse question ID
            try:
                qid = int(qid_str)
            except ValueError:
                # Skip non-numeric IDs
                continue
            
            # Parse years
            years = parse_years(row.get('years', ''))
            
            # Get question text
            question_text = row.get('question_text', '').strip()
            
            # Parse response alternatives
            response_alternatives_str = row.get('response_alternatives', '').strip()
            if response_alternatives_str:
                response_alternatives = [alt.strip() for alt in response_alternatives_str.split('|') if alt.strip()]
            else:
                response_alternatives = []
            
            # Build question entry
            question = {
                'question_id': qid,
                'question_text': question_text,
                'years': format_years(years),
                'years_list': sorted(years),
                'num_years': len(years),
                'response_alternatives': response_alternatives,
                'num_responses': len(response_alternatives)
            }
            
            questions.append(question)
    
    # Sort by question_id
    questions.sort(key=lambda x: x['question_id'])
    
    print(f"\nFinal library contains {len(questions)} questions")
    
    # Build output structure
    output = {
        'source_file': input_file,
        'total_questions': len(questions),
        'questions_with_alternatives': sum(1 for q in questions if q['num_responses'] > 0),
        'questions': questions
    }
    
    # Write JSON
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("Done!")
    print(f"\nSummary:")
    print(f"  - Total questions: {len(questions)}")
    print(f"  - Questions with response alternatives: {output['questions_with_alternatives']}")
    print(f"  - Questions without alternatives: {len(questions) - output['questions_with_alternatives']}")
    
    return output

if __name__ == '__main__':
    build_library()

