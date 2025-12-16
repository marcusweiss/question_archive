# Quick Start - Search Interface

## The Problem
Browsers block loading JSON files when you open HTML files directly (file://). You need a local web server.

## Solution - 3 Easy Steps

1. **Start the server:**
   ```powershell
   cd question-library
   python -m http.server 8000
   ```

2. **Open in browser:**
   Go to: **http://localhost:8000/search.html**

3. **Search:**
   Type in the search box (e.g., "inkomstskillnader")

## Alternative: Use the PowerShell Script

Just double-click `start-server.ps1` and it will start the server automatically.

Then open: **http://localhost:8000/search.html**

## Troubleshooting

- **No results?** Check the browser console (F12) for errors
- **"Loading library..." forever?** The JSON file might not be loading - check console
- **Server won't start?** Make sure Python is installed and in your PATH

## Test if JSON loads

Open: **http://localhost:8000/test_search.html**

This will tell you if the JSON file is loading correctly.

