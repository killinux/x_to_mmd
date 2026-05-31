"""Resolve a parsed XpsModel into a per-bone conversion plan (bpy-independent).

Each source bone gets an action:
  'rename'  -> give it the MMD Japanese name (weights carried as-is)
  'merge'   -> fold it (and its weights, via ADD) into the nearest kept/renamed
               ancestor; for junk/twist/muscle bones that carry skin weight
  'keep'    -> leave as-is (facial/hair/accessory bones the target also keeps)

This NEVER splits weights. Merge = additive transfer (allowed); the caller must
get user confirmation before any actual weight SPLIT (see CLAUDE.md §1).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from . import aliases
from .normalize import analyze


@dataclass
class BonePlan:
    index: int
    source: str
    action: str               # 'rename' | 'merge' | 'keep'
    mmd_name: Optional[str] = None    # for 'rename'
    slot: Optional[str] = None
    side: Optional[str] = None
    merge_into: Optional[int] = None  # for 'merge': target source-bone index
    weighted: int = 0          # weighted-vertex count


def _weight_counts(xps) -> List[int]:
    cnt = [0] * len(xps.bones)
    for mesh in xps.meshes:
        for v in mesh.vertices:
            for b, w in zip(v.bones, v.weights):
                if w > 0 and 0 <= b < len(cnt):
                    cnt[b] += 1
    return cnt


def resolve(xps) -> List[BonePlan]:
    cnt = _weight_counts(xps)
    plans: List[BonePlan] = [None] * len(xps.bones)  # type: ignore

    # pass 1: rename matches
    for i, b in enumerate(xps.bones):
        base, side = analyze(b.name)
        slot = aliases.XNALARA.get(base)
        if slot:
            plans[i] = BonePlan(i, b.name, "rename", aliases.mmd_name(slot, side),
                                slot, side, weighted=cnt[i])

    # pass 2: classify the rest (merge junk/twist/muscle, else keep)
    low = [b.name.lower() for b in xps.bones]
    for i, b in enumerate(xps.bones):
        if plans[i] is not None:
            continue
        is_junk = any(h in low[i] for h in aliases.MERGE_HINTS)
        if is_junk:
            plans[i] = BonePlan(i, b.name, "merge", weighted=cnt[i])
        else:
            plans[i] = BonePlan(i, b.name, "keep", weighted=cnt[i])

    # pass 3: resolve merge targets = nearest ancestor that is rename/keep
    def nearest_kept(idx: int) -> Optional[int]:
        p = xps.bones[idx].parent_id
        seen = 0
        while 0 <= p < len(xps.bones) and seen < len(xps.bones):
            if plans[p].action in ("rename", "keep"):
                return p
            p = xps.bones[p].parent_id
            seen += 1
        return None

    for i in range(len(xps.bones)):
        if plans[i].action == "merge":
            plans[i].merge_into = nearest_kept(i)
    return plans


def summarize(plans: List[BonePlan]) -> dict:
    by = {"rename": 0, "merge": 0, "keep": 0}
    for p in plans:
        by[p.action] += 1
    return by
