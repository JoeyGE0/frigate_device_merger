# Repository Setup Guide

## File Structure

```
frigate_device_merger/
├── .github/
│   ├── workflows/
│   │   └── validate.yml          # GitHub Actions validation
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md         # Bug report template
│       └── feature_request.md    # Feature request template
├── custom_components/
│   └── frigate_device_merger/
│       ├── __init__.py           # Main component code
│       ├── config_flow.py        # Config flow
│       ├── manifest.json         # Component manifest
│       └── README.md            # Documentation
├── .gitignore                    # Git ignore rules
├── CHANGELOG.md                 # Version history
├── hacs.json                    # HACS configuration
├── LICENSE                      # MIT License
└── README.md                    # Main README
```

## Before Publishing

### 1. Replace Placeholders

Search and replace `YOUR_USERNAME` with your actual GitHub username in:

- `manifest.json` (documentation and issue_tracker URLs)
- `README.md` (HACS installation instructions)
- `hacs.json` (if needed)

### 2. Update Codeowners

In `manifest.json`, replace `@YOUR_USERNAME` with your GitHub username (e.g., `@josiahclark`)

### 3. Create GitHub Repository

1. Go to GitHub and create a new repository
2. Name it: `frigate_device_merger`
3. Make it public (required for HACS)
4. Don't initialize with README (we already have one)

### 4. Push to GitHub

```bash
cd custom_components/frigate_device_merger
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/frigate_device_merger.git
git push -u origin main
```

### 5. Create Release

1. Go to your repository on GitHub
2. Click "Releases" > "Create a new release"
3. Tag: `v1.0.0`
4. Title: `v1.0.0 - Initial Release`
5. Description: Copy from CHANGELOG.md
6. Publish release

### 6. Submit to HACS (Optional)

If you want to submit to the default HACS repository:

1. Fork https://github.com/hacs/default
2. Add your integration to `integration.json`
3. Submit a pull request

## Testing

Before publishing, test locally:

1. Copy to `config/custom_components/frigate_device_merger/`
2. Restart Home Assistant
3. Add integration via UI
4. Check logs for any errors
5. Verify devices merge correctly
