"""
Build a cross-year searchable question library from multiple SPSS files.

This script:
- Extracts questions from multiple years (2023, 2024, etc.)
- Groups similar questions across years
- Tracks variations in items and response alternatives
- Creates a searchable library structure
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
import sys

try:
    import pyreadstat
except ImportError:
    print("Installing pyreadstat...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyreadstat"])
    import pyreadstat

# Import functions from the single-year extraction script
from extract_question_library import (
    extract_variable_labels,
    extract_value_labels,
    get_spss_value_labels,
    is_missing_code,
    identify_batteries,
    natural_sort_key
)


def extract_year_questions(spss_path: Path, year: int) -> Tuple[List[Dict], List[Dict]]:
    """Extract questions and batteries from a single year's SPSS file."""
    print(f"\n=== Extracting {year} ===")
    
    if not spss_path.exists():
        print(f"Warning: File not found: {spss_path}")
        return [], []
    
    # Extract from SPSS file
    variable_labels = extract_variable_labels(spss_path)
    value_labels_meta = extract_value_labels(spss_path)
    
    # Build questions list
    all_questions = []
    for var_name, var_label in variable_labels.items():
        # Get value labels for this variable
        stata_value_labels = get_spss_value_labels(value_labels_meta, var_name)
        alternatives = []
        
        for value in sorted(stata_value_labels.keys()):
            alternatives.append(stata_value_labels[value])
        
        # Normalize question text to remove F prefixes and other variable prefixes
        normalized_label = normalize_question_text(var_label) if var_label else ""
        
        all_questions.append({
            "variable": var_name,
            "question_text": normalized_label,  # Store normalized text (without F prefixes)
            "response_alternatives": alternatives,
            "year": year
        })
    
    # Identify batteries
    batteries, battery_variable_names = identify_batteries(all_questions)
    
    # Add year to batteries
    for battery in batteries:
        battery["year"] = year
    
    # Filter out invalid questions and exclude battery sub-questions
    valid_questions = []
    seen_variables = set()
    
    def is_battery_subquestion(var_name: str) -> bool:
        var_lower = var_name.lower()
        if var_lower in battery_variable_names:
            return True
        match = re.match(r'^([a-z]+\d+)([a-z]+)', var_lower)
        if match:
            base_name = match.group(1)
            for battery in batteries:
                if battery.get("variable", "").lower() == base_name:
                    return True
        return False
    
    for q in all_questions:
        var_name = q.get("variable", "")
        var_name_lower = var_name.lower()
        question_text = str(q.get("question_text") or "").strip()
        
        if var_name_lower in seen_variables:
            continue
        seen_variables.add(var_name_lower)
        
        if is_battery_subquestion(var_name):
            continue
        
        if question_text and question_text != "-" and len(question_text) > 3:
            if not ("," in question_text and any(word in question_text.lower() for word in ["universitet", "institut", "göteborgs"])):
                skip_patterns = ["löpnr", "formid", "indatum", "mode"]
                if not any(var_name_lower.startswith(pattern) for pattern in skip_patterns):
                    alternatives = q.get("response_alternatives", [])
                    if len(alternatives) >= 20:
                        alternatives = ["öppen fråga"]
                    
                    # Normalize question text to remove F prefixes
                    normalized_question_text = normalize_question_text(question_text)
                    
                    valid_q = {
                        "variable": var_name,
                        "question_text": normalized_question_text,  # Store normalized text
                        "response_alternatives": alternatives,
                        "year": year
                    }
                    valid_questions.append(valid_q)
    
    return valid_questions, batteries


def normalize_question_text(text: str) -> str:
    """Normalize question text for comparison (remove variable prefixes, extra spaces)."""
    if not text:
        return ""
    
    # Remove variable prefix patterns (e.g., "f7. ", "f72. ", "F77a.: ", "F99a.: ")
    # This handles both lowercase and uppercase, with or without colons
    text = re.sub(r'^[a-z]+\d+[a-z]*[.:]\s*', '', text, flags=re.IGNORECASE).strip()
    
    # Also remove any remaining F prefixes that might be in the middle (shouldn't happen, but just in case)
    # Remove patterns like "F77a.:" or "F99a.:" anywhere in the text
    text = re.sub(r'\b[a-z]+\d+[a-z]*[.:]\s*', '', text, flags=re.IGNORECASE).strip()
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()  # Keep original case for display, just normalize spacing


