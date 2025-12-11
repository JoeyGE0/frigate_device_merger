# Quick Start - Copy & Paste Guide

## 📁 Repository Structure

Your GitHub repo should look like this:

```
frigate_device_merger/
├── .github/
│   ├── workflows/
│   │   └── validate.yml
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── custom_components/
│   └── frigate_device_merger/
│       ├── __init__.py
│       ├── config_flow.py
│       ├── manifest.json
│       └── README.md
├── .gitignore
├── CHANGELOG.md
├── hacs.json
├── LICENSE
└── README.md
```

## 🔧 Customization Checklist

Before pushing to GitHub, update these files:

### 1. `manifest.json`

- Replace `YOUR_USERNAME` with your GitHub username (2 places)
- Update `@YOUR_USERNAME` in codeowners

### 2. `README.md`

- Replace `YOUR_USERNAME` in HACS installation instructions

### 3. `hacs.json`

- No changes needed (unless you want to add more countries)

## 🚀 GitHub Setup Commands

```bash
# Navigate to the component directory
cd "/Users/josiahclark/Library/Mobile Documents/com~apple~CloudDocs/Coding and development/custom_components/frigate_device_merger"

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Frigate Device Merger v1.0.0"

# Create main branch
git branch -M main

# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/frigate_device_merger.git

# Push to GitHub
git push -u origin main
```

## 📝 After Pushing

1. **Create Release:**

   - Go to GitHub repo > Releases > Create new release
   - Tag: `v1.0.0`
   - Title: `v1.0.0 - Initial Release`
   - Copy content from CHANGELOG.md

2. **Test Installation:**

   - Add repo to HACS as custom repository
   - Install via HACS
   - Verify it works

3. **Optional - Submit to HACS Default:**
   - Fork https://github.com/hacs/default
   - Add your integration
   - Submit PR

## ✅ Files Ready to Push

All files are ready! Just:

1. Replace `YOUR_USERNAME` placeholders
2. Run git commands above
3. Create release on GitHub

Done! 🎉
