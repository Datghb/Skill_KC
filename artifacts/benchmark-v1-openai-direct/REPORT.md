# V1 OpenAI Direct Benchmark

Run date: 2026-08-25  
Generation: `gpt-5.6-luna`, reasoning effort `high`, OpenAI Chat Completions  
Embedding: `gemini-embedding-2`  
Input mode: `slide_only`

## Successful verified runs

| Dataset | Content units | Knowledge items | Trackable KCs | Parent topics | Leaf moves | Repair retries | Wall time | Estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Day 06 | 14 | 14 | 10 | 6 | 1 | 1 | 205.46 s | $0.031586 |
| Day 10 | 45 | 28 | 28 | 11 | 4 | 0 | 250.44 s | $0.042282 |
| Day 14 | 78 | 40 | 40 | 12 | 4 | 1 | 351.94 s | $0.067621 |
| **Total** | **137** | **82** | **78** | **29** | **9** | **2** | **807.84 s** | **$0.141489** |

Derived metrics:

- 0.569 trackable KC per content unit.
- $0.001033 estimated provider cost per content unit.
- $0.001814 estimated provider cost per trackable KC.
- 222,619 OpenAI tokens and 30,458 Gemini embedding input tokens.
- All three recorded runs passed replay verification.

OpenAI cost uses the published GPT-5.6 Luna token rates at run time: $0.20 per million uncached input tokens, $0.02 per million cached input tokens, and $1.20 per million output tokens. Gemini cost uses the estimate emitted by the pipeline manifest.

## Repair observations

- Day 06 extraction required one repair because `primary_capability_vi` was missing.
- Day 14 extraction required one repair because an evidence ID did not exist in the input bundle.
- Day 10 required no repair.
- Parent refinement passed on the first attempt for all three successful runs.

## Interpretation limits

The cost total covers successful recorded runs only. Two earlier Day 06 attempts reached paid provider stages but failed before a run manifest was written, so actual account charges for the entire test session are higher and must be read from provider billing dashboards.

Replay verification proves artifact integrity, evidence references, partition coverage, and Ward lineage. It does not measure pedagogical correctness. These live outputs have not received independent human judge labels, so no `high`, `review`, or `low` quality rate is reported.

OpenAI model source: https://developers.openai.com/api/docs/models/gpt-5.6-luna
