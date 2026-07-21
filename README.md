# High Performance Culture Diagnostic Tool

A working prototype of the HPC Diagnostic Tool — built on the PERILL framework and
positioned around four business-friendly pillars: **Purpose · Partnership · Processes · Excellence**.

## What's inside

```
hpc_tool/
├── app.py                      # Streamlit application (all pages)
├── requirements.txt            # Python dependencies
├── run.sh / run.bat            # Convenience launchers
├── README.md                   # This file
├── hpc/
│   ├── config_loader.py        # Loads & validates the master configuration Excel
│   ├── engine.py               # Scoring, classification, insights, recommendations
│   ├── charts.py               # Radar, correlation heatmap, ranking bar
│   └── report.py               # Executive PDF report generator
└── data/
    ├── HPC_Question_Bank_Template.xlsx    # Master configuration (round-trip file)
    ├── HPC_Response_Data_Template.xlsx    # Pre-loaded sample dataset (144 respondents, 8 depts)
    └── generated/                          # Auto-created for exported PDFs
```

## Quick start

### 1. Install
```bash
cd hpc_tool
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run
```bash
streamlit run app.py
```
Or double-click `run.sh` (Mac/Linux) / `run.bat` (Windows). The tool opens
at `http://localhost:8501`.

## Application pages

| Page | What it does |
|---|---|
| 🏠 **Home** | Company-wide snapshot: submissions, pillar scores, classification. |
| 📝 **Take Questionnaire** | Employee flow: select department → 40 questions (tabbed by pillar) → submit. |
| 📊 **Admin Dashboard** | Filter by department / date / minimum responses. Compare radar, heatmap, ranking, and insights. |
| 📥 **Upload Response Data** | Import an Excel/CSV response dataset. Replace or append. |
| ⚙️ **Upload Configuration** | Upload a new master config file. Schema validated. **Diff preview** shows exactly what changed. Change log entry required. |
| 📄 **Generate Executive Report** | Choose a focus department → download the professionally formatted PDF. |

## The master configuration file

`data/HPC_Question_Bank_Template.xlsx` is the single source of truth for the tool.
Edit it in Excel, save it, and re-upload via the *Upload Configuration* page.

**Sheets:**
- **Question Bank** — 40 questions, edit wording / add / retire
- **Departments** — add / retire / rename departments
- **Config** — scale bounds, band thresholds, imbalance rules, minimum sample size
- **Change Log** — audit trail (mandatory entry on upload)
- **_SCHEMA** — hidden system sheet; the tool rejects files with the wrong tag

The upload page shows a diff preview like:
```
Departments added (1)
 + D09 — Digital Transformation
Questions edited (2)
 ~ Q13: wording changed
 ~ Q18: wording changed
Settings changed (1)
 ~ min_responses_dept: 10 → 8
```

## Scoring & classification

- **Overall HPC Score** = mean of the four pillar means
- **Band classification:** Dysfunctional (<4.0) → Balanced (<6.0) → Performing (<8.0) → High Performance (≥8.0)
- **Balance factor:** if the gap between the max and min pillar > 2.0, classification is **automatically downgraded** one band and flagged as a strategic risk
- Sample size < `min_responses_dept` triggers a caution warning

All thresholds are editable in `Config`.

## Data privacy

- Anonymous mode is on by default (`anonymous_mode=TRUE` in Config)
- Reports below the minimum-response threshold display a warning
- The PDF generator uses aggregated statistics only

## Extending the tool

- **New pillar?** Requires code changes in `PILLARS` (config_loader.py) and updated question distribution
- **New chart?** Add to `hpc/charts.py`, then embed in `report.py` or `app.py`
- **Copilot / AI narrative?** Wire an LLM call in `hpc/report.py` before the "story.append" for insights — pass the `AnalysisResult` object as the prompt payload

## Troubleshooting

| Symptom | Fix |
|---|---|
| Fonts render as boxes | Ensure your Python has a working matplotlib backend |
| "Sheet '_SCHEMA' not found" on upload | The file was not built from the template — regenerate from the master template |
| Streamlit port busy | `streamlit run app.py --server.port 8502` |
| Charts don't refresh | Clear the browser cache or restart Streamlit |

## Version

- Tool version: 1.0.0
- Schema tag: HPC-CONFIG-v1
- Powered by the PERILL framework
