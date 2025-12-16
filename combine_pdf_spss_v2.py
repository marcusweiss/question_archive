"""Combine question text and items from cleaned PDF text with response scales from SPSS file."""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

def parse_cleaned_text(text_path: Path) -> List[Dict]:
    """Parse cleaned PDF text to extract questions and items, removing response scales."""
    with open(text_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by double newlines (question blocks)
    blocks = content.split('\n\n')
    
    questions = []
    response_scale_words = {
        'dagligen', 'vecka', 'sällan', 'aldrig', 'mycket', 'ganska', 'varken', 
        'knappast', 'inte', 'helt', 'delvis', 'stort', 'litet', 'förtroende',
        'viktigt', 'bra', 'dåligt', 'positiv', 'negativ', 'nöjd', 'instämmer',
        'ja', 'nej', 'vet ej', 'ingen', 'uppfattning', 'kryss', 'ej kryss',
        'flera', 'gång', 'gånger', 'någon', 'mån', 'halvåret', 'månaden', 'veckan'
    }
    
    def is_response_scale(text: str) -> bool:
        """Check if text is a response scale."""
        text_lower = text.lower().strip()
        words = text_lower.split()
        if not words:
            return False
        # Check for number patterns
        if re.match(r'^[\d\s\-–]+$', text.strip()):
            return True
        # Check if mostly scale words
        if len(words) <= 10:
            scale_count = sum(1 for w in words if w in response_scale_words or w.isdigit() or re.match(r'^\d+[–-]\d+', w))
            if scale_count >= len(words) * 0.5:
                return True
        return False
    
    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines:
            continue
        
        # Find question (line with '?' or longest line)
        question = None
        question_idx = -1
        items = []
        
        for i, line in enumerate(lines):
            if '?' in line:
                question = line
                question_idx = i
                break
        
        # If no question mark, use first substantial line
        if not question and lines:
            for i, line in enumerate(lines):
                if len(line) > 30 and not is_response_scale(line):
                    question = line
                    question_idx = i
                    break
        
        if not question:
            continue
        
        # Extract items (lines after question that aren't response scales)
        # Also filter out question continuations
        question_lower = question.lower()
        question_words = set(re.findall(r'\b\w+\b', question_lower))
        
        for line in lines[question_idx + 1:]:
            line_clean = line.strip()
            if not line_clean:
                continue
            
            # Skip if it's clearly a response scale
            if is_response_scale(line_clean):
                continue
            
            # Skip if it's a question continuation (contains '?' or shares many words with question)
            line_lower = line_clean.lower()
            if '?' in line_clean:
                # Check if it shares significant words with the question (likely a continuation)
                line_words = set(re.findall(r'\b\w+\b', line_lower))
                common = question_words.intersection(line_words)
                stop_words = {'hur', 'du', 'är', 'och', 'i', 'av', 'för', 'som', 'på', 'med', 'till', 'om', 'det', 'en', 'den', 'från', 'eller', 'att', 'har', 'kan', 'ska', 'vilken', 'vilka', 'vad', 'när', 'var', 'de', 'följande', 'gjort', 'följande'}
                common = {w for w in common if w not in stop_words and len(w) > 2}
                if len(common) >= 2:  # Lower threshold to catch more continuations
                    continue  # Skip question continuation
            
            # Also skip lines that are clearly question continuations (start with "Och", "Hur", etc.)
            question_starters = ['och', 'hur', 'vilken', 'vilka', 'vad', 'när', 'var', 'varför']
            first_word = line_clean.split()[0].lower() if line_clean.split() else ''
            if first_word in question_starters and '?' in line_clean:
                continue
            
            # Check if line is mostly response scale words (even if not detected by is_response_scale)
            words = line_clean.split()
            if len(words) <= 10:  # Increased threshold
                scale_count = sum(1 for w in words if w.lower() in response_scale_words or w.isdigit() or re.match(r'^\d+[–-]\d+', w))
                if scale_count >= len(words) * 0.6:  # 60% are scale words
                    continue
            
            # Also check for patterns like "Någon gång Någon Någon Någon Flera" (all response scale words)
            if len(words) <= 10:
                scale_word_count = sum(1 for w in words if w.lower() in response_scale_words or w.isdigit() or re.match(r'^\d+[–-]\d+', w))
                if scale_word_count >= len(words) * 0.8:  # 80% are scale words
                    continue
                # Also check if all words are response scale words (exact match)
                if all(w.lower() in response_scale_words or w.isdigit() or re.match(r'^\d+[–-]\d+', w) for w in words):
                    continue
            
            # Now extract items - items are typically on separate lines or separated clearly
            if line_clean and line_clean[0].isupper() and len(line_clean) > 5:
                # Check if line contains response scale words mixed with items
                scale_word_positions = [i for i, w in enumerate(words) if w.lower() in response_scale_words or w.isdigit() or re.match(r'^\d+[–-]\d+', w)]
                
                if scale_word_positions:
                    # Response scale is at the beginning, items come after
                    # Find where items start (after last scale word or number)
                    last_scale_pos = max(scale_word_positions) if scale_word_positions else -1
                    item_words = words[last_scale_pos + 1:]
                    
                    if not item_words:
                        continue
                    
                    # Smart splitting: items are typically separated by capitalized words
                    # But preserve compound names like "Sveriges Radio", "P1 i Sveriges Radio"
                    # Strategy: look for patterns where a capitalized word starts a new item
                    # but don't split if it's part of a compound name
                    current_item = []
                    i = 0
                    while i < len(item_words):
                        word = item_words[i]
                        
                        # Check if this word starts a new item
                        # A new item typically starts with a capital letter
                        if word and word[0].isupper() and current_item:
                            prev_word = current_item[-1] if current_item else ''
                            
                            # Don't split if:
                            # 1. Previous word is lowercase (part of compound like "Sveriges Radio")
                            # 2. Previous word is a connector (i, och, eller, etc.)
                            # 3. Previous word is a number/letter (like "P1", "f1a")
                            # 4. Current word is a common second part of compound names
                            # 5. Previous word contains a slash (like "Radio/Lokalradion")
                            compound_second_parts = {'radio', 'television', 'tv', 'fm', 'am', 'sr', 'svt'}
                            
                            should_continue = False
                            if prev_word:
                                if prev_word[0].islower():
                                    should_continue = True
                                elif prev_word.lower() in ['i', 'och', 'eller', 'av', 'för', 'på', 'med', 'till', 'de', 'den', 'det']:
                                    should_continue = True
                                elif re.match(r'^[A-Z]?\d+[a-z]*$', prev_word):  # P1, f1a, etc.
                                    should_continue = True
                                elif word.lower() in compound_second_parts:
                                    should_continue = True
                                elif '/' in prev_word:  # Handle "Radio/Lokalradion"
                                    should_continue = True
                                # Also check if we're in the middle of a compound name pattern
                                elif i > 0 and i < len(item_words) - 1:
                                    # Check if next word might be part of compound
                                    next_word = item_words[i + 1] if i + 1 < len(item_words) else ''
                                    if next_word and (next_word.lower() in compound_second_parts or '/' in next_word):
                                        should_continue = True
                                # Special case: if current word is "Radio" and previous is "Sveriges", keep together
                                elif word.lower() == 'radio' and prev_word.lower() == 'sveriges':
                                    should_continue = True
                            
                            if should_continue:
                                current_item.append(word)
                            else:
                                # Start new item
                                item_text = ' '.join(current_item)
                                if item_text and len(item_text) > 3:
                                    items.append(item_text)
                                current_item = [word]
                        else:
                            current_item.append(word)
                        i += 1
                    
                    # Add last item
                    if current_item:
                        item_text = ' '.join(current_item)
                        if item_text and len(item_text) > 3:
                            items.append(item_text)
                    
                    # Post-process items for this line (merge/split as needed)
                    # This will be applied to all items at the end
                    pass
                else:
                    # No response scale words - might be a single item or multiple items
                    # Check for clear item separators
                    if '...' in line_clean:
                        parts = re.split(r'\s*\.\.\.\s*', line_clean)
                        for part in parts:
                            part = part.strip()
                            if part and part[0].isupper() and len(part) > 5:
                                items.append(part)
                    elif re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z]', line_clean):
                        # Multiple items - split on capital letters but preserve compound names
                        # This is tricky - for now, treat as single item if it looks like a compound name
                        # Compound names often have pattern: "Word1 Word2" where both are capitalized
                        if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$', line_clean):
                            # Likely a single compound name/item
                            items.append(line_clean)
                        else:
                            # Try to split - look for clear breaks
                            # Split on patterns where we have "Item1 Item2 Item3" with clear separation
                            parts = re.split(r'(?<=[a-z])\s+(?=[A-Z][a-z]+(?:\s+[a-z]+)*\s*$)', line_clean)
                            for part in parts:
                                part = part.strip()
                                if part and len(part) > 5:
                                    items.append(part)
                    else:
                        # No response scale - might be single item or multiple items on one line
                        # Check if line contains multiple items (separated by capitalized words)
                        if re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', line_clean):
                            # Multiple items - split carefully
                            words = line_clean.split()
                            current_item = []
                            for word in words:
                                if word and word[0].isupper() and current_item:
                                    prev_word = current_item[-1] if current_item else ''
                                    if prev_word and (prev_word[0].islower() or prev_word.lower() in ['i', 'och', 'eller', 'av', 'för', 'på', 'med', 'till']):
                                        current_item.append(word)
                                    else:
                                        item_text = ' '.join(current_item)
                                        if item_text and len(item_text) > 3:
                                            items.append(item_text)
                                        current_item = [word]
                                else:
                                    current_item.append(word)
                            if current_item:
                                item_text = ' '.join(current_item)
                                if item_text and len(item_text) > 3:
                                    items.append(item_text)
                        else:
                            # Single item - clean it up
                            item = re.sub(r'^[a-z]\s*[–-]\s*', '', line_clean, flags=re.IGNORECASE)
                            item = re.sub(r'^:\s*[–-]\s*[a-z]\s*', '', item, flags=re.IGNORECASE)
                            item = re.sub(r'^[*\s]+', '', item)
                            if item and len(item) > 3:
                                items.append(item)
        
        if question and items:
            # Post-process: merge items that were incorrectly split and split items that were incorrectly merged
            merged_items = []
            i = 0
            while i < len(items):
                current = items[i]
                # Check if this item is a pattern like "P1 i" or "P2 i" and next is "Sveriges Radio"
                if re.match(r'^[A-Z]\d+\s+i$', current) and i + 1 < len(items):
                    next_item = items[i + 1]
                    if next_item.startswith('Sveriges'):
                        merged_items.append(current + ' ' + next_item)
                        i += 2
                        continue
                # Check if item ends with "Sveriges" and next starts with "Radio"
                elif current.endswith('Sveriges') and i + 1 < len(items):
                    next_item = items[i + 1]
                    if next_item.startswith('Radio'):
                        merged_items.append(current + ' ' + next_item)
                        i += 2
                        continue
                # Check if item contains multiple items that should be split (like "P4 i Sveriges Radio/Lokalradion Rix FM")
                # Simple string-based approach
                if '/Lokalradion' in current and current.endswith(' Rix FM'):
                    # Remove " Rix FM" from the end and add it as separate item
                    first_part = current[:-len(' Rix FM')]  # Remove " Rix FM" from end
                    merged_items.append(first_part)
                    merged_items.append('Rix FM')
                    i += 1
                    continue
                elif '/Lokalradion' in current and ' Rix FM' in current:
                    # " Rix FM" is somewhere in the middle
                    parts = current.split(' Rix FM', 1)
                    if len(parts) == 2 and parts[1]:  # Make sure second part is not empty
                        merged_items.append(parts[0])
                        merged_items.append('Rix FM' + parts[1])
                        i += 1
                        continue
                # Also check for other station names after /Lokalradion
                elif '/Lokalradion' in current:
                    # Look for pattern: ".../Lokalradion" followed by space and station name
                    lokalradion_pos = current.find('/Lokalradion')
                    if lokalradion_pos > 0:
                        after = current[lokalradion_pos + len('/Lokalradion'):].strip()
                        # If there's text after /Lokalradion that looks like a station name (2 capitalized words)
                        if after and len(after.split()) == 2 and all(w[0].isupper() for w in after.split()):
                            merged_items.append(current[:lokalradion_pos + len('/Lokalradion')])
                            merged_items.append(after)
                            i += 1
                            continue
                merged_items.append(current)
                i += 1
            items = merged_items
            
            questions.append({
                'question': question,
                'items': items
            })
    
    return questions

