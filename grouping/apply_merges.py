"""
Apply merges from merge_suggestions.csv to grouping_worksheet_full_merged.csv
Based on user review (0 = don't merge, 1 = merge)
"""

import csv
from collections import defaultdict

def read_merge_suggestions(filename, limit=2000):
    """Read first N merge suggestions"""
    merges = []
    with open(filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for i, row in enumerate(reader):
            if i >= limit:
                break
            
            # Look for merge decision column - could be "Merge?", "merge", etc.
            # Also check last column in case it's unnamed
            merge_decision = None
            merge_col = None
            for key in row.keys():
                if 'merge' in key.lower():
                    val = row[key].strip()
                    if val == '0':
                        merge_decision = False
                        merge_col = key
                        break
                    elif val == '1':
                        merge_decision = True
                        merge_col = key
                        break
            
            # If not found, check if last column value is 0 or 1
            if merge_decision is None:
                all_values = list(row.values())
                if all_values:
                    last_val = all_values[-1].strip()
                    if last_val == '0':
                        merge_decision = False
                    elif last_val == '1':
                        merge_decision = True
            
            # Debug: show first few rows with decisions
            if i < 5 and merge_decision is not None:
                print(f"  Row {i+1}: Found merge decision {merge_decision} in column '{merge_col or 'last'}'")
            
            # Only process if there's a decision (0 or 1)
            # Skip empty values (not yet reviewed)
            if merge_decision is not None:
                q1_id = row.get('q1_id', '').strip()
                q2_id = row.get('q2_id', '').strip()
                if q1_id and q2_id:
                    merges.append({
                        'q1_id': q1_id,
                        'q2_id': q2_id,
                        'should_merge': merge_decision
                    })
    return merges

def read_questions(filename):
    """Read questions from merged worksheet"""
    questions = {}
    try:
        # Try backup file if main is empty
        backup_file = filename.replace('.csv', ' - kopia.csv')
        import os
        if os.path.exists(backup_file):
            file_to_read = backup_file
            print(f"  Reading from backup: {backup_file}")
        else:
            file_to_read = filename
            
        with open(file_to_read, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                qid = row.get('question_id', '').strip()
                if qid:  # Only add if question_id exists
                    # Ensure should_group_with column exists
                    if 'should_group_with' not in row:
                        row['should_group_with'] = ''
                    questions[qid] = row
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        import traceback
        traceback.print_exc()
    return questions

def apply_merges(questions, merges):
    """Apply merge decisions to questions"""
    # Track which questions should be grouped with which
    # q1_id is the target (kept), q2_id is merged into q1
    merge_map = defaultdict(set)
    
    for merge in merges:
        if merge['should_merge']:
            q1_id = merge['q1_id']
            q2_id = merge['q2_id']
            # q2 should be merged into q1
            merge_map[q1_id].add(q2_id)
    
    # Update questions with should_group_with
    for q1_id, q2_ids in merge_map.items():
        if q1_id in questions:
            # Combine existing should_group_with with new ones
            existing = questions[q1_id].get('should_group_with', '').strip()
            existing_ids = set()
            if existing:
                # Try to extract numeric IDs from existing value
                for x in existing.split(','):
                    x = x.strip()
                    # Only keep if it's a numeric ID
                    if x.isdigit():
                        existing_ids.add(x)
            
            # Add new IDs (ensure they're all strings)
            all_ids = existing_ids | {str(qid) for qid in q2_ids}
            if all_ids:
                # Sort numerically
                sorted_ids = sorted(all_ids, key=lambda x: int(x) if x.isdigit() else 999999)
                questions[q1_id]['should_group_with'] = ', '.join(sorted_ids)
    
    return questions

def write_questions(filename, questions):
    """Write updated questions back to CSV"""
    if not questions:
        return
    
    # Get fieldnames from first question
    fieldnames = list(questions[list(questions.keys())[0]].keys())
    
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

def remove_processed_suggestions(filename, num_to_remove=2000):
    """Remove first N rows from merge_suggestions.csv"""
    rows = []
    with open(filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        fieldnames = reader.fieldnames
        for i, row in enumerate(reader):
            if i >= num_to_remove:
                rows.append(row)
    
    # Write back remaining rows
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)

def main():
    print("Step 1: Counting questions in grouping_worksheet_full_merged.csv...")
    questions = read_questions('grouping_worksheet_full_merged.csv')
    initial_count = len(questions)
    print(f"Initial question count: {initial_count}")
    
    print("\nStep 2: Reading merge suggestions (first 2000)...")
    merges = read_merge_suggestions('merge_suggestions.csv', limit=2000)
    print(f"Found {len(merges)} merge decisions")
    
    # Count how many should merge
    should_merge_count = sum(1 for m in merges if m['should_merge'])
    print(f"  - Should merge: {should_merge_count}")
    print(f"  - Should NOT merge: {len(merges) - should_merge_count}")
    
    print("\nStep 3: Applying merges...")
    questions = apply_merges(questions, merges)
    
    print("\nStep 4: Writing updated questions...")
    write_questions('grouping_worksheet_full_merged.csv', questions)
    
    print("\nStep 5: Removing processed suggestions from merge_suggestions.csv...")
    remove_processed_suggestions('merge_suggestions.csv', num_to_remove=2000)
    
    print("\nStep 6: Re-counting questions...")
    questions_after = read_questions('grouping_worksheet_full_merged.csv')
    final_count = len(questions_after)
    
    print(f"\nFinal question count: {final_count}")
    print(f"Questions removed through merging: {initial_count - final_count}")
    
    # Count how many now have should_group_with
    with_grouping = sum(1 for q in questions_after.values() if q.get('should_group_with', '').strip())
    print(f"Questions with should_group_with set: {with_grouping}")

if __name__ == '__main__':
    main()

