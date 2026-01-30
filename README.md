# Chumcred StratIQ — AI-Powered Business & Financial Diagnostics

Chumcred StratIQ is a board-ready business diagnostics platform that helps Analysts, CEOs, and Admins assess company performance using KPI scoring, benchmarking, SWOT, and AI-assisted advisory narratives.

## Key Features
- KPI-based business health scoring (BHI)
- Industry benchmarking (telecom, banking, FMCG + more)
- SWOT + recommendations
- Board-pack PDF export (branded)
- Financial Analyzer (3-year trend) + charts
- Hybrid AI: rules-driven facts + GPT narrative layer
- Role-based access: Admin, CEO, Analyst
- Subscription gating (monetization-ready)

---

## Local Setup

### 1) Create virtual environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
2) Install dependencies
pip install -r requirements.txt
3) Set environment variables
Windows PowerShell

setx OPENAI_API_KEY "sk-your-key"
Restart terminal after setting.

4) Run the app
streamlit run app.py
Deploy on Railway (GitHub → Railway)
1) Push to GitHub
Ensure secrets are not committed (OPENAI_API_KEY must never be in code).

2) Create Railway project from GitHub repo
Railway → New Project → Deploy from GitHub.

3) Set Start Command
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
4) Add Railway Variables
Railway → Service → Variables:

OPENAI_API_KEY = sk-...

Custom Domain (Porkbun)
Add domain in Railway to obtain the target hostname

In Porkbun DNS:

www CNAME → Railway hostname

root @ ALIAS (CNAME flattening) → Railway hostname

Security Notes
Never commit API keys to GitHub.

Use Railway Variables (production) and local environment variables (development).

.streamlit/secrets.toml is ignored by .gitignore.

License
Proprietary / Internal (update as needed)