def match_to_spss(pdf_questions: List[Dict], spss_data: Dict) -> List[Dict]:
    """Match PDF questions to SPSS variables and add response scales."""
    combined = []
    
    spss_questions = {var: data['question'] for var, data in spss_data.items()}
    spss_scales = {var: data['response_scale'] for var, data in spss_data.items() if data['response_scale']}
    
    def find_match(pdf_q: str) -> Optional[str]:
        """Find best matching SPSS variable."""
        pdf_q_lower = pdf_q.lower()
        pdf_words = set(re.findall(r'\b\w+\b', pdf_q_lower))
        
        best_match = None
        best_score = 0
        
        for var, spss_q in spss_questions.items():
            spss_q_lower = spss_q.lower()
            spss_words = set(re.findall(r'\b\w+\b', spss_q_lower))
            
            # Calculate word overlap
            common = pdf_words.intersection(spss_words)
            # Remove common stop words
            stop_words = {'hur', 'du', 'är', 'och', 'i', 'av', 'för', 'som', 'på', 'med', 'till', 'om', 'det', 'en', 'den', 'från', 'eller', 'att', 'har', 'kan', 'ska', 'vilken', 'vilka', 'vad', 'när', 'var'}
            common = {w for w in common if w not in stop_words and len(w) > 2}
            
            if len(common) >= 3:
                score = len(common)
                if score > best_score:
                    best_score = score
                    best_match = var
        
        return best_match
    
    for pdf_q_data in pdf_questions:
        pdf_q = pdf_q_data['question']
        pdf_items = pdf_q_data['items']
        
        matched_var = find_match(pdf_q)
        response_scale = spss_scales.get(matched_var) if matched_var else None
        
        combined.append({
            'variable': matched_var,
            'question': pdf_q,
            'response_scale': response_scale,
            'items': pdf_items
        })
    
    return combined

