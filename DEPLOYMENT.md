# Deployment Guide

## GitHub Pages Setup

The tool is configured to deploy automatically via GitHub Actions. To make it live:

### Step 1: Enable GitHub Pages
1. Go to your repository: https://github.com/marcusweiss/question_archive
2. Click **Settings** → **Pages** (in the left sidebar)
3. Under **Source**, select **"GitHub Actions"** (NOT "Deploy from a branch")
4. Click **Save**

### Step 2: Wait for Deployment
- The GitHub Actions workflow will automatically run after you enable Pages
- You can check the deployment status at: https://github.com/marcusweiss/question_archive/actions
- Once complete, your site will be live at: **https://marcusweiss.github.io/question_archive/**

### Step 3: Access Your Live Site
- Main page: https://marcusweiss.github.io/question_archive/
- Search interface: https://marcusweiss.github.io/question_archive/search.html

## Automatic Updates
- Every time you push to the `main` branch, the site will automatically redeploy
- Updates typically take 1-2 minutes to go live

## Troubleshooting

**Site not loading?**
- Check the Actions tab to see if deployment succeeded
- Make sure GitHub Pages is set to "GitHub Actions" source
- Wait a few minutes for DNS propagation

**JSON file not loading?**
- Ensure `question_library_cross_year.json` is in the repository root
- Check browser console for CORS errors
- GitHub Pages should serve JSON files correctly

**Need to update the library?**
1. Run `python build_library_from_merged_csv.py` locally
2. Commit and push the updated `question_library_cross_year.json`
3. The site will automatically redeploy