def normalize_response_alternative(alt: str) -> str:
    """Normalize response alternatives to handle minor variations.
    
    Examples:
    - "Någon gång under de senaste 12 månaderna" -> "någon gång under de senaste 12 mån"
    - "Någon gång de senaste 12 månaderna" -> "någon gång de senaste 12 mån"
    - "Någon gång under de senaste 12 mån" -> "någon gång under de senaste 12 mån"
    """
    if not isinstance(alt, str):
        return str(alt)
    
    text = alt.strip().lower()
    
    # Remove "Ej svar -" prefixes
    if text.startswith("ej svar -"):
        return ""  # Return empty to be filtered out
    
    # Normalize common variations
    # "månaderna" -> "mån"
    text = re.sub(r'\bmånaderna\b', 'mån', text)
    text = re.sub(r'\bmånader\b', 'mån', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def extract_core_question_text(text: str) -> str:
    """Extract the core question text by removing common prefixes and parent question stems.
    
    This helps group questions that are essentially the same but have different wording:
    - "Vilken är din åsikt? Minska inkomstskillnaderna" -> "Minska inkomstskillnaderna"
    - "Din åsikt om: Minska inkomstskillnaderna i samhället" -> "Minska inkomstskillnaderna i samhället"
    - "Åsikt om förslag i den politiska debatten - Minska inkomstskillnaderna i samhället" -> "Minska inkomstskillnaderna i samhället"
    """
    if not text:
        return ""
    
    # First normalize to remove variable prefixes
    text = normalize_question_text(text)
    
    # Common prefixes to remove (in order of specificity)
    prefixes = [
        r'^åsikt om förslag i den politiska debatten\s*[-–—]\s*',  # "Åsikt om förslag i den politiska debatten - "
        r'^åsikt om förslag i utrikesdebatten\s*[-–—]\s*',  # "Åsikt om förslag i utrikesdebatten - "
        r'^åsikt om förslag\s*[-–—]\s*',  # "Åsikt om förslag - "
        r'^vilken är din åsikt\?\s*',  # "Vilken är din åsikt? "
        r'^din åsikt:\s*',  # "Din åsikt: " (note: colon, not "om:")
        r'^din åsikt om:\s*',  # "Din åsikt om: "
        r'^åsikt om:\s*',  # "Åsikt om: "
        r'^hur ofta under de senaste 12\s*[-:]\s*',  # "Hur ofta under de senaste 12 - " or "12: "
        r'^hur ofta under de senaste 12\s+mån\??\s*[-:]\s*',  # "Hur ofta under de senaste 12 mån? - "
        r'^de senaste 12 månaderna:\s*',  # "De senaste 12 månaderna: "
        r'^om:\s*',  # "om: " or "Om: "
    ]
    
    # Also normalize common variations in the text itself
    # "månaderna" -> "mån" for consistency
    text = re.sub(r'\b12\s+månaderna\b', '12 mån', text, flags=re.IGNORECASE)
    text = re.sub(r'\b12\s+mån\b', '12 mån', text, flags=re.IGNORECASE)
    
    for prefix in prefixes:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE).strip()
    
    # Normalize common variations in question stems
    # "månaderna" -> "mån" for consistency in matching
    text = re.sub(r'\bmånaderna\b', 'mån', text, flags=re.IGNORECASE)
    text = re.sub(r'\bmånader\b', 'mån', text, flags=re.IGNORECASE)
    
    # Normalize whitespace again
    text = re.sub(r'\s+', ' ', text)
    
    # For questions about "Minska inkomstskillnaderna", normalize variations
    # "Minska inkomstskillnaderna" and "Minska inkomstskillnaderna i samhället" should match
    # Also handle "Minska inkomstskillnaderna i samhället" -> "Minska inkomstskillnaderna"
    if 'minska inkomstskillnaderna' in text.lower():
        # Remove "i samhället" suffix if present (for matching purposes)
        # This ensures "Minska inkomstskillnaderna" and "Minska inkomstskillnaderna i samhället" match
        text = re.sub(r'\s+i\s+samhället\s*$', '', text, flags=re.IGNORECASE).strip()
    
    # Normalize whitespace one more time after all processing
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def questions_are_similar(q1: Dict, q2: Dict, threshold: float = 0.8) -> bool:
    """Check if two questions are similar enough to be grouped together."""
    text1 = normalize_question_text(q1.get("question_text", ""))
    text2 = normalize_question_text(q2.get("question_text", ""))
    
    # Exact match
    if text1 == text2:
        return True
    
    # Check if one is a substring of the other (for slight variations)
    if len(text1) > 20 and len(text2) > 20:
        if text1 in text2 or text2 in text1:
            return True
    
    # Simple word overlap (for questions with minor wording differences)
    words1 = set(text1.split())
    words2 = set(text2.split())
    if len(words1) > 0 and len(words2) > 0:
        overlap = len(words1 & words2) / max(len(words1), len(words2))
        if overlap >= threshold:
            return True
    
    return False


