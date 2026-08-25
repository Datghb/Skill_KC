# VLearn Standalone KC Pipeline

This handoff contains a clean Knowledge Component pipeline. It does not import
the host repository, dated experiments or hidden files from a developer machine.

## Public boundary

The package starts from an AI-ready material bundle:

```text
material-bundle/
├── lesson.json
├── sources.json
└── content_units.json
```

Raw PDF, video and transcript conversion belongs to the upstream material
pipeline. KC extraction consumes stable content units only.

## Pipeline

```text
material bundle validation
→ Luna KC extraction
→ Gemini embedding with disk cache
→ Ward candidate partitions
→ Luna selects K, splits and moves individual leaves
→ whole-parent merge is rejected
→ exact partition and lineage gates
→ immutable run manifest
```

Nothing is automatically published to runtime.

## Quick verification without API keys

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'

.venv/bin/vlearn-kc validate examples/day01/material-bundle
.venv/bin/vlearn-kc replay \
  examples/day01/material-bundle \
  examples/day01/recorded-run
```

Expected Day 1 replay:

```text
261 content units
43 knowledge items
36 trackable KCs
15 parent topics
2 explicit cross-Ward leaf moves
verified: true
```

Audit teacher review files before using revise/reject labels to tune extraction:

```bash
.venv/bin/vlearn-kc review-audit path/to/reviews.json
```

The audit fails its quality gate when a non-pass decision lacks an actionable
rationale, a move lacks a target group, or high scores conflict with an
unexplained non-pass decision.

## Run with providers

Export configuration explicitly; the package does not load `.env` by itself.

```bash
export OPENAI_API_KEY='<openai-api-key>'
export GEMINI_API_KEYS='<key-1>,<key-2>'

.venv/bin/vlearn-kc run \
  examples/day01/material-bundle \
  runs/day01
```

Useful overrides:

```text
--generation-base-url (legacy alias: --gateway-base-url)
--generation-model (legacy alias: --gateway-model)
--reasoning-effort
--gemini-base-url
--embedding-model
--embedding-cache
--extraction-prompt
--refinement-prompt
```

## Output contract

```text
run/
├── kc-candidates.json
├── embeddings.json
├── embedding-cache.json
├── ward-candidates.json
├── parent-topics.json
└── run-manifest.json
```

`run-manifest.json` records input, prompt and artifact hashes along with provider
telemetry. Its `counts` section reports `core_kcs`, `extension_kcs`, and
`reference_concepts` separately. The `knowledge_roles` section groups compact KC
details by role; full source evidence remains in `kc-candidates.json` to avoid
duplicating large content. It always contains:

```json
{
  "release": {
    "auto_publish": false,
    "production_write": false
  }
}
```

## Parent refinement policy

Allowed actions:

```text
keep
split
move one or more explicitly logged leaves
rename
```

Disallowed action:

```text
merge whole parent clusters
```

Every final parent declares its Ward home. Every cross-Ward member must have an
exact source/target move record, and no Ward baseline cluster may disappear.

## Included data

`examples/day01/` is a fully replayable sample with AI-ready material,
embeddings and the validated K=15 parent result.

`artifacts/phase1-leaf-review-snapshot/` contains all 15 days and 526 generated
leaf KCs plus their independent-review sidecars. It intentionally excludes raw
media, provider logs, stale Ward candidates and legacy parent clusters.

`material-bundles/phase1/` contains canonical, validated inputs for all 15 days.
These bundles replace the previous hidden dependency on transcript ZIPs,
`selected-manifest`, PDF paths and separate `evidence_sections.json` files. A
teammate can rerun any day directly:

```bash
.venv/bin/vlearn-kc run material-bundles/phase1/day03 runs/day03
```

## Source layout

```text
src/vlearn_kc/
├── contracts.py
├── extraction.py
├── providers.py
├── clustering.py
├── refinement.py
├── pipeline.py
├── replay.py
├── cli.py
└── prompts/
```

No module performs dynamic imports or repository discovery. All filesystem
reads are rooted in explicit CLI input, output, cache or prompt arguments.

## Current scope

The runnable core stops after validated parent topics. The included Phase 1
leaf snapshot contains existing independent KC judge results for review. PG is
a downstream package and is intentionally not coupled into this KC package.
