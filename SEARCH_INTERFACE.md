# Question Library Search Interface

A simple, fast search interface for the SOM Question Library.

## How to Use

**Important:** You need to use a local web server (browsers block loading JSON files when opening HTML directly).

### Option 1: Use the PowerShell script (Easiest)
1. Right-click `start-server.ps1` and select "Run with PowerShell"
2. Open your browser and go to: **http://localhost:8000/search.html**

### Option 2: Manual server start
1. Open PowerShell in the `question-library` folder
2. Run: `python -m http.server 8000`
3. Open your browser and go to: **http://localhost:8000/search.html**

2. **Search for questions:**
   - Type in the search box (e.g., "inkomstskillnader", "förtroende", "politik")
   - Results update in real-time as you type
   - Search is case-insensitive and matches anywhere in the question text

3. **View results:**
   - Each result shows:
     - Question text with year range (e.g., "2023-2024: ..." or "2024: ...")
     - Which years the question appears in
     - Response alternatives (or "öppen fråga" for open questions)
     - For batteries: sub-items are also shown

## Features

- **Fast search**: Searches through all questions and batteries instantly
- **Year tracking**: Shows which years each question appears in
- **Response alternatives**: Displays available response options
- **Battery support**: Shows sub-items for battery questions
- **Clean interface**: Easy to read and navigate

## Example Searches

- `inkomstskillnader` - Find questions about income inequality
- `förtroende` - Find questions about trust
- `politik` - Find questions about politics
- `medier` - Find questions about media
- `EU` - Find questions about the EU

## Technical Details

- Pure HTML/JavaScript - no server needed
- Loads `question_library_cross_year.json` from the same folder
- Works offline once the JSON is loaded
- Responsive design - works on desktop and mobile

## Adding More Years

When you add more years and regenerate `question_library_cross_year.json`, just refresh the page - the search interface will automatically include the new data.

