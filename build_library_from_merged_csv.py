"""
Build the cross-year question library from grouping_worksheet_full_merged.csv
This uses the already-merged CSV file instead of reading from SPSS files.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Set

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

def build_library_from_merged_csv(input_file: str = 'grouping/grouping_worksheet_full_merged.csv',
                                  output_file: str = 'question_library_cross_year.json'):
    """Build the cross-year library from the merged CSV file."""
    
    base_path = Path(__file__).parent
    input_path = base_path / input_file
    
    print(f"Reading from {input_path}...")
    
    questions = []
    all_years = set()
    
    with open(input_path, 'r', encoding='utf-8-sig') as f:
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
            all_years.update(years)
            
            # Get question text
            question_text = row.get('question_text', '').strip()
            
            # Parse response alternatives
            response_alternatives_str = row.get('response_alternatives', '').strip()
            if response_alternatives_str:
                response_alternatives = [alt.strip() for alt in response_alternatives_str.split('|') if alt.strip()]
            else:
                response_alternatives = []
            
            # Format years for display
            years_str = format_years(years)
            
            # Build question entry
            question = {
                "question_text": f"{years_str}: {question_text}" if years_str else question_text,
                "full_question_text": f"{years_str}: {question_text}" if years_str else question_text,
                "response_alternatives": response_alternatives,
                "years": {str(year): "" for year in years},  # Empty variable names since we don't have them
                "type": "cross_year" if len(years) > 1 else "single_year",
                "question_id": qid,
                "num_years": len(years),
                "years_list": sorted(years)
            }
            
            questions.append(question)
    
    # Sort by question text
    questions.sort(key=lambda q: q.get("question_text", "").lower())
    
    print(f"\nFinal library contains {len(questions)} questions")
    print(f"Years covered: {sorted(all_years)}")
    
    # Build output structure (matching the format expected by the search interface)
    output = {
        "years": sorted(all_years),
        "total_unique_questions": len(questions),
        "total_unique_batteries": 0,  # No batteries in merged CSV
        "questions": questions,
        "batteries": []
    }
    
    # Save output
    output_path = base_path / output_file
    print(f"Writing to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== Summary ===")
    print(f"Years: {output['years']}")
    print(f"Total questions: {len(questions)}")
    print(f"Questions with response alternatives: {sum(1 for q in questions if q.get('response_alternatives'))}")
    print(f"Questions appearing in multiple years: {sum(1 for q in questions if len(q.get('years_list', [])) > 1)}")
    print(f"\nSaved to: {output_path}")
    
    return output

if __name__ == "__main__":
    build_library_from_merged_csv()