def questions_are_identical(q1: Dict, q2: Dict) -> bool:
    """Check if two questions are completely identical (text and alternatives)."""
    text1 = normalize_question_text(q1.get("question_text", ""))
    text2 = normalize_question_text(q2.get("question_text", ""))
    
    if text1 != text2:
        return False
    
    alt1 = q1.get("response_alternatives", [])
    alt2 = q2.get("response_alternatives", [])
    
    if len(alt1) != len(alt2):
        return False
    
    return alt1 == alt2


def format_year_range(years: List[int]) -> str:
    """Format year range as string (e.g., [2023, 2024] -> "2023-2024", [2024] -> "2024")."""
    if len(years) == 1:
        return str(years[0])
    elif len(years) == 2:
        return f"{years[0]}-{years[1]}"
    else:
        return f"{years[0]}-{years[-1]}"


def group_questions_across_years(all_questions: List[Dict]) -> List[Dict]:
    """Group questions across years based on normalized question text and alternatives."""
    print("\n=== Grouping questions across years ===")
    print(f"Processing {len(all_questions)} questions...")
    
    # Use a dictionary for O(1) lookup instead of O(n²) nested loops
    groups_dict = {}
    
    for i, q in enumerate(all_questions):
        if i % 1000 == 0:
            print(f"  Processing question {i}/{len(all_questions)}...")
        
        # Use core question text + alternatives as unique identifier (ignore variable name, prefix, and year)
        # Extract core text to handle variations in wording
        q_text = q.get("question_text", "")
        # If we have a full_question_text, use that for core extraction (it has more context)
        if q.get("full_question_text"):
            q_text = q.get("full_question_text", "")
        
        core_text = extract_core_question_text(q_text)
        
        # If core text is empty, fall back to normalized question_text
        if not core_text:
            core_text = normalize_question_text(q.get("question_text", ""))
        
        # Normalize response alternatives aggressively to handle variations
        raw_alts = q.get("response_alternatives", [])
        # Normalize and filter alternatives
        normalized_alts_list = []
        seen_normalized = set()  # Remove duplicates
        
        for alt in raw_alts:
            normalized = normalize_response_alternative(alt)
            if normalized and normalized not in seen_normalized:
                normalized_alts_list.append(normalized)
                seen_normalized.add(normalized)
        
        # Sort to ensure consistent ordering
        normalized_alts_list.sort()
        normalized_alts = tuple(normalized_alts_list)
        
        # Match on core question text + normalized alternatives (scale)
        # Item wording is most important, but scale must match
        q_id = (core_text.lower(), normalized_alts)  # Don't include year - allows cross-year matching
        
        # Add to group (create new group if doesn't exist)
        if q_id not in groups_dict:
            groups_dict[q_id] = []
        groups_dict[q_id].append(q)
        
    # Now create grouped entries from the dictionary
    print(f"Creating grouped entries from {len(groups_dict)} unique question groups...")
    grouped = []
    
    for group_id, group in groups_dict.items():
        # Create grouped question entry
        years = sorted(set(g.get("year") for g in group))
        year_range = format_year_range(years)
        
        # Use the MOST RECENT year's question wording for display
        # Sort by year descending to get the latest
        group_sorted_by_year = sorted(group, key=lambda g: g.get("year", 0), reverse=True)
        latest_question = group_sorted_by_year[0]
        
        # Get the best question text for display (prefer full_question_text if available)
        full_question_text = latest_question.get("full_question_text", "")
        if not full_question_text:
            full_question_text = latest_question.get("question_text", "")
        
        # Normalize for display (remove F prefixes but keep the full wording)
        display_text = normalize_question_text(full_question_text)
        
        # Extract core text for the main question_text field (for search/grouping)
        core_text = extract_core_question_text(full_question_text)
        if not core_text:
            core_text = normalize_question_text(str(latest_question.get("question_text", "")))
        
        # Use latest question's parent question if available
        parent_question = latest_question.get("parent_question", "")
        if parent_question:
            # Normalize parent question too
            parent_question = normalize_question_text(parent_question)
        
        # Use latest question's response alternatives (normalized, without "Ej svar -")
        latest_alts = latest_question.get("response_alternatives", [])
        normalized_display_alts = []
        seen = set()
        for alt in latest_alts:
            if isinstance(alt, str):
                alt_clean = alt.strip()
                if not alt_clean.lower().startswith("ej svar -"):
                    # Remove duplicates
                    if alt_clean not in seen:
                        normalized_display_alts.append(alt_clean)
                        seen.add(alt_clean)
            else:
                normalized_display_alts.append(alt)
        
        if len(group) > 1:
            # Multiple years - all are identical (matched on core text + alternatives)
            grouped.append({
                "question_text": f"{year_range}: {core_text}",  # Core text for search/grouping
                "full_question_text": f"{year_range}: {display_text}",  # Full text for display
                "parent_question": parent_question,  # Parent question if from battery
                "response_alternatives": normalized_display_alts,
                "years": {str(g.get("year")): g.get("variable", "") for g in group},
                "type": "cross_year"
            })
        else:
            # Single year
            grouped.append({
                "question_text": f"{year_range}: {core_text}",  # Core text for search/grouping
                "full_question_text": f"{year_range}: {display_text}",  # Full text for display
                "parent_question": parent_question,  # Parent question if from battery
                "response_alternatives": normalized_display_alts,
                "years": {str(group[0].get("year")): group[0].get("variable", "")},
                "type": "single_year"
            })
    
    print(f"Grouped {len(all_questions)} questions into {len(grouped)} unique questions")
    return grouped