if __name__ == "__main__":
    text_path = Path(r"C:\Users\xwmarc\Desktop\AI-test\question-library\Kodböcker\cleaned\SOMKodbok_2024_cleaned.txt")
    spss_json_path = Path(r"C:\Users\xwmarc\Desktop\AI-test\question-library\Kodböcker\cleaned\spss_questions.json")
    output_path = Path(r"C:\Users\xwmarc\Desktop\AI-test\question-library\Kodböcker\cleaned\combined_pdf_spss.json")
    
    print("Parsing cleaned PDF text...")
    pdf_questions = parse_cleaned_text(text_path)
    print(f"Found {len(pdf_questions)} questions with items")
    
    print("\nLoading SPSS data...")
    with open(spss_json_path, 'r', encoding='utf-8') as f:
        spss_data = json.load(f)
    print(f"Loaded {len(spss_data)} variables from SPSS")
    
    print("\nMatching and combining...")
    combined = match_to_spss(pdf_questions, spss_data)
    
    matched = sum(1 for c in combined if c['variable'])
    print(f"Matched {matched} out of {len(combined)} questions to SPSS variables")
    
    with_scales = sum(1 for c in combined if c['response_scale'])
    print(f"Found response scales for {with_scales} questions")
    
    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved to: {output_path}")
    
    # Show examples
    print("\nFirst 5 examples:")
    for i, q in enumerate(combined[:5]):
        print(f"\n{i+1}. Variable: {q['variable']}")
        print(f"   Question: {q['question'][:70]}...")
        print(f"   Response scale: {q['response_scale'][:60] if q['response_scale'] else 'None'}...")
        print(f"   Items: {len(q['items'])}")

