---
name: vlearn-kc-extractor
description: Extract and validate draft knowledge components and parent topics from a prepared VLearn material bundle. Use when course content is already normalized into lesson, sources, and content-unit JSON files; do not use for raw PDF, presentation, audio, video, or quiz generation.
---

# VLearn KC Extractor

Create an auditable draft KC inventory and parent-topic partition from a prepared material bundle. Treat every result as review-required and never publish it automatically.

## Workflow

1. Read [references/contracts.md](references/contracts.md) to confirm the input and output boundary.
2. Run `python scripts/run_kc.py validate <bundle>` before any provider-backed action.
3. Before `run`, read [references/provider-safety.md](references/provider-safety.md), tell the user that OpenAI and Gemini receive course data, mention possible cost, and obtain explicit consent. Permission to prepare files or code is not consent to transmit course data.
4. After consent, run `python scripts/run_kc.py run <bundle> <new-output-dir> --acknowledge-external-processing`. Always use a new output directory.
5. The runner replays the result. If verification fails, stop and report the failure without presenting the artifacts as usable.
6. Read [references/review-checklist.md](references/review-checklist.md) and review the verified draft with the user. Do not mark it approved or write it to production without a separate explicit request.

Use `python scripts/run_kc.py replay <bundle> <recorded-run>` for offline verification. Use `doctor` when the Python package or environment may be unavailable.

Raw document conversion and quiz generation are outside this skill. Ask for a normalized bundle or route those tasks to a dedicated workflow.