def batteries_are_identical(b1: Dict, b2: Dict) -> bool:
    """Check if two batteries are completely identical."""
    if b1.get("question_text", "") != b2.get("question_text", ""):
        return False
    
    sub1 = b1.get("sub_items", [])
    sub2 = b2.get("sub_items", [])
    if sub1 != sub2:
        return False
    
    alt1 = b1.get("response_alternatives", [])
    alt2 = b2.get("response_alternatives", [])
    if alt1 != alt2:
        return False
    
    return True


def group_batteries_across_years(all_batteries: List[Dict]) -> List[Dict]:
    """Group batteries across years based on normalized question text, sub_items, and alternatives."""
    print("\n=== Grouping batteries across years ===")
    print(f"Processing {len(all_batteries)} batteries...")
    
    # Use a dictionary for O(1) lookup instead of O(n²) nested loops
    groups_dict = {}
    
    for i, battery in enumerate(all_batteries):
        if i % 100 == 0:
            print(f"  Processing battery {i}/{len(all_batteries)}...")
        
        # Use normalized question text + sub_items + alternatives as unique identifier (ignore variable name and year)
        b_text = normalize_question_text(battery.get("question_text", ""))
        b_sub_items = tuple(battery.get("sub_items", []))
        b_alts = tuple(battery.get("response_alternatives", []))
        b_id = (b_text.lower(), b_sub_items, b_alts)  # Don't include year - allows cross-year matching
        
        # Add to group (create new group if doesn't exist)
        if b_id not in groups_dict:
            groups_dict[b_id] = []
        groups_dict[b_id].append(battery)
    
    # Now create grouped entries from the dictionary
    print(f"Creating grouped entries from {len(groups_dict)} unique battery groups...")
    grouped = []
    
    for group_id, group in groups_dict.items():
        # Create grouped battery entry
        years = sorted(set(b.get("year") for b in group))
        year_range = format_year_range(years)
        
        # Use normalized text (without variable prefix)
        normalized_text = normalize_question_text(group[0].get("question_text", ""))
        
        # Use the most complete sub_items and alternatives from the group
        main_sub_items = max([g.get("sub_items", []) for g in group], key=len)
        main_response_alternatives = max([g.get("response_alternatives", []) for g in group], key=len)
        
        if len(group) > 1:
            # All years identical - use compact format with year range
            grouped.append({
                "question_text": f"{year_range}: {normalized_text}",
                "sub_items": main_sub_items,
                "response_alternatives": main_response_alternatives,
                "years": {str(b.get("year")): b.get("variable", "") for b in group},
                "type": "battery"
            })
        else:
            # Single year
            grouped.append({
                "question_text": f"{year_range}: {normalized_text}",
                "sub_items": main_sub_items,
                "response_alternatives": main_response_alternatives,
                "years": {str(group[0].get("year")): group[0].get("variable", "")},
                "type": "battery"
            })
    
    print(f"Grouped {len(all_batteries)} batteries into {len(grouped)} unique batteries")
    return grouped


