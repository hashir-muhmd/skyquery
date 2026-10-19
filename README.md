# SkyQuery

A local AI agent that answers plain-English questions about 20.9M US domestic flights (2023–2025) by writing and running SQL.

**Stack:** Ollama (qwen2.5-coder:7b) · DuckDB · Parquet · Python. Free and fully local.

## Try it
```
python -m src.agent "Which 5 airports with at least 10,000 flights had the worst on-time percentage?"
```

## Progress
- [x] Day 1: Ollama + qwen2.5-coder:7b running on GPU (RTX 5060, ~4.6 GB VRAM)
- [x] Day 1: 36 BTS CSVs converted to one Parquet file (20,928,599 rows, 357 MB, 16 s)
- [x] Day 1: First DuckDB queries matched against SkyMetrics. Found a null-handling bug: SkyMetrics counted cancelled/diverted flights as on-time (79.1% vs correct 77.5%)
- [x] Day 2: Verified answer key (11 questions). Baseline with raw schema only: **2/5 correct (40%)**. Failures were about column meaning and metric definitions, not SQL syntax
- [x] Week 1: Semantic layer (clean view + schema guide). Same 5 questions at temperature 0: **raw 3/5 → semantic 5/5**
- [x] Week 1: Agent loop. Guarded SQL tool (SELECT-only, single statement, no file access, 1,000-row limit, 30 s timeout), retry on error (max 2), grounded plain-English summary that states its assumptions
- [ ] Week 2: Grow the test set to 30-40 questions, measure accuracy, fix the most common failures

## Data
US BTS on-time performance data, 2023–2025, from the [SkyMetrics](https://github.com/hashir-muhmd/skymetrics) project. The data file is not stored in this repo. Run `scripts/convert_to_parquet.py` to build it.
