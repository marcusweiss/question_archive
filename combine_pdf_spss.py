"""Combine question text and items from PDF with response scales from SPSS file."""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    print("Installing pdfplumber...")
    import subprocess
    subprocess.check_call(["pip", "install", "pdfplumber"])
    import pdfplumber

def extract_from_pdf(pdf_path: Path, start_page: int = 12, end_page: int = 60) -> List[Dict]:
    """Extract questions and items directly from PDF, preserving variable names."""
    questions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(start_page - 1, min(end_page, len(pdf.pages))):
            page = pdf.pages[page_num]
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            current_question = None
            current_var = None
            current_items = []
            in_response_scale = False
            
            # Response scale indicators
            response_scale_words = {
                'dagligen', 'vecka', 'sällan', 'aldrig', 'mycket', 'ganska', 'varken', 
                'knappast', 'inte', 'helt', 'delvis', 'stort', 'litet', 'förtroende',
                'viktigt', 'bra', 'dåligt', 'positiv', 'negativ', 'nöjd', 'instämmer',
                'ja', 'nej', 'vet ej', 'ingen', 'uppfattning', 'kryss', 'ej kryss'
            }
            
            def is_response_scale_line(line: str) -> bool:
                line_lower = line.lower().strip()
                words = line_lower.split()
                if not words:
                    return False
                if len(words) <= 8:
                    scale_word_count = sum(1 for w in words if w in response_scale_words or w.isdigit())
                    if scale_word_count >= len(words) * 0.6:
                        return True
                if re.match(r'^[\d\s\-–]+$', line.strip()):
                    return True
                if re.search(r'\d+\s*[–-]\s*\d+', line):
                    return True
                return False
            
            for line in lines:
                line = line.strip()
                if not line:
                    if current_question and current_items:
                        questions.append({
                            'variable': current_var,
                            'question': current_question,
                            'items': current_items
                        })
                        current_question = None
                        current_var = None
                        current_items = []
                    in_response_scale = False
                    continue
                
                # Check for variable name pattern (e.g., "f8", "* f8", "f1a")
                # Look for patterns like "f8", "f1a", "* f8", "f8:", etc.
                var_match = re.match(r'^[*\s]*([a-z]+\d+[a-z]*)\s*[:.]?\s*(.+)$', line, re.IGNORECASE)
                if var_match:
                    var_name = var_match.group(1).lower()
                    question_text = var_match.group(2).strip()
                    # Remove form prefixes like "R1:"
                    question_text = re.sub(r'^R\d+\s*:\s*', '', question_text, flags=re.IGNORECASE)
                    # Only treat as question if it has '?' or is substantial text
                    if '?' in question_text or (len(question_text) > 15 and not question_text.isupper()):
                        if current_question and current_items:
                            questions.append({
                                'variable': current_var,
                                'question': current_question,
                                'items': current_items
                            })
                        current_var = var_name
                        current_question = question_text
                        current_items = []
                        in_response_scale = False
                    continue
                
                # Also check for questions without variable names (lines ending with '?')
                if '?' in line and len(line) > 10:
                    if current_question and current_items:
                        questions.append({
                            'variable': current_var,
                            'question': current_question,
                            'items': current_items
                        })
                    current_var = None
                    current_question = line
                    current_items = []
                    in_response_scale = False
                    continue
                
                # Check if response scale
                if is_response_scale_line(line):
                    in_response_scale = True
                    continue
                
                # If we have a question and this isn't a response scale, check if it's an item
                if current_question and not in_response_scale:
                    # Item: starts with capital letter, not too short
                    if line and line[0].isupper() and len(line) > 3:
                        # Clean item (remove any remaining prefixes)
                        item = re.sub(r'^[a-z]\s*[–-]\s*', '', line, flags=re.IGNORECASE)
                        item = re.sub(r'^:\s*[–-]\s*[a-z]\s*', '', item, flags=re.IGNORECASE)
                        item = re.sub(r'^[*\s]+', '', item)
                        if item and len(item) > 3:
                            current_items.append(item)
            
            # Add last question
            if current_question and current_items:
                questions.append({
                    'variable': current_var,
                    'question': current_question,
                    'items': current_items
                })
    
    return questions

