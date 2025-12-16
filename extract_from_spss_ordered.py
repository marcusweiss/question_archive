"""Extract questions, items, and response scales from SPSS .sav file, preserving order."""
import pyreadstat
from pathlib import Path
import json
from typing import Dict, List, Optional, Tuple
import re

def extract_from_spss_ordered(sav_path: Path):
    """Extract questions, items, and response scales from SPSS file, preserving variable order."""
    # Read SPSS file with metadata
    df, meta = pyreadstat.read_sav(str(sav_path))
    
    print(f"Shape: {df.shape}")
    print(f"Columns: {len(df.columns)}")
    
    # Get variable labels (questions)
    variable_labels = meta.column_names_to_labels if hasattr(meta, 'column_names_to_labels') else {}
    
    # Get value labels (response scales)
    variable_value_labels = meta.variable_value_labels if hasattr(meta, 'variable_value_labels') else {}
    
    print(f"\nVariables with labels: {len(variable_labels)}")
    print(f"\nVariables with value labels: {len(variable_value_labels)}")
    
    # Track which variables we've already processed (to skip item variables)
    processed_vars = set()
    
    # Store results in order
    ordered_questions = []
    
    # Helper function to extract base name (e.g., "f1a" -> "f1", "f2" -> "f2")
    def get_base_name(var_name: str) -> str:
        # Check if it ends with a letter (likely an item variable)
        if var_name and var_name[-1].isalpha() and len(var_name) > 1:
            # Try to extract base (e.g., "f1a" -> "f1", "f3aa" -> "f3a")
            # Pattern: starts with letter(s), then digits, then optional letters
            # For "f1a" we want "f1", for "f3aa" we want "f3a"
            match = re.match(r'^([a-z]+\d+)', var_name, re.IGNORECASE)
            if match:
                return match.group(1)
        return var_name
    
    # Helper function to check if a variable is an item (has a base variable)
    def is_item_variable(var_name: str) -> bool:
        base = get_base_name(var_name)
        return base != var_name
    
    # Helper function to get all item variables for a base (including the base if it's an item)
    def get_item_variables(base_name: str, all_vars: List[str], include_base_item: bool = False) -> List[str]:
        items = []
        for var in all_vars:
            if get_base_name(var) == base_name:
                if var != base_name or include_base_item:
                    items.append(var)
        return sorted(items)
    
    # Process variables in order
    all_variables = list(df.columns)
    
    for var_name in all_variables:
        if var_name in processed_vars:
            continue
        
        base_name = get_base_name(var_name)
        is_item = is_item_variable(var_name)
        
        # Check if this variable has items (battery question)
        # Get all items for this base (excluding the base variable itself if it exists)
        item_vars = get_item_variables(base_name, all_variables, include_base_item=False)
        
        # If this is a battery question (has multiple items), group them
        # Group if: (1) there are multiple items, OR (2) current var is an item and has siblings
        should_group = len(item_vars) > 1 or (is_item and len(item_vars) >= 1)
        
        if should_group:
            # Determine the main variable to use for question text and response scale
            # Priority: base variable if exists, otherwise first item
            if base_name in all_variables and base_name not in processed_vars:
                main_var = base_name
            else:
                # Use first item as main variable
                main_var = sorted(item_vars)[0]
            
            # Get question text - try base first, then first item
            question_text = variable_labels.get(base_name, '')
            if not question_text:
                question_text = variable_labels.get(main_var, '')
            if not question_text and item_vars:
                question_text = variable_labels.get(sorted(item_vars)[0], '')
            
            # Get response scale from main variable or first item
            response_scale = None
            if main_var in variable_value_labels:
                scale_dict = variable_value_labels[main_var]
            elif item_vars and sorted(item_vars)[0] in variable_value_labels:
                scale_dict = variable_value_labels[sorted(item_vars)[0]]
            else:
                scale_dict = None
            
            if scale_dict:
                scale_values = [str(v) for k, v in sorted(scale_dict.items()) 
                              if not any(admin in str(v).lower() for admin in 
                                       ['frågan ej', 'ej svar', 'dubbelkryss', 'ej svar – hela', 'ej svar - hela'])]
                response_scale = ', '.join(scale_values)
            
            # Collect all items (include current variable if it's an item)
            items = []
            all_item_vars = sorted(item_vars)
            # If current variable is an item, include it in the items to process
            if is_item and var_name not in all_item_vars:
                all_item_vars.insert(0, var_name)
            
            for item_var in all_item_vars:
                item_question = variable_labels.get(item_var, '')
                # Only add if it's different from the main question
                if item_question and item_question != question_text:
                    items.append(item_question)
                processed_vars.add(item_var)
            
            # Mark base variable as processed if it exists
            if base_name in all_variables:
                processed_vars.add(base_name)
            
            # Use position of first item for ordering (use current var if it's an item, otherwise first item)
            if is_item:
                first_item_pos = all_variables.index(var_name)
            else:
                first_item_pos = all_variables.index(sorted(item_vars)[0]) if item_vars else all_variables.index(var_name)
            
            ordered_questions.append({
                'variable_name': base_name,
                'question': question_text,
                'response_scale': response_scale,
                'items': items,
                'position': first_item_pos
            })
            
        elif not is_item:
            # Single question (no items) - process normally
            question_text = variable_labels.get(var_name, '')
            
            # Get response scale
            response_scale = None
            if var_name in variable_value_labels:
                scale_dict = variable_value_labels[var_name]
                if scale_dict:
                    scale_values = [str(v) for k, v in sorted(scale_dict.items()) 
                                  if not any(admin in str(v).lower() for admin in 
                                           ['frågan ej', 'ej svar', 'dubbelkryss', 'ej svar – hela', 'ej svar - hela'])]
                    response_scale = ', '.join(scale_values)
            
            ordered_questions.append({
                'variable_name': var_name,
                'question': question_text,
                'response_scale': response_scale,
                'items': [],
                'position': all_variables.index(var_name)
            })
            processed_vars.add(var_name)
    
    # Sort by position to ensure correct order
    ordered_questions.sort(key=lambda x: x['position'])
    
    # Convert to dictionary format
    questions_dict = {}
    for q in ordered_questions:
        questions_dict[q['variable_name']] = {
            'question': q['question'],
            'response_scale': q['response_scale'],
            'items': q['items']
        }
    
    return questions_dict, df

