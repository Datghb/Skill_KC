from __future__ import annotations

from typing import Any, Mapping

import numpy as np
from scipy.cluster.hierarchy import cut_tree, linkage
from sklearn.metrics import silhouette_score


TRACKABLE_ROLES = {"core_kc", "extension_kc"}


def trackable_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item.get("knowledge_role") in TRACKABLE_ROLES]


def _evidence_content(evidence: Mapping[str, Any]) -> str:
    return str(evidence.get("content") or "").strip()


def embedding_text(item: Mapping[str, Any]) -> str:
    evidence = [
        _evidence_content(value) for value in item.get("resolved_evidence") or []
    ]
    blocks = [
        f"Tên: {str(item['name_vi']).strip()}",
        f"Ranh giới: {str(item['description_vi']).strip()}",
        f"Năng lực: {str(item.get('primary_capability_vi') or '').strip()}",
        f"Target Bloom: {str(item.get('target_bloom_level') or '').strip()}",
        f"Vai trò: {str(item['knowledge_role']).strip()}",
        "Bằng chứng:\n" + "\n\n".join(value for value in evidence if value),
    ]
    return "\n\n".join(block for block in blocks if block.strip())


def _first_page(item: Mapping[str, Any]) -> int:
    pages = [
        int(value["page_no"])
        for value in item.get("resolved_evidence") or []
        if value.get("page_no") is not None
    ]
    return min(pages) if pages else 10_000


def _normalized(vectors: np.ndarray) -> np.ndarray:
    value = np.asarray(vectors, dtype=float)
    if value.ndim != 2:
        raise ValueError("embedding matrix must be two-dimensional")
    norms = np.linalg.norm(value, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("embedding matrix contains a zero vector")
    return value / norms


def _memberships(
    labels: np.ndarray, items: list[dict[str, Any]]
) -> list[list[str]]:
    by_label: dict[int, list[dict[str, Any]]] = {}
    for item, label in zip(items, labels):
        by_label.setdefault(int(label), []).append(item)
    groups = [
        sorted(group, key=lambda item: (_first_page(item), str(item["code"])))
        for group in by_label.values()
    ]
    groups.sort(key=lambda group: (_first_page(group[0]), str(group[0]["code"])))
    return [[str(item["code"]) for item in group] for group in groups]


def ward_candidates(
    items: list[dict[str, Any]],
    vectors: np.ndarray,
    *,
    max_k: int = 15,
) -> dict[str, Any]:
    if len(items) < 3:
        raise ValueError("Ward clustering requires at least three trackable items")
    if len(items) != len(vectors):
        raise ValueError("item and embedding counts differ")
    normalized = _normalized(vectors)
    tree = linkage(normalized, method="ward", optimal_ordering=True)
    upper = min(max_k, len(items) - 1)
    cuts = []
    for k in range(2, upper + 1):
        labels = cut_tree(tree, n_clusters=[k]).reshape(-1)
        membership = _memberships(labels, items)
        sizes = [len(group) for group in membership]
        cuts.append(
            {
                "k": k,
                "silhouette_cosine": round(
                    float(silhouette_score(normalized, labels, metric="cosine")),
                    6,
                ),
                "singleton_count": sum(size == 1 for size in sizes),
                "min_cluster_size": min(sizes),
                "median_cluster_size": float(np.median(sizes)),
                "max_cluster_size": max(sizes),
                "membership": membership,
            }
        )
    return {
        "schema_version": "vlearn_ward_candidates_v1",
        "algorithm": "l2_normalized_ward_hierarchical",
        "trackable_kc_count": len(items),
        "candidate_k_range": [cuts[0]["k"], cuts[-1]["k"]],
        "candidate_cuts": cuts,
        "ward_linkage": tree.tolist(),
    }

