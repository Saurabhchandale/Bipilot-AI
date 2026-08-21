# Bipilot AI

Bipilot AI is an AI-powered dataset analysis and dashboard generation platform built with Flask, Pandas, Plotly, and optional OpenAI/Gemini integrations.

## Features

- Upload CSV and Excel datasets
- Clean duplicates, missing values, dates, and numeric columns
- Detect numeric, categorical, datetime, currency, and percentage columns
- Profile nulls, unique values, outliers, correlations, and distributions
- Detect dataset type such as Sales, Finance, HR, Marketing, Inventory, and Insurance
- Generate automatic Plotly dashboard visuals            
- Generate AI-style business insights with local fallback or optional API providers
- Modern 3D animated dashboard UI


## Setup

```powershell
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Optional AI Configuration

Create a `.env` file for OpenAI:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini
```

Or for Gemini:
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-1.5-flash
```

Without API keys, Bipilot AI uses the built-in local insight generator.

