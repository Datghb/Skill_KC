---
name: vlearn-kc-extractor
description: Extract and validate draft knowledge components and parent topics from a prepared VLearn material bundle. Use when course content is already normalized into lesson, sources, and content-unit JSON files; do not use for raw PDF, presentation, audio, video, or quiz generation.
---

# VLearn KC Extractor

Create an auditable draft KC inventory and parent-topic partition from a prepared material bundle. Treat every result as review-required and never publish it automatically.

## Workflow

1. Read [references/contracts.md](references/contracts.md) to confirm the input and output boundary.
2. Resolve `scripts/run_kc.py` relative to this `SKILL.md`, not relative to the user's working directory. Run `python <skill-root>/scripts/run_kc.py doctor <bundle>` when environment readiness is unknown, then run `python <skill-root>/scripts/run_kc.py validate <bundle>` before any provider-backed action.
3. Before `run`, read [references/provider-safety.md](references/provider-safety.md), tell the user that OpenAI and Gemini receive course data, mention possible cost, and obtain explicit consent. Permission to prepare files or code is not consent to transmit course data.
4. After consent, run `python <skill-root>/scripts/run_kc.py run <bundle> <new-output-dir> --acknowledge-external-processing`. Always use a new or empty output directory.
5. The runner replays the result and fails closed unless verification returns exactly `true`. On any failure, keep the output quarantined and do not present it as usable.
6. Read [references/review-checklist.md](references/review-checklist.md) and review the verified draft with the user. Do not mark it approved or write it to production without a separate explicit request.

Use `python <skill-root>/scripts/run_kc.py replay <bundle> <recorded-run>` for offline verification and require `verified: true`. A successful provider-backed `run` summary must also report `status: draft`, `review_required: true`, and `publish_allowed: false`.

Raw document conversion and quiz generation are outside this skill. Ask for a normalized bundle or route those tasks to a dedicated workflow.
