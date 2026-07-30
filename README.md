# Document Intelligence Pipeline (Multi-Agent, CV + NLP)

A multi-agent pipeline that reads scanned receipt images and turns them
into structured, validated data with a dashboard on top. 

## Architecture

```
 ┌─────────────┐    ┌────────────────────┐    ┌──────────────────┐
 │  OCR Agent  │───▶│ Extraction Agent   │───▶│ Validation Agent │
 │  (EasyOCR,  │    │ (Claude API, with  │    │ (business rules: │
 │   CV)       │    │  rule-based        │    │  totals, dates,  │
 │             │    │  fallback)         │    │  vendor sanity)  │
 └─────────────┘    └────────────────────┘    └──────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │  SQLite (results)   │
                     └─────────────────────┘
                          │           │
                          ▼           ▼
                 ┌────────────┐  ┌───────────────┐
                 │ Streamlit  │  │ Power BI      │
                 │ dashboard  │  │ (Windows only)│
                 └────────────┘  └───────────────┘
```


## Dataset

[CORD (Consolidated Receipt Dataset)](https://huggingface.co/datasets/naver-clova-ix/cord-v2) 

```bash
pip install datasets
python -c "
from datasets import load_dataset
ds = load_dataset('naver-clova-ix/cord-v2', split='test[:50]')
import os
os.makedirs('data/images', exist_ok=True)
for i, item in enumerate(ds):
    item['image'].save(f'data/images/receipt_{i:03d}.png')
"
```

(Downloads 50 test images to `data/images/` — plenty for a portfolio demo.)

## Setup

```bash
pip install -r requirements.txt
```

Works identically on Windows and Mac — no OS-specific code, no API key
required to run the full pipeline. By default, the Extraction Agent uses
regex/rule-based extraction (free, no external calls).

### Optional: enabling the LLM extraction agent

If you want to compare LLM-based extraction against the rule-based
fallback, get a key from [console.anthropic.com](https://console.anthropic.com):

```bash
# Mac/Linux
export ANTHROPIC_API_KEY=your_key_here

# Windows PowerShell
$env:ANTHROPIC_API_KEY="your_key_here"
```

This is entirely optional. `ExtractionAgent` checks for the environment
variable at startup; if it's not set, it uses the rule-based path
automatically, and the pipeline runs end-to-end either way. 

## Run

```bash
python orchestrator.py --images_dir data/images --db pipeline_results.db
streamlit run dashboard/app.py
```

## Results


| Metric | Value |
|---|---|
| Documents processed | 50 |
| Valid rate  | 0% |
| Avg OCR confidence | 0.62 |


