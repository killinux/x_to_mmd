"""XPS/XNALara -> MMD bone-name resolution (bpy-independent).

    from core.bonemap import resolve
    plans = resolve(xps_model)   # list of BonePlan (rename/merge/keep)
"""
from . import aliases
from .normalize import analyze, tokenize
from .resolver import BonePlan, resolve, summarize

__all__ = ["resolve", "summarize", "BonePlan", "analyze", "tokenize", "aliases"]