def parse_pdf_text(pdf_text_path: Path) -> List[Dict]:
    """Parse the cleaned PDF text to extract questions and items (without response scales)."""
    with open(pdf_text_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    questions = []
    current_question = None
    current_items = []
    in_response_scale = False
    
    # Common response scale indicator words
    response_scale_words = {
        'dagligen', 'vecka', 'sällan', 'aldrig', 'mycket', 'ganska', 'varken', 
        'knappast', 'inte', 'helt', 'delvis', 'stort', 'litet', 'förtroende',
        'viktigt', 'bra', 'dåligt', 'positiv', 'negativ', 'nöjd', 'instämmer',
        'ja', 'nej', 'vet ej', 'ingen', 'uppfattning', 'kryss', 'ej kryss'
    }
    
    def is_response_scale_line(line: str) -> bool:
        """Check if a line is likely a response scale."""
        line_lower = line.lower().strip()
        # Check if line contains mostly response scale words
        words = line_lower.split()
        if not words:
            return False
        
        # If line is very short and contains numbers/scale indicators
        if len(words) <= 8:
            scale_word_count = sum(1 for w in words if w in response_scale_words or w.isdigit())
            if scale_word_count >= len(words) * 0.6:  # 60% are scale words
                return True
        
        # Check for patterns like "1 2 3 4 5" or "Ja Nej"
        if re.match(r'^[\d\s\-–]+$', line.strip()):
            return True
        
        # Check for common scale patterns
        if re.search(r'\d+\s*[–-]\s*\d+', line):  # "1-2" or "3–4"
            return True
        
        return False
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            # Empty line - end current question block
            if current_question:
                if current_items:
                    questions.append({
                        'question': current_question,
                        'items': current_items
                    })
                current_question = None
                current_items = []
                in_response_scale = False
            i += 1
            continue
        
        # Check if this is a response scale line
        if is_response_scale_line(line):
            in_response_scale = True
            i += 1
            continue
        
        # Check if this is a question (ends with '?' or is a long statement)
        if '?' in line or (len(line) > 30 and not in_response_scale):
            # If we have a previous question, save it
            if current_question and current_items:
                questions.append({
                    'question': current_question,
                    'items': current_items
                })
            
            # Start new question
            current_question = line
            current_items = []
            in_response_scale = False
            i += 1
            continue
        
        # If we have a question and this isn't a response scale, it's likely an item
        if current_question and not in_response_scale:
            # Check if line starts with capital letter (likely an item)
            if line and line[0].isupper():
                # Clean up the item (remove any remaining prefixes)
                item = line.strip()
                # Remove common prefixes that might remain
                item = re.sub(r'^[a-z]\s*[–-]\s*', '', item, flags=re.IGNORECASE)
                item = re.sub(r'^:\s*[–-]\s*[a-z]\s*', '', item, flags=re.IGNORECASE)
                if item and len(item) > 3:
                    current_items.append(item)
        
        i += 1
    
    # Add last question if exists
    if current_question and current_items:
        questions.append({
            'question': current_question,
            'items': current_items
        })
    
    return questions

def load_spss_data(spss_json_path: Path) -> Dict:
    """Load SPSS questions, response scales, and items."""
    with open(spss_json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def match_pdf_to_spss(pdf_questions: List[Dict], spss_data: Dict) -> List[Dict]:
    """Match PDF questions to SPSS data and combine them."""
    combined = []
    
    spss_scales = {var: data['response_scale'] for var, data in spss_data.items() if data['response_scale']}
    
    # Helper to get base variable name (e.g., "f1a" -> "f1")
    def get_base_name(var_name: str) -> str:
        if not var_name:
            return None
        match = re.match(r'^([a-z]+\d+)', var_name.lower())
        return match.group(1) if match else var_name.lower()
    
    for pdf_q_data in pdf_questions:
        pdf_var = pdf_q_data.get('variable')
        pdf_question = pdf_q_data['question']
        pdf_items = pdf_q_data['items']
        
        # Try to match by variable name
        matched_var = None
        response_scale = None
        
        if pdf_var:
            # Try exact match first
            if pdf_var in spss_scales:
                matched_var = pdf_var
                response_scale = spss_scales[pdf_var]
            else:
                # Try base name match (for battery questions)
                base_name = get_base_name(pdf_var)
                if base_name and base_name in spss_scales:
                    matched_var = base_name
                    response_scale = spss_scales[base_name]
        
        combined.append({
            'variable': matched_var or pdf_var,
            'question': pdf_question,
            'response_scale': response_scale,
            'items': pdf_items
        })
    
    return combined

if __name__ == "__main__":
    # Use 2024 PDF to get variable names
    pdf_path = Path(r"C:\Users\xwmarc\Desktop\AI-test\question-library\Kodböcker\SOMKodbok_2024.pdf")
    spss_json_path = Path(r"C:\Users\xwmarc\Desktop\AI-test\question-library\Kodböcker\cleaned\spss_questions.json")
    output_path = Path(r"C:\Users\xwmarc\Desktop\AI-test\question-library\Kodböcker\cleaned\combined_pdf_spss.json")
    
    print("Extracting questions from PDF (pages 12-60)...")
    pdf_questions = extract_from_pdf(pdf_path, start_page=12, end_page=60)
    print(f"Found {len(pdf_questions)} questions in PDF")
    
    print("\nLoading SPSS data...")
    spss_data = load_spss_data(spss_json_path)
    print(f"Loaded {len(spss_data)} variables from SPSS")
    
    print("\nMatching and combining...")
    combined = match_pdf_to_spss(pdf_questions, spss_data)
    
    # Count matches
    matched = sum(1 for c in combined if c['variable'] is not None)
    print(f"Matched {matched} out of {len(combined)} questions")
    
    # Save combined data
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved combined data to: {output_path}")
    
    # Print first few examples
    print("\nFirst 5 combined questions:")
    for i, q in enumerate(combined[:5]):
        print(f"\n{i+1}. Variable: {q['variable']}")
        print(f"   Question: {q['question'][:80]}...")
        print(f"   Response scale: {q['response_scale'][:60] if q['response_scale'] else 'None'}...")
        print(f"   Items: {len(q['items'])}")

