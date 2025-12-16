"""
Apply merges and actually remove merged questions from grouping_worksheet_full_merged.csv
This processes the should_group_with column and merges questions, removing duplicates.
"""

import csv
import re
from collections import defaultdict

def parse_years(years_str):
    """Parse years string into sorted list of years"""
    if not years_str or not years_str.strip():
        return []
    years = []
    for part in years_str.split(','):
        part = part.strip()
        if '-' in part:
            # Handle ranges like "1999-2001"
            start, end = part.split('-')
            years.extend(range(int(start.strip()), int(end.strip()) + 1))
        else:
            try:
                years.append(int(part))
            except ValueError:
                continue
    return sorted(set(years))

def format_years(years_list):
    """Format sorted years list back to string format"""
    if not years_list:
        return ""
    
    # Group consecutive years
    years = sorted(set(years_list))
    result = []
    i = 0
    while i < len(years):
        start = years[i]
        # Find consecutive range
        j = i
        while j + 1 < len(years) and years[j + 1] == years[j] + 1:
            j += 1
        end = years[j]
        
        if start == end:
            result.append(str(start))
        else:
            result.append(f"{start}-{end}")
        i = j + 1
    
    return ", ".join(result)

def read_questions(filename):
    """Read questions from merged worksheet"""
    questions = {}
    try:
        # Try backup file if main is empty
        backup_file = filename.replace('.csv', ' - kopia.csv')
        import os
        if os.path.exists(backup_file) and os.path.getsize(filename) < 100:
            file_to_read = backup_file
            print(f"  Reading from backup: {backup_file}")
        else:
            file_to_read = filename
            
        with open(file_to_read, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            fieldnames = reader.fieldnames
            for row in reader:
                qid = row.get('question_id', '').strip()
                if qid:  # Only add if question_id exists
                    # Ensure should_group_with column exists
                    if 'should_group_with' not in row:
                        row['should_group_with'] = ''
                    questions[qid] = row
        return questions, fieldnames
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        import traceback
        traceback.print_exc()
        return {}, []

def merge_questions(questions):
    """Merge questions based on should_group_with column"""
    # Track which questions should be removed (they're merged into others)
    to_remove = set()
    
    # Process each question that has should_group_with
    for qid, q in list(questions.items()):
        should_group_with = q.get('should_group_with', '').strip()
        if not should_group_with:
            continue
        
        # Parse IDs to merge
        source_ids = [x.strip() for x in should_group_with.split(',') if x.strip()]
        
        # Collect years from all source questions
        all_years = set(parse_years(q.get('years', '')))
        
        # Process each source question
        for source_id in source_ids:
            if source_id in questions:
                source_q = questions[source_id]
                # Add source question's years
                source_years = parse_years(source_q.get('years', ''))
                all_years.update(source_years)
                
                # Mark source for removal
                to_remove.add(source_id)
            else:
                print(f"  Warning: Source question {source_id} not found (referenced by {qid})")
        
        # Update target question with combined years
        combined_years = format_years(list(all_years))
        q['years'] = combined_years
        if combined_years:
            # Count years
            years_list = parse_years(combined_years)
            q['num_years'] = len(years_list)
        
        # Clear should_group_with after processing
        q['should_group_with'] = ''
    
    # Remove merged questions
    for qid in to_remove:
        if qid in questions:
            del questions[qid]
    
    return questions, len(to_remove)

def write_questions(filename, questions, fieldnames):
    """Write updated questions back to CSV"""
    if not questions:
        return
    
    # Ensure should_group_with is in fieldnames
    if 'should_group_with' not in fieldnames:
        fieldnames = list(fieldnames) + ['should_group_with']
    
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        # Write in question_id order (handle non-numeric IDs)
        def sort_key(qid):
            try:
                return int(qid) if qid else 999999
            except ValueError:
                return 999999
        
        for qid in sorted(questions.keys(), key=sort_key):
            writer.writerow(questions[qid])

def main():
    print("Step 1: Reading questions from grouping_worksheet_full_merged.csv...")
    questions, fieldnames = read_questions('grouping_worksheet_full_merged.csv')
    initial_count = len(questions)
    print(f"Initial question count: {initial_count}")
    
    # Count how many have should_group_with
    with_grouping = sum(1 for q in questions.values() if q.get('should_group_with', '').strip())
    print(f"Questions with should_group_with set: {with_grouping}")
    
    print("\nStep 2: Merging questions...")
    questions, removed_count = merge_questions(questions)
    print(f"Removed {removed_count} merged questions")
    
    print("\nStep 3: Writing updated questions...")
    write_questions('grouping_worksheet_full_merged.csv', questions, fieldnames)
    
    print("\nStep 4: Final count...")
    final_count = len(questions)
    print(f"\nFinal question count: {final_count}")
    print(f"Questions removed through merging: {initial_count - final_count}")
    
    # Verify no should_group_with remain
    remaining_grouping = sum(1 for q in questions.values() if q.get('should_group_with', '').strip())
    print(f"Questions with should_group_with remaining: {remaining_grouping}")

if __name__ == '__main__':
    main()

