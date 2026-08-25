# VLearn KC Pipeline Standalone Design

## Goal

Provide a clean, independently runnable Knowledge Component pipeline that starts
from a canonical AI-ready material bundle and produces validated KC and parent
topic artifacts without importing legacy experiments or the host repository's
`src/` package.

## Boundary

Upstream owns conversion of raw PDF, Markdown, slide pages, transcript and video
alignment into one material bundle. This package does not discover files in
`Downloads`, infer repository roots or parse arbitrary historical layouts.

Input per lesson:

```text
material-bundle/
├── lesson.json
├── sources.json
└── content_units.json
```

Output per run:

```text
run/
├── kc-candidates.json
├── embeddings.json
├── ward-candidates.json
├── parent-topics.json
├── run-manifest.json
└── logs/
```

## Pipeline

```text
validate material bundle
→ extract frozen leaf KCs
→ embed trackable leaves
→ generate Ward candidate cuts
→ select K, split and move individual leaves
→ reject whole-cluster merge
→ validate exact leaf partition and Ward lineage
→ write immutable run manifest
```

## Dependency policy

- No absolute source paths.
- No dynamic imports from dated experiment folders.
- No `VLEARN_REPO_ROOT` requirement.
- No hidden reads from `.env`, transcript ZIPs or previous run directories.
- Provider configuration is explicit through CLI/environment.
- Every input and prompt is represented by a SHA-256 hash in the run manifest.

## Data policy

The runnable handoff contains one Day 1 fixture and the final Phase 1 KC review
snapshot. Raw video, PDF and credentials remain separate upstream assets.

## Safety gates

- Every source content unit has a stable ID and source hash.
- Every leaf KC cites existing content-unit IDs.
- Every trackable leaf appears exactly once in the parent partition.
- Parent refinement may keep, split, move a leaf or rename a parent.
- Whole-parent merge is prohibited.
- Every cross-Ward leaf move is explicit and auditable.
- No stage publishes to runtime automatically.

