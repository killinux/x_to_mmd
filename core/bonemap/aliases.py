"""XPS/XNALara generic-skeleton -> MMD bone mapping data (bpy-independent).

`XNALARA` maps a normalized, side-stripped base (from normalize.analyze) to an
MMD slot key. `SLOT_JP` gives each slot its MMD Japanese name; SIDED slots get a
左/右 prefix. Finger digits are FULL-WIDTH (０１２３) to match VMD conventions.
"""
from __future__ import annotations

SLOT_JP = {
    "all_parent": "全ての親", "center": "センター", "groove": "グルーブ", "waist": "腰",
    "lower_body": "下半身", "upper_body": "上半身", "upper_body2": "上半身2", "upper_body3": "上半身3",
    "neck": "首", "head": "頭",
    "shoulder": "肩", "arm": "腕", "elbow": "ひじ", "wrist": "手首",
    "leg": "足", "knee": "ひざ", "ankle": "足首", "toe": "つま先",
    "eye": "目", "bust": "胸",
    "thumb0": "親指０", "thumb1": "親指１", "thumb2": "親指２",
    "index1": "人指１", "index2": "人指２", "index3": "人指３",
    "middle1": "中指１", "middle2": "中指２", "middle3": "中指３",
    "ring1": "薬指１", "ring2": "薬指２", "ring3": "薬指３",
    "little1": "小指１", "little2": "小指２", "little3": "小指３",
}

SIDED = {
    "shoulder", "arm", "elbow", "wrist", "leg", "knee", "ankle", "toe", "eye", "bust",
    "thumb0", "thumb1", "thumb2", "index1", "index2", "index3",
    "middle1", "middle2", "middle3", "ring1", "ring2", "ring3", "little1", "little2", "little3",
}

# normalized side-stripped base  ->  slot
XNALARA = {
    "root_ground": "all_parent",
    "root_hips": "center",
    "pelvis": "lower_body",
    "spine_lower": "upper_body",
    "spine_middle": "upper_body2",
    "spine_upper": "upper_body3",
    "head_neck_lower": "neck",
    "head_neck_upper": "head",
    "leg_thigh": "leg", "leg_knee": "knee", "leg_ankle": "ankle",
    "leg_toes": "toe", "leg_toe": "toe",
    "arm_shoulder_1": "shoulder", "arm_shoulder_2": "arm",
    "arm_elbow": "elbow", "arm_wrist": "wrist",
    "head_eyeball": "eye",
    "boob_1": "bust",
    "arm_finger_1a": "thumb0", "arm_finger_1b": "thumb1", "arm_finger_1c": "thumb2",
    "arm_finger_2a": "index1", "arm_finger_2b": "index2", "arm_finger_2c": "index3",
    "arm_finger_3a": "middle1", "arm_finger_3b": "middle2", "arm_finger_3c": "middle3",
    "arm_finger_4a": "ring1", "arm_finger_4b": "ring2", "arm_finger_4c": "ring3",
    "arm_finger_5a": "little1", "arm_finger_5b": "little2", "arm_finger_5c": "little3",
}

# original-name substrings that mark a junk/twist/muscle bone to merge into its parent
MERGE_HINTS = ("unused", "foretwist", "twist", "muscle", "xtra")


def mmd_name(slot: str, side):
    base = SLOT_JP[slot]
    if slot in SIDED:
        return ("左" if side == "L" else "右") + base
    return base
