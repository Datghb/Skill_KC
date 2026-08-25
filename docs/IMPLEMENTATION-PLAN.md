# Standalone KC Pipeline Implementation Plan

**Goal:** Replace the experiment import chain with one standalone package and a reproducible Day 1 fixture.

## Tasks

1. Define and test material, KC and parent-topic contracts.
2. Add explicit generation and embedding provider interfaces.
3. Extract current KC prompt and response validation into focused modules.
4. Implement Ward candidate generation with a local embedding cache.
5. Implement select-K, split and leaf-move refinement without parent merge.
6. Add CLI commands for validation, extraction, clustering and full execution.
7. Build a Day 1 material fixture from canonical artifacts.
8. Verify the fixture offline and add mocked provider integration tests.
9. Add README, environment example, schema files and run manifest documentation.
10. Package only after all standalone checks pass.

