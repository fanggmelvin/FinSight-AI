[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://finsight-by-melvin.streamlit.app/)

# FinSight AI

**Financial Analyst Copilot | Python Â· Streamlit Â· OpenAI**

FinSight AI turns structured financial data into interactive dashboards, evidence-linked performance investigations and management recommendations. Built as a finance and AI engineering portfolio project, it separates financial calculations from language-model decisions to make reporting more reproducible and reduce unsupported numerical claims.

![Release](https://img.shields.io/badge/release-v0.16.0-blue) ![Tests](https://img.shields.io/badge/tests-195%20passed-brightgreen) ![Python](https://img.shields.io/badge/Python-3.14-blue)

## Project at a glance

| Metric | Result |
|---|---:|
| Automated tests passed in local release validation | 195 |
| Live regression workflows exercised successfully | 9 |
| Application pages / bundled financial skills | 7 / 7 |
| Sample dataset records | 700 |
| 2014 sample revenue analyzed | $92.31M |
| Observed token reduction across six workflows vs. v0.14.4 | 74.1% |
| Observed revenue-investigation token reduction vs. v0.8.0 | 96.2% |

## Business problem

Analysts must reconcile financial data, explain changes in performance, prioritize risks and communicate findings to management. Unrestricted language-model reporting can introduce unsupported numbers or causal explanations. FinSight uses local financial computation and constrained AI action selection instead of asking a model to calculate or invent financial results.

## Application walkthrough

| Page | Purpose |
|---|---|
| Overview | Financial KPIs and performance overview |
| Data Upload | Excel/CSV ingestion, worksheet selection and validation |
| Financial Analysis | Revenue, gross profit, margin and dimensional breakdowns |
| Performance Drivers | Period comparisons and contribution analysis |
| Anomaly Detection | Rule-based financial exception flags |
| AI Copilot | Natural-language routing, evidence and contextual action selection |
| Financial Reports | Executive reporting and management priorities |

## Application screenshots

The screenshots below show the full sample dataset (September 2013â€“December 2014, 700 records, approximately $118.73M revenue). The financial case study below uses only 2014.

### Overview dashboard

Full-dataset KPIs and platform capabilities.

![Overview dashboard](screenshots/overview.png)

### Financial analysis

Interactive filters and financial KPIs across 700 sample records.

![Financial analysis](screenshots/financial-analysis.png)

### Monthly performance

Revenue, gross profit, month-over-month growth and gross margin charts.

![Monthly performance](screenshots/monthly-performance.png)

### Monthly financial summary

Detailed monthly metrics and expandable calculation evidence.

![Monthly financial summary](screenshots/monthly-summary.png)

### Performance drivers

Product revenue and gross profit rankings.

![Performance drivers](screenshots/performance-drivers.png)

### AI Copilot interface

Automatic routing, manual analysis modes and natural-language question entry.

![AI Copilot interface](screenshots/ai-copilot.png)

### Executive reporting interface

Financial filters, report audience selection and report generation controls.

![Executive reporting interface](screenshots/executive-report.png)

## Architecture

```mermaid
flowchart TD
    A[Excel or CSV] --> B[Validation and filters]
    Q[Natural-language question] --> R[Question routing and scope guards]
    B --> C[Local financial calculation engine]
    R --> C
    C --> D[Evidence registry]
    R --> S[Bundled financial skill selection]
    D --> T[Deterministic findings and themes]
    S --> T
    T --> M[OpenAI: choose approved action IDs]
    S --> M
    M --> V[Validate selections or use local defaults]
    T --> V
    D --> O[Evidence-linked report]
    V --> O
    O --> I[Check evidence ID existence]
```

Financial values, findings, priorities and business implications are generated locally. The model receives calculated themes and selects between approved investigation plans using a strict JSON schema. Invalid or unavailable AI responses fall back to local recommendations. The application checks evidence ID existence; it does not independently audit the financial data or verify factual entailment.

### Modular financial skills

| Skill | Focus |
|---|---|
| `financial-performance` | Overall financial performance |
| `variance-analysis` | Period changes and arithmetic contributions |
| `profitability-analysis` | Gross margin and product profitability |
| `concentration-risk` | Revenue exposure and concentration |
| `anomaly-detection` | Financial exceptions and review priorities |
| `executive-reporting` | Management-oriented reporting |
| `evidence-verification` | Mandatory evidence guidance |

Skills are bundled Markdown instructions selected by deterministic routing. They are not separately trained models.

## Financial case study

Using the Microsoft Financial Sample dataset, the application analyzed 2014 performance and investigated the October-to-November revenue decline.

| Annual metric | 2014 |
|---|---:|
| Revenue | $92,311,094.75 |
| Cost of goods sold | $79,295,857.00 |
| Gross profit | $13,015,237.75 |
| Gross margin | 14.10% |

| Investigation metric | Result |
|---|---:|
| October revenue | $12,375,819.92 |
| November revenue | $5,384,214.20 |
| Revenue change | âˆ’$6,991,605.72 (âˆ’56.49%) |
| Gross profit change | âˆ’$1,177,385.72 |
| Gross margin change | âˆ’3.17 percentage points |

The investigation identifies Carretera as the largest negative product revenue contributor, Germany as the largest negative geographic contributor, and Government as the largest negative segment contributor. VTT / Germany / Government is a leading negative intersection. These overlapping dimensions must not be added together.

The annual review also identifies Enterprise's negative gross margin (âˆ’2.70%) and Government plus Small Business concentration (79.63% of revenue). These findings support targeted review of pricing, costs, sales mix and demand sensitivity, not conclusions about underlying causation.

## AI efficiency benchmarks

Reported tokens from observed development runs using the same six analytical workflow categories:

| Workflow | v0.14.4 | v0.15.0 | v0.16.0 |
|---|---:|---:|---:|
| Product profitability | 1,637 | 590 | 466 |
| Segment concentration | 1,379 | 582 | 566 |
| Financial summary | 7,200 | 1,786 | 1,269 |
| Anomaly detection | 1,067 | 1,098 | 842 |
| Revenue investigation | 6,041 | 1,230 | 1,028 |
| Executive reporting | 4,003 | 1,869 | 1,352 |
| **Total** | **21,327** | **7,155** | **5,523** |

The observed total fell 74.1% relative to v0.14.4. A separate historical revenue-investigation benchmark fell from 27,006 tokens in v0.8.0 to 1,028 in v0.16.0 (96.2%). Architectures and verification approaches changed across versions; these are development observations, not controlled experiments or guaranteed cost savings. The latest reported counts cover the final model request only.

## Run locally

Development environment: Windows, Python 3.14. Other environments have not been validated for this release.

```powershell
git clone https://github.com/fanggmelvin/FinSight-AI.git
cd FinSight-AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Local analysis works without a key. To enable OpenAI, set `OPENAI_API_KEY` and `FINSIGHT_LIVE_AI=1` in `.env`. Set `FINSIGHT_AI_UPLOADS=1` to make interpretation available for uploads. Select the consent control under **AI Copilot → Settings** before sharing an uploaded workbook’s question or excerpts.

```powershell
python -m streamlit run app.py
```

Open the local URL printed by Streamlit. FinSight comes with the sample dataset. Upload an Excel workbook or CSV from **Change dataset** to open its dashboard or explore it in Copilot.

Try these questions in **AI Copilot**:

- Summarize financial performance in 2014.
- Rank all products by gross margin in 2014 and identify profitability risks.
- Why did revenue decline in November 2014? Analyze product, country, and segment contributions.
- Identify unusual financial results and anomalies in 2014.
- Prepare an executive financial performance report for the CFO for 2014.

## Testing and reliability

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pip check
```

Release validation on the developer's Windows environment: **195 passed in 1.58 seconds**, no broken requirements. Nine live regression checks covered six analytical workflows and three guards: unsupported metrics, unavailable years and ambiguous comparison periods. All three guards prevented an AI request in the tested cases.

## Repository structure

| Module | Responsibility |
|---|---|
| `app.py` | Streamlit interface |
| `finsight/data_validator.py` | Input normalization and validation |
| `finsight/finance_engine.py` | Financial calculations |
| `finsight/evidence_engine.py` | Structured financial evidence |
| `finsight/investigation_engine.py`, `finsight/investigation_bridge.py` | Contribution investigations |
| `finsight/question_router.py`, `finsight/reliability.py` | Routing and safeguards |
| `finsight/skill_engine.py`, `skills/`, `finsight/skill_workflow.py` | Bundled skill selection and workflow utilities |
| `finsight/commentary_engine.py`, `finsight/narrative_engine.py` | Calculated findings, themes and approved action plans |
| `finsight/ai_engine.py` | OpenAI integration and selection validation |
| `finsight/deterministic_report.py` | Local financial report rendering |
| `finsight/verification_engine.py`, `finsight/claim_mapping.py` | Verification utilities |
| `tests/test_*.py` | Test suite and connection diagnostic |

**Stack:** Python, Streamlit, Pandas, NumPy, Plotly, Altair, OpenAI API, OpenPyXL, Pytest and Git.

## Limitations

- Gross profit is not net income. Unsupported metrics require additional data.
- Contribution analysis is arithmetic attribution, not proof of causation.
- Anomaly and priority thresholds are illustrative review rules, not audited materiality standards.
- Evidence ID checks do not prove factual entailment or source-data accuracy.
- AI selects predefined investigation plans rather than performing unrestricted autonomous financial reasoning.
- Results depend on the uploaded data, and passing tests do not guarantee universal correctness.
- This is an educational portfolio project, not production financial software or investment advice.

## Author

**Melvin Fang** â€” University of California San Diego, B.S. Business Economics, Minor in Finance.

Built to demonstrate financial analysis, business intelligence, applied AI integration and software reliability.

**Release:** v0.16.0


## Deploy on Streamlit Community Cloud

Use `app.py` as the entry point and Python 3.14, the version used by local validation and CI. The app runs in local-analysis mode by default.

For a live demo, add the following root-level settings in the hosted app’s Secrets tab. Use a deployment project key. Keep serving uploaded files locally in a public app.

```toml
FINSIGHT_LIVE_AI = "1"
FINSIGHT_AI_UPLOADS = "0"
OPENAI_API_KEY = "replace-with-your-deployment-project-key"
OPENAI_MODEL = "gpt-4.1-mini"
```

For a private deployment where authorized users may share workbook excerpts, restrict the app’s audience and set `FINSIGHT_AI_UPLOADS = "1"`. Each user still opts in for their upload. The app keeps its calculated answer available when OpenAI is unavailable. Review [Streamlit secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) and the [shared request limits](API_GUARD.md) before enabling live requests.

Before publishing, run `python -m pip check` and `python -m pytest -q`. The repository CI also runs the Chromium upload and Copilot smoke test.


## v0.17.0 - Modern Fintech Interface

- Modern fintech SaaS-inspired design.
- Professional sidebar navigation.
- Rounded financial KPI cards.
- Interactive executive overview dashboard.
- Consistent financial chart formatting.
- Collapsible analysis filters.
- Streamlined AI Copilot with suggested questions.
- Improved typography, spacing, and readability.
- Existing financial engine and AI workflows preserved.
- All 198 automated regression tests passed.

