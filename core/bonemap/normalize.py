"""Bone-name normalization + side detection (bpy-independent).

Turns a raw source bone name into (base, side) where `base` is a normalized,
side-stripped, junk-prefix-stripped key for dictionary lookup, and side is
'L' / 'R' / None. Only the SOURCE side is normalized; MMD target names keep
their exact (full/half-width) form.
"""
from __future__ import annotations

import re
import unicodedata

# Rig/exporter prefixes that carry no semantic meaning.
JUNK_TOKENS = {"unused", "bip001", "bip01", "valvebiped", "mixamorig", "def", "cf", "b"}
SIDE_L = {"left", "l", "lft"}
SIDE_R = {"right", "r", "rgt"}

_SPLIT = re.compile(r"[ _\-\.\:\\/]+")


def tokenize(name: str):
    s = unicodedata.normalize("NFKC", name).lower()
    return [t for t in _SPLIT.split(s) if t]


def analyze(name: str):
    """Return (base, side). base is '_'-joined, side-and-junk stripped."""
    side = None
    out = []
    for t in tokenize(name):
        if t in SIDE_L:
            side = side or "L"
            continue
        if t in SIDE_R:
            side = side or "R"
            continue
        if t in JUNK_TOKENS:
            continue
        out.append(t)
    return "_".join(out), side
