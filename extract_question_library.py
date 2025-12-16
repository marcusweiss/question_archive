"""
Extract question library from codebook PDF and Stata file.

This script extracts:
- All questions with their variable names
- Sub-questions for batteries
- All response alternatives (excluding missing codes 94-99)
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import sys

# Try to import required libraries
try:
    import pdfplumber
except ImportError:
    print("Installing pdfplumber...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
    import pdfplumber

try:
    import pyreadstat
except ImportError:
    print("Installing pyreadstat...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyreadstat"])
    import pyreadstat


def extract_value_labels(spss_path: Path):
    """Extract value labels metadata from SPSS file."""
    print(f"Reading SPSS file: {spss_path}")
    df, meta = pyreadstat.read_sav(str(spss_path), metadataonly=True)
    
    # For SPSS, we return the meta object directly since value labels are accessed via variable_value_labels
    print(f"Found value labels for {len(meta.variable_value_labels) if hasattr(meta, 'variable_value_labels') and meta.variable_value_labels else 0} variables")
    return meta


def extract_variable_labels(spss_path: Path) -> Dict[str, str]:
    """Extract variable labels from SPSS file."""
    print(f"Extracting variable labels from: {spss_path}")
    df, meta = pyreadstat.read_sav(str(spss_path), metadataonly=True)
    
    variable_labels = {}
    
    # pyreadstat returns column_labels as a list, matching column_names
    if hasattr(meta, 'column_names') and hasattr(meta, 'column_labels'):
        col_names = meta.column_names
        col_labels = meta.column_labels
        
        # Handle both list and dict formats
        if isinstance(col_names, list) and isinstance(col_labels, list):
            variable_labels = dict(zip(col_names, col_labels))
        elif isinstance(col_labels, dict):
            variable_labels = col_labels
        else:
            # Fallback: try to get from dataframe
            if df is not None:
                for col in df.columns:
                    variable_labels[col] = ""  # Default empty
    
    print(f"Found labels for {len(variable_labels)} variables")
    return variable_labels


def is_missing_code(value: int) -> bool:
    """Check if a value is a missing code (typically 94-99)."""
    return 94 <= value <= 99


def extract_questions_from_pdf(pdf_path: Path) -> List[Dict]:
    """
    Extract questions from PDF codebook.
    Returns a list of question dictionaries with variable names, question text, and response alternatives.
    """
    print(f"Extracting questions from PDF: {pdf_path}")
    questions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"PDF has {len(pdf.pages)} pages")
        
        current_question = None
        current_variable = None
        in_response_section = False
        response_alternatives = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                line_clean = line.strip()
                if not line_clean:
                    continue
                
                # Look for variable names (common patterns: v1, q1, var1, etc.)
                # Variable names are typically at the start of a line, followed by question text
                var_match = re.match(r'^([a-z]+\d+[a-z0-9]*)\s+(.+)$', line_clean, re.IGNORECASE)
                
                if var_match:
                    # Save previous question if exists
                    if current_question:
                        questions.append({
                            "variable": current_variable,
                            "question_text": current_question,
                            "response_alternatives": response_alternatives.copy()  # Simple list of labels
                        })
                    
                    # Start new question
                    current_variable = var_match.group(1).strip()
                    current_question = var_match.group(2).strip()
                    response_alternatives = []
                    in_response_section = False
                    continue
                
                # Look for response alternatives (typically numbers followed by text)
                # Pattern: "1. Alternative text" or "1 Alternative text" or "(1) Alternative text"
                response_match = re.match(r'^[\(]?(\d+)[\.\)]?\s+(.+)$', line_clean)
                
                if response_match:
                    value = int(response_match.group(1))
                    label = response_match.group(2).strip()
                    
                    # Skip missing codes
                    if is_missing_code(value):
                        continue
                    
                    # Just store the label as a string
                    response_alternatives.append(label)
                    in_response_section = True
                    continue
                
                # Look for sub-questions in batteries (indented or with specific markers)
                # These might be continuation lines or sub-question indicators
                if current_question and (line_clean.startswith('-') or 
                                        line_clean.startswith('•') or
                                        re.match(r'^[a-z]\)', line_clean, re.IGNORECASE)):
                    # Might be a continuation of the main question
                    current_question += " " + line_clean
                    continue
                
                # Continuation of question text (if not in response section)
                if current_question and not in_response_section and len(line_clean) > 10:
                    current_question += " " + line_clean
        
        # Don't forget the last question
        if current_question:
            questions.append({
                "variable": current_variable,
                "question_text": current_question,
                "response_alternatives": response_alternatives.copy()  # Simple list of labels
            })
    
    print(f"Extracted {len(questions)} questions from PDF")
    return questions


def get_spss_value_labels(meta, var_name: str) -> Dict[int, str]:
    """Get value labels for a variable from SPSS metadata, handling case-insensitive matching."""
    # SPSS stores value labels in variable_value_labels dict, where key is var name and value is the labels dict
    if not hasattr(meta, 'variable_value_labels') or not meta.variable_value_labels:
        return {}
    
    # Try exact match first
    if var_name in meta.variable_value_labels:
        vl = meta.variable_value_labels[var_name]
    # Try uppercase
    elif var_name.upper() in meta.variable_value_labels:
        vl = meta.variable_value_labels[var_name.upper()]
    # Try lowercase
    elif var_name.lower() in meta.variable_value_labels:
        # Find the actual key (case-sensitive)
        actual_key = next((k for k in meta.variable_value_labels.keys() if k.lower() == var_name.lower()), None)
        if actual_key:
            vl = meta.variable_value_labels[actual_key]
        else:
            return {}
    else:
        return {}
    
    # Convert float keys to integers and filter missing codes
    result = {}
    for key, label in vl.items():
        try:
            # SPSS uses float keys (1.0, 2.0, etc.)
            value = int(float(key))
            if not is_missing_code(value):
                result[value] = label
        except (ValueError, TypeError):
            continue
    
    return result


def merge_pdf_and_stata_data(
    pdf_questions: List[Dict],
    variable_labels: Dict[str, str],
    value_labels: Dict[str, Dict]
) -> List[Dict]:
    """
    Merge PDF-extracted questions with Stata metadata.
    Enriches questions with variable labels and value labels from Stata.
    """
    print("Merging PDF and Stata data...")
    
    # Create case-insensitive lookup for variable labels
    var_label_lookup = {}
    for k, v in variable_labels.items():
        var_label_lookup[k.lower()] = (k, v)  # Store original key and value
    
    merged_questions = []
    processed_variables = set()
    
    for pdf_q in pdf_questions:
        var_name = pdf_q.get("variable")
        if not var_name:
            continue
        
        # Get variable label from Stata (case-insensitive)
        stata_label = ""
        original_var_name = var_name
        if var_name.lower() in var_label_lookup:
            original_var_name, stata_label = var_label_lookup[var_name.lower()]
        
        # Get value labels from SPSS (case-insensitive)
        stata_value_labels = get_spss_value_labels(value_labels, original_var_name)
        
        # Merge response alternatives - just keep labels as a simple list
        merged_alternatives = []
        
        # Use Stata value labels as primary source
        if stata_value_labels:
            for value in sorted(stata_value_labels.keys()):
                merged_alternatives.append(stata_value_labels[value])
        else:
            # Fallback to PDF-extracted alternatives (already simple list)
            merged_alternatives.extend(pdf_q.get("response_alternatives", []))
        
        # Determine question text (prefer Stata label)
        question_text = stata_label if stata_label else pdf_q.get("question_text", "")
        
        merged_questions.append({
            "variable": original_var_name,  # Use original Stata variable name
            "question_text": question_text,
            "response_alternatives": merged_alternatives,  # Simple list of labels
            "source": "merged"
        })
        processed_variables.add(original_var_name.lower())
    
    # Also include variables that exist in SPSS but not in PDF
    for var_name, var_label in variable_labels.items():
        if var_name.lower() not in processed_variables:
            stata_value_labels = get_spss_value_labels(value_labels, var_name)
            alternatives = []
            
            for value in sorted(stata_value_labels.keys()):
                alternatives.append(stata_value_labels[value])
            
            merged_questions.append({
                "variable": var_name,
                "question_text": var_label,
                "response_alternatives": alternatives,  # Simple list of labels
                "source": "stata_only"
            })
    
    print(f"Merged {len(merged_questions)} questions total")
    return merged_questions


def extract_common_stem(texts: List[str]) -> Tuple[str, List[str]]:
    """
    Extract common question stem and sub-items from battery question texts.
    Returns (common_stem, sub_items)
    Handles cases where the first item might be different from the rest.
    """
    if not texts:
        return "", []
    
    # Remove variable prefixes (e.g., "f1a. ", "f1b. ")
    cleaned_texts = []
    for text in texts:
        # Remove variable prefix pattern (e.g., "f1a. ", "f1b. ")
        cleaned = re.sub(r'^[a-z]+\d+[a-z]*\.\s*', '', text, flags=re.IGNORECASE).strip()
        cleaned_texts.append(cleaned)
    
    if not cleaned_texts:
        return "", []
    
    # Check if first item is significantly different from the rest
    # If we have 3+ items and first is different, use items 2+ for stem extraction
    if len(cleaned_texts) >= 3:
        first_text = cleaned_texts[0]
        other_texts = cleaned_texts[1:]
        
        # Check if first text shares a common separator pattern with others
        separators = [" - ", ": ", ". ", "? ", " från ", " hos ", " om ", " gjort följande "]
        first_has_common_sep = False
        
        for sep in separators:
            first_pos = first_text.find(sep)
            if first_pos != -1:
                # Check if at least 2 other texts have the same separator
                matching_count = sum(1 for text in other_texts if text.find(sep) != -1)
                if matching_count >= 2:
                    first_has_common_sep = True
                    break
        
        # If first doesn't share common pattern, extract stem from items 2+
        if not first_has_common_sep:
            # Extract stem from items 2+
            stem, sub_items_rest = extract_common_stem_from_list(other_texts)
            # First item becomes first sub-item
            sub_items = [first_text] + sub_items_rest
            return stem, sub_items
    
    # Normal extraction for all items
    return extract_common_stem_from_list(cleaned_texts)


def extract_common_stem_from_list(texts: List[str]) -> Tuple[str, List[str]]:
    """
    Extract common stem from a list of texts (helper function).
    """
    if not texts:
        return "", []
    
    # First, try to find separator patterns that indicate where stem ends
    separators = [" - ", ": ", ". ", "? ", " från ", " hos ", " om ", " gjort följande "]
    common_sep_pos = None
    
    for sep in separators:
        positions = []
        for text in texts:
            pos = text.find(sep)
            if pos != -1:
                positions.append(pos)
        
        # If all texts have the same separator at the same position, use it
        if len(positions) == len(texts) and len(set(positions)) == 1:
            common_sep_pos = positions[0] + len(sep)
            break
    
    if common_sep_pos is not None:
        # Use separator-based extraction
        common_stem = texts[0][:common_sep_pos].strip()
        sub_items = []
        for text in texts:
            sub_item = text[common_sep_pos:].strip()
            # Remove leading dashes, colons, spaces
            sub_item = re.sub(r'^[-:\s]+', '', sub_item).strip()
            if sub_item:
                sub_items.append(sub_item)
        return common_stem, sub_items
    
    # Fallback: find common prefix by character comparison
    first_text = texts[0]
    common_end = len(first_text)
    
    for text in texts[1:]:
        # Find where the texts diverge
        min_len = min(len(first_text), len(text))
        for i in range(min_len):
            if first_text[i] != text[i]:
                common_end = min(common_end, i)
                break
        common_end = min(common_end, min_len)
    
    # Extract common stem (try to end at word boundary)
    common_stem = first_text[:common_end].strip()
    # Try to extend to end of last word if we're in the middle
    if common_end < len(first_text) and common_end > 0:
        # Find last space before divergence
        last_space = common_stem.rfind(' ')
        if last_space > len(common_stem) * 0.5:  # If space is in second half, use it
            common_stem = first_text[:last_space + 1].strip()
            common_end = last_space + 1
    
    # Extract sub-items (the parts after the common stem)
    sub_items = []
    for text in texts:
        if len(text) > len(common_stem):
            sub_item = text[len(common_stem):].strip()
            # Remove leading dashes, colons, spaces
            sub_item = re.sub(r'^[-:\s]+', '', sub_item).strip()
            if sub_item:
                sub_items.append(sub_item)
        else:
            # If text is shorter than stem, use the whole text as sub-item
            sub_items.append(text)
    
    return common_stem, sub_items


def natural_sort_key(var_name: str) -> tuple:
    """Natural sort key for variable names like f1, f2, f10, alder8"""
    if not var_name:
        return ('', 0, '')
    # Extract prefix and number
    match = re.match(r'^([a-z]+)(\d+)(.*)$', var_name.lower())
    if match:
        prefix = match.group(1)
        number = int(match.group(2))
        suffix = match.group(3)
        return (prefix, number, suffix)
    return (var_name.lower(), 0, '')


def identify_batteries(questions: List[Dict]) -> Tuple[List[Dict], Set[str]]:
    """
    Identify battery questions and extract simplified structure.
    Returns (batteries, battery_variable_names) where battery_variable_names is a set
    of all variable names that are part of batteries (to exclude from regular questions).
    """
    print("Identifying battery questions...")
    
    # Group variables by base name
    battery_groups = {}
    
    for q in questions:
        var_name = q.get("variable", "")
        if not var_name:
            continue
        
        # Try to extract base name (e.g., "f1" from "f1a", "f1b", "f1aa", "f1ab", etc.)
        # Pattern: base name followed by one or more letters (and possibly more letters/numbers)
        base_match = re.match(r'^([a-z]+\d+)([a-z]+)', var_name, re.IGNORECASE)
        if base_match:
            base_name = base_match.group(1).lower()
            if base_name not in battery_groups:
                battery_groups[base_name] = []
            battery_groups[base_name].append(q)
    
    # Identify actual batteries (groups with 2+ questions)
    batteries = []
    battery_variable_names = set()
    
    for base_name, group in battery_groups.items():
        if len(group) > 1:
            # Sort by variable name to maintain order
            sorted_group = sorted(group, key=lambda x: x.get("variable", "").lower())
            
            # Collect question texts and response alternatives
            question_texts = [q.get("question_text", "") for q in sorted_group]
            response_alternatives = sorted_group[0].get("response_alternatives", [])
            
            # For batteries, use the most common response alternatives (or first if all different)
            # Count alternatives frequency
            alt_counts = {}
            for q in sorted_group:
                alts = tuple(q.get("response_alternatives", []))
                alt_counts[alts] = alt_counts.get(alts, 0) + 1
            
            # Use the most common alternatives, or first if all are different
            if alt_counts:
                most_common_alternatives = max(alt_counts.items(), key=lambda x: x[1])[0]
                response_alternatives = list(most_common_alternatives)
                
                # Check if this is an open-ended question with many alternatives
                if len(response_alternatives) >= 20:
                    response_alternatives = ["öppen fråga"]
                
                # Extract common stem and sub-items
                common_stem, sub_items = extract_common_stem(question_texts)
                
                # Collect variable names for exclusion
                for q in sorted_group:
                    battery_variable_names.add(q.get("variable", "").lower())
                
                batteries.append({
                    "variable": base_name,
                    "question_text": common_stem,
                    "sub_items": sub_items,
                    "response_alternatives": response_alternatives if response_alternatives else []
                })
    
    print(f"Identified {len(batteries)} battery groups")
    
    # Sort batteries by variable name (natural sort)
    batteries.sort(key=lambda b: natural_sort_key(b.get("variable", "")))
    
    return batteries, battery_variable_names


def main():
    base_path = Path(__file__).parent
    spss_path = base_path / "Riks-SOM 2024.sav"
    
    if not spss_path.exists():
        print(f"Error: SPSS file not found at {spss_path}")
        return
    
    # Extract from SPSS file
    print("Extracting data from SPSS file...")
    variable_labels = extract_variable_labels(spss_path)
    value_labels = extract_value_labels(spss_path)
    
    # Build questions list from Stata data only
    all_questions = []
    for var_name, var_label in variable_labels.items():
        # Get value labels for this variable
        stata_value_labels = get_spss_value_labels(value_labels, var_name)
        alternatives = []
        
        for value in sorted(stata_value_labels.keys()):
            alternatives.append(stata_value_labels[value])
        
        all_questions.append({
            "variable": var_name,
            "question_text": var_label,
            "response_alternatives": alternatives
        })
    
    # Identify batteries
    batteries, battery_variable_names = identify_batteries(all_questions)
    
    # Filter out invalid questions and exclude battery sub-questions
    valid_questions = []
    seen_variables = set()  # Track to avoid duplicates
    
    # Also check if variable is a battery sub-question by pattern matching
    def is_battery_subquestion(var_name: str) -> bool:
        """Check if a variable is part of a battery (e.g., f1a, f1b, f2aa, etc.)"""
        var_lower = var_name.lower()
        # Check if it's in the battery variable names set
        if var_lower in battery_variable_names:
            return True
        # Also check pattern: base name + letters (e.g., f1a, f2b, etc.)
        match = re.match(r'^([a-z]+\d+)([a-z]+)', var_lower)
        if match:
            base_name = match.group(1)
            # Check if this base name has a battery
            for battery in batteries:
                if battery.get("variable", "").lower() == base_name:
                    return True
        return False
    
    for q in all_questions:
        var_name = q.get("variable", "")
        var_name_lower = var_name.lower()
        question_text = q.get("question_text", "").strip()
        
        # Skip duplicates
        if var_name_lower in seen_variables:
            continue
        seen_variables.add(var_name_lower)
        
        # Skip battery sub-questions (they're in the batteries section)
        if is_battery_subquestion(var_name):
            continue
        
        # Skip questions with just "-" or very short text (likely metadata)
        if question_text and question_text != "-" and len(question_text) > 3:
            # Also skip if it looks like author/affiliation info
            if not ("," in question_text and any(word in question_text.lower() for word in ["universitet", "institut", "göteborgs"])):
                # Skip technical/metadata variables (case-insensitive)
                # Note: mtidn is included as it's an open question, not skipped
                skip_patterns = ["löpnr", "formid", "indatum", "mode"]
                if not any(var_name_lower.startswith(pattern) for pattern in skip_patterns):
                    # Check if this is an open-ended question with many alternatives
                    alternatives = q.get("response_alternatives", [])
                    if len(alternatives) >= 20:
                        # Mark as open question
                        alternatives = ["öppen fråga"]
                    
                    valid_q = {
                        "variable": q.get("variable"),
                        "question_text": question_text,
                        "response_alternatives": alternatives
                    }
                    valid_questions.append(valid_q)
    
    # Sort questions by variable name (natural sort)
    valid_questions.sort(key=lambda q: natural_sort_key(q.get("variable", "")))
    
    # Create output structure
    output = {
        "year": 2024,
        "source_files": {
            "spss": str(spss_path.name)
        },
        "total_questions": len(valid_questions),
        "questions_with_alternatives": len([q for q in valid_questions if q.get("response_alternatives")]),
        "batteries": batteries,
        "questions": valid_questions
    }
    
    # Save output
    output_path = base_path / "question_library_2024.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\nQuestion library saved to: {output_path}")
    print(f"Total questions: {len(valid_questions)}")
    print(f"Batteries identified: {len(batteries)}")
    print(f"\nSample questions:")
    for q in valid_questions[:5]:
        alt_count = len(q.get('response_alternatives', []))
        print(f"  {q.get('variable')}: {q.get('question_text', '')[:60]}...")
        print(f"    Alternatives ({alt_count}): {q.get('response_alternatives', [])[:3] if alt_count > 0 else 'None'}...")


if __name__ == "__main__":
    main()

