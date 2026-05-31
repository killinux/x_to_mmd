"""PMX reader test on a hand-built minimal PMX 2.0 (UTF-8, 1-byte indices)."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pmx import read_pmx  # noqa: E402


def i32(v):
    return struct.pack("<i", v)


def f(v):
    return struct.pack("<f", v)


def by(v):
    return bytes([v])


def txt(s):
    b = s.encode("utf-8")
    return i32(len(b)) + b


def _build_pmx():
    d = b"PMX " + f(2.0) + by(8) + bytes([1, 0, 1, 1, 1, 1, 1, 1])  # utf8, all idx size 1
    d += txt("m") + txt("m") + txt("") + txt("")
    # 3 vertices (BDEF1), Y = 0,1,2 -> bounds
    d += i32(3)
    for k in range(3):
        d += f(float(k)) + f(float(k)) + f(0.0)   # position
        d += f(0.0) + f(0.0) + f(1.0)             # normal
        d += f(0.0) + f(0.0)                       # uv
        d += by(0)                                 # BDEF1
        d += struct.pack("<b", 0)                  # bone 0
        d += f(1.0)                                # edge scale
    # 1 face
    d += i32(3) + bytes([0, 1, 2])
    # 0 textures
    d += i32(0)
    # 1 material
    d += i32(1)
    d += txt("mat") + txt("mat")
    d += f(1) + f(1) + f(1) + f(1)                 # diffuse
    d += f(0) + f(0) + f(0) + f(0.5)               # specular + strength
    d += f(0.5) + f(0.5) + f(0.5)                  # ambient
    d += by(0x1E)                                  # flags (shadows + edge)
    d += f(0) + f(0) + f(0) + f(1) + f(1.0)        # edge color + size
    d += struct.pack("<b", -1) + struct.pack("<b", -1)  # tex / sphere index
    d += by(0) + by(1) + by(0)                     # sphere mode, toon shared, toon idx
    d += txt("") + i32(3)                          # memo + surface count
    # 2 bones; bone1 inherits rotation from bone0 (付与 0.5)
    d += i32(2)
    d += txt("全ての親") + txt("root") + f(0) + f(0) + f(0)
    d += struct.pack("<b", -1) + i32(0) + struct.pack("<H", 0x000A) + f(0) + f(0) + f(1)
    d += txt("センター") + txt("center") + f(0) + f(1) + f(0)
    d += struct.pack("<b", 0) + i32(0) + struct.pack("<H", 0x010A) + f(0) + f(0) + f(1)
    d += struct.pack("<b", 0) + f(0.5)             # grant parent + weight
    # morphs / display / rigidbodies / joints = 0
    d += i32(0) + i32(0) + i32(0) + i32(0)
    return d


def test_pmx_minimal():
    m = read_pmx(_build_pmx())
    assert m.version == 2.0 and m.encoding == 1
    assert m.vertex_count == 3 and m.face_count == 1
    assert len(m.textures) == 0 and len(m.materials) == 1
    assert m.materials[0].name == "mat" and m.materials[0].has_edge
    assert len(m.bones) == 2
    assert m.bones[0].name == "全ての親" and m.bones[0].parent == -1
    assert m.bones[1].name == "センター" and m.bones[1].inherit_rotation
    assert m.bones[1].grant_parent == 0 and abs(m.bones[1].grant_weight - 0.5) < 1e-6
    # vertex bounds (Y from 0..2)
    assert abs(m.vmax[1] - 2.0) < 1e-6 and abs(m.vmin[1] - 0.0) < 1e-6
    s = m.summary()
    assert s["bones_with_grant"] == 1 and s["bones_with_ik"] == 0
