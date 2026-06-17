# Vibiz.ai

AI-powered marketing generator for any website. Paste a URL → get Google Ads, Facebook/Instagram ads, SEO recommendations, and content ideas in seconds.

## Setup

```bash
cd vibiz-ai
pip install -r requirements.txt

# Add your Anthropic API key
cp .env.example .env
# Edit .env and paste your ANTHROPIC_API_KEY

python app.py
```

Open http://localhost:5000

## Deploy to Replit

1. Upload this folder to a new Replit project (Python)
2. Add `ANTHROPIC_API_KEY` in Replit Secrets
3. Set the run command to: `python app.py`
4. Click Run