def main():
    base_path = Path(__file__).parent
    
    # Find all SPSS files
    spss_files = sorted(base_path.glob("Riks-SOM *.sav"))
    
    if not spss_files:
        print("No SPSS files found!")
        return
    
    print(f"Found {len(spss_files)} SPSS file(s)")
    
    # Extract year from filename
    all_questions = []
    all_batteries = []
    
    for spss_file in spss_files:
        # Extract year from filename (e.g., "Riks-SOM 2024.sav" -> 2024)
        year_match = re.search(r'(\d{4})', spss_file.name)
        if year_match:
            year = int(year_match.group(1))
            questions, batteries = extract_year_questions(spss_file, year)
            all_questions.extend(questions)
            all_batteries.extend(batteries)
        else:
            print(f"Warning: Could not extract year from {spss_file.name}")
    
    # Extract battery sub-items as individual questions
    battery_sub_items = []
    for battery in all_batteries:
        battery_text = normalize_question_text(battery.get("question_text", ""))
        parent_question = battery.get("question_text", "").strip()
        
        for sub_item in battery.get("sub_items", []):
            if not sub_item:
                continue
                
            # Remove "om: " prefix if present
            clean_sub_item = re.sub(r'^om:\s*', '', str(sub_item), flags=re.IGNORECASE).strip()
            
            # Combine parent question with sub-item for full question wording
            if parent_question:
                # If parent ends with ":" or similar, combine directly
                if parent_question.endswith((':', '-', '?')):
                    full_question = f"{parent_question} {clean_sub_item}"
                else:
                    full_question = f"{parent_question}: {clean_sub_item}"
            else:
                full_question = clean_sub_item
            
            # Normalize all text to remove F prefixes
            normalized_sub_item = normalize_question_text(clean_sub_item)
            normalized_full_question = normalize_question_text(full_question)
            normalized_parent = normalize_question_text(parent_question) if parent_question else ""
            
            # Create a synthetic variable name for tracking (not used for grouping)
            battery_sub_items.append({
                "question_text": normalized_sub_item,  # Store normalized item for grouping
                "full_question_text": normalized_full_question,  # Store normalized full wording for display
                "parent_question": normalized_parent,  # Store normalized parent for reference
                "response_alternatives": battery.get("response_alternatives", []),
                "year": battery.get("year"),
                "variable": f"{battery.get('variable', '')}_subitem",  # Synthetic variable for tracking
                "source": "battery_sub_item"
            })
    
    # Combine regular questions and battery sub-items
    all_questions_with_subitems = all_questions + battery_sub_items
    
    # Group questions across years (including battery sub-items)
    grouped_questions = group_questions_across_years(all_questions_with_subitems)
    grouped_batteries = group_batteries_across_years(all_batteries)
    
    # Sort
    grouped_questions.sort(key=lambda q: natural_sort_key(q.get("question_text", "")))
    grouped_batteries.sort(key=lambda b: natural_sort_key(b.get("question_text", "")))
    
    # Create output structure
    output = {
        "years": sorted(set(q.get("year") for q in all_questions)),
        "total_unique_questions": len(grouped_questions),
        "total_unique_batteries": len(grouped_batteries),
        "questions": grouped_questions,
        "batteries": grouped_batteries
    }
    
    # Save output
    output_path = base_path / "question_library_cross_year.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== Summary ===")
    print(f"Years: {output['years']}")
    print(f"Unique questions: {len(grouped_questions)}")
    print(f"Unique batteries: {len(grouped_batteries)}")
    print(f"\nSaved to: {output_path}")
    
    # Show some statistics
    cross_year_count = sum(1 for q in grouped_questions if len(q.get("years", [])) > 1)
    print(f"Questions appearing in multiple years: {cross_year_count}")


if __name__ == "__main__":
    main()

