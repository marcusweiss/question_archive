"""
Split merge_suggestions.csv into two files based on years_overlap:
- merge_suggestions_noyears.csv: suggestions where years DON'T overlap
- merge_suggestions_yesyears.csv: suggestions where years DO overlap
"""

import csv

def split_suggestions(input_file, no_years_file, yes_years_file):
    """Split merge suggestions by years_overlap"""
    no_years_rows = []
    yes_years_rows = []
    
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        fieldnames = reader.fieldnames
        
        for row in reader:
            years_overlap = row.get('years_overlap', '').strip()
            
            # Check if years_overlap is True/False (case-insensitive)
            if years_overlap.lower() == 'true':
                yes_years_rows.append(row)
            elif years_overlap.lower() == 'false':
                no_years_rows.append(row)
            else:
                # If unclear, check the actual years
                q1_years = set(y.strip() for y in row.get('q1_years', '').split(',')) if row.get('q1_years') else set()
                q2_years = set(y.strip() for y in row.get('q2_years', '').split(',')) if row.get('q2_years') else set()
                overlap = q1_years & q2_years
                
                if overlap:
                    yes_years_rows.append(row)
                else:
                    no_years_rows.append(row)
    
    # Write no_years file
    print(f"Writing {len(no_years_rows)} suggestions WITHOUT year overlap to {no_years_file}...")
    with open(no_years_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(no_years_rows)
    
    # Write yes_years file
    print(f"Writing {len(yes_years_rows)} suggestions WITH year overlap to {yes_years_file}...")
    with open(yes_years_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(yes_years_rows)
    
    return len(no_years_rows), len(yes_years_rows)

def main():
    input_file = 'merge_suggestions.csv'
    no_years_file = 'merge_suggestions_noyears.csv'
    yes_years_file = 'merge_suggestions_yesyears.csv'
    
    print(f"Reading from {input_file}...")
    no_count, yes_count = split_suggestions(input_file, no_years_file, yes_years_file)
    
    print(f"\nSummary:")
    print(f"  - Suggestions WITHOUT year overlap: {no_count}")
    print(f"  - Suggestions WITH year overlap: {yes_count}")
    print(f"  - Total: {no_count + yes_count}")

if __name__ == '__main__':
    main()