if __name__ == "__main__":
    sav_path = Path(r"C:\Users\xwmarc\Desktop\AI-test\question-library\Kodböcker\cleaned\Riks-SOM 2024.sav")
    
    if not sav_path.exists():
        print(f"File not found: {sav_path}")
    else:
        questions_dict, df = extract_from_spss_ordered(sav_path)
        
        # Save to separate JSON files
        output_dir = sav_path.parent
        
        # 1. Save all questions with response scales (ordered)
        questions_output = output_dir / "spss_questions.json"
        with open(questions_output, 'w', encoding='utf-8') as f:
            json.dump(questions_dict, f, ensure_ascii=False, indent=2)
        print(f"\nSaved ordered questions to: {questions_output}")
        
        # 2. Save just questions (variable labels)
        questions_only = {var: data['question'] for var, data in questions_dict.items() if data['question']}
        questions_only_output = output_dir / "spss_questions_only.json"
        with open(questions_only_output, 'w', encoding='utf-8') as f:
            json.dump(questions_only, f, ensure_ascii=False, indent=2)
        print(f"Saved questions only to: {questions_only_output}")
        
        # 3. Save just response scales
        response_scales = {var: data['response_scale'] for var, data in questions_dict.items() if data['response_scale']}
        scales_output = output_dir / "spss_response_scales.json"
        with open(scales_output, 'w', encoding='utf-8') as f:
            json.dump(response_scales, f, ensure_ascii=False, indent=2)
        print(f"Saved response scales to: {scales_output}")
        
        # 4. Save just items
        items_output = output_dir / "spss_items.json"
        items_dict = {}
        for var_name, data in questions_dict.items():
            if data['items']:
                items_dict[var_name] = data['items']
        with open(items_output, 'w', encoding='utf-8') as f:
            json.dump(items_dict, f, ensure_ascii=False, indent=2)
        print(f"Saved items to: {items_output}")
        
        # Print first 10 in order
        print(f"\nFirst 10 questions in order:")
        count = 0
        for var_name, data in questions_dict.items():
            if count < 10:
                print(f"\n{var_name}:")
                print(f"  Question: {data['question'][:80]}...")
                print(f"  Response scale: {data['response_scale']}")
                print(f"  Items: {len(data['items'])}")
                count += 1

