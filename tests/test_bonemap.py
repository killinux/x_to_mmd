"""Bone-map resolver tests on a tiny synthetic XPS skeleton."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bonemap import analyze, resolve  # noqa: E402
from core.bonemap.aliases import mmd_name  # noqa: E402
from core.xps.types import XpsBone, XpsMesh, XpsModel, XpsVertex  # noqa: E402


def test_analyze_side_and_junk():
    assert analyze("arm left shoulder 1") == ("arm_shoulder_1", "L")
    assert analyze("unused bip001 pelvis") == ("pelvis", None)
    assert analyze("arm right finger 2a") == ("arm_finger_2a", "R")
    assert analyze("unused bip001 l foretwist") == ("foretwist", "L")


def test_mmd_name_sided_and_fullwidth():
    assert mmd_name("leg", "L") == "左足"
    assert mmd_name("index1", "R") == "右人指１"   # full-width digit
    assert mmd_name("lower_body", None) == "下半身"


def _mini_model():
    bones = [
        XpsBone("root ground", -1, (0, 0, 0)),
        XpsBone("unused bip001 pelvis", 0, (0, 1, 0)),
        XpsBone("leg left thigh", 1, (0.1, 1, 0)),
        XpsBone("unused bip001 xtra04", 2, (0.1, 0.9, 0)),   # junk child of thigh
        XpsBone("head jaw", 1, (0, 1.6, 0)),                 # facial -> keep
    ]
    # one vertex weighted to the junk bone (idx 3) so it has weight
    v = XpsVertex(pos=(0, 0, 0), normal=(0, 0, 1), color=(255, 255, 255, 255),
                  uvs=[(0, 0)], bones=[3, 0, 0, 0], weights=[1.0, 0, 0, 0])
    mesh = XpsMesh("m", [], 1, [v], [])
    return XpsModel(bones=bones, meshes=[mesh])


def test_resolve_actions():
    plans = resolve(_mini_model())
    by_idx = {p.index: p for p in plans}
    assert by_idx[0].action == "rename" and by_idx[0].mmd_name == "全ての親"
    assert by_idx[1].action == "rename" and by_idx[1].mmd_name == "下半身"
    assert by_idx[2].action == "rename" and by_idx[2].mmd_name == "左足"
    # junk bone -> merge into nearest renamed ancestor (the thigh)
    assert by_idx[3].action == "merge" and by_idx[3].merge_into == 2
    assert by_idx[3].weighted == 1
    # facial bone -> keep
    assert by_idx[4].action == "keep"
