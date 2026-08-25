# Contracts

## Input

A material bundle is one directory containing:

- `lesson.json`: lesson identity and `source_slug`.
- `sources.json`: stable source IDs and hashes.
- `content_units.json`: grounded text units with stable IDs and content hashes.

All three files must use the same `source_slug`. Source locators must be stable and must not be absolute local paths. This skill does not convert raw PDF, presentation, audio, video, or transcript files.

## Output

A successful run writes KC candidates, embeddings, Ward candidates, parent topics, an embedding cache, and `run-manifest.json`. The manifest hashes inputs, prompts, and artifacts. Its release flags must keep `auto_publish` and `production_write` false.

`replay` verifies evidence, the exact KC partition, Ward lineage, and artifact hashes. Verification proves integrity and contract compliance; it does not replace pedagogical review.
