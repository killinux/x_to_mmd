"""Unit tests for the native XPS parser, using hand-built fixtures that exercise
all three layouts (ASCII, legacy .mesh, header-bearing .xps) and the version
booleans (tangent presence, fixed-4 vs variable weights)."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.xps import read_ascii, read_bin, parse_mesh_name  # noqa: E402
from core.xps.binreader import BinReader  # noqa: E402


# ---- binary builder helpers (mirror the on-disk format) ----
def s(text):
    b = text.encode("utf-8")
    n = len(b)
    out = b""
    while True:
        byte = n & 0x7F
        n >>= 7
        out += bytes([byte | 0x80]) if n else bytes([byte])
        if not n:
            break
    return out + b


def u32(v):
    return struct.pack("<I", v)


def i16(v):
    return struct.pack("<h", v)


def f(v):
    return struct.pack("<f", v)


def color():
    return bytes([255, 255, 255, 255])


# ---------------------------------------------------------------------------
def test_varint_roundtrip():
    # multi-byte .NET 7-bit length (e.g. 300 -> 0xAC 0x02)
    r = BinReader(s("x" * 300))
    assert r.varint() == 300
    assert r.read(300) == b"x" * 300


def test_parse_mesh_name():
    assert parse_mesh_name("8_Face_1_0_0") == (8, "Face")
    assert parse_mesh_name("12_Hair") == (12, "Hair")
    assert parse_mesh_name("PlainName") == (None, "PlainName")


def test_ascii_basic():
    text = "\n".join([
        "2",                      # bone count
        "root", "-1", "0 0 0",
        "spine", "0", "0 1 0",
        "1",                      # mesh count
        "8_Body_1_0_0",           # mesh name
        "1",                      # uv layers
        "1",                      # textures
        "body.png", "0",
        "3",                      # vertices
        "0 0 0", "0 0 1", "255 255 255 255", "0.0 0.0", "0 1 0 0", "0.5 0.5 0 0",
        "1 0 0", "0 0 1", "255 255 255 255", "0.1 0.0", "0 1 0 0", "1.0 0.0 0 0",
        "0 1 0", "0 0 1", "255 255 255 255", "0.0 0.1", "1 0 0 0", "1.0 0.0 0 0",
        "1",                      # faces
        "0 1 2",
    ])
    m = read_ascii(text)
    assert m.fmt == "ascii"
    assert len(m.bones) == 2
    assert m.bones[0].name == "root" and m.bones[0].parent_id == -1
    assert m.bones[1].pos == (0.0, 1.0, 0.0)
    assert len(m.meshes) == 1
    mesh = m.meshes[0]
    assert mesh.render_group == 8 and mesh.base_name == "Body"
    assert mesh.uv_layer_count == 1 and len(mesh.textures) == 1
    assert mesh.textures[0].file == "body.png"
    assert len(mesh.vertices) == 3 and mesh.faces == [(0, 1, 2)]
    v = mesh.vertices[1]
    assert v.uvs == [(0.1, 0.0)] and v.bones == [0, 1, 0, 0]
    assert v.weights[0] == 1.0
    assert m.total_vertices == 3 and m.total_faces == 1


def _legacy_mesh_bytes():
    d = b""
    d += u32(2)                                   # 2 bones
    d += s("root") + i16(-1) + f(0) + f(0) + f(0)
    d += s("bone1") + i16(0) + f(0) + f(1) + f(0)
    d += u32(1)                                   # 1 mesh
    d += s("8_Test_1_0_0") + u32(1) + u32(1)      # name, 1 uv, 1 texture
    d += s("tex.png") + u32(0)
    d += u32(3)                                   # 3 vertices
    for vi in range(3):
        d += f(vi) + f(0) + f(0)                  # pos
        d += f(0) + f(0) + f(1)                   # normal
        d += color()
        d += f(0.1 * vi) + f(0.2 * vi)            # uv layer 0
        d += f(0) + f(0) + f(1) + f(1)            # tangent (legacy => present)
        d += i16(0) + i16(1) + i16(0) + i16(0)    # fixed-4 bone idx
        d += f(1.0) + f(0.0) + f(0.0) + f(0.0)    # fixed-4 weights
    d += u32(1) + u32(0) + u32(1) + u32(2)        # 1 face
    return d


def test_legacy_mesh_binary():
    m = read_bin(_legacy_mesh_bytes())
    assert m.fmt == "mesh" and m.header is None
    assert len(m.bones) == 2 and m.bones[1].parent_id == 0
    assert len(m.meshes) == 1
    mesh = m.meshes[0]
    assert mesh.render_group == 8 and len(mesh.vertices) == 3
    uv = mesh.vertices[2].uvs[0]
    assert abs(uv[0] - 0.2) < 1e-6 and abs(uv[1] - 0.4) < 1e-6
    assert mesh.vertices[0].bones == [0, 1, 0, 0]
    assert m.total_faces == 1


def _xps_header_bytes():
    h = u32(323232) + struct.pack("<H", 3) + struct.pack("<H", 15)  # magic, v3.15
    h += s("XNAaraL")
    h += u32(0)                                   # settings_len (NEW uses items)
    h += s("machine") + s("user") + s("files")
    h += u32(0)                                   # hash
    h += u32(0)                                   # items = 0
    body = u32(1)                                 # 1 bone
    body += s("root") + i16(-1) + f(0) + f(0) + f(0)
    body += u32(1)                                # 1 mesh
    body += s("mesh") + u32(1) + u32(0)           # name, 1 uv, 0 textures
    body += u32(1)                                # 1 vertex
    body += f(0) + f(0) + f(0) + f(0) + f(0) + f(1) + color()
    body += f(0.5) + f(0.5)                       # uv (no tangent on v3.15)
    body += i16(2)                                # variable weight count = 2
    body += i16(0) + i16(0)
    body += f(0.7) + f(0.3)
    body += u32(0)                                # 0 faces
    return h + body


def test_xps_header_binary_variable_weights():
    m = read_bin(_xps_header_bytes())
    assert m.fmt == "xps"
    assert m.header.version_major == 3 and m.header.version_minor == 15
    assert m.header.has_tangent is False
    assert m.header.has_variable_weights is True
    assert len(m.bones) == 1 and len(m.meshes) == 1
    v = m.meshes[0].vertices[0]
    assert v.bones == [0, 0] and abs(v.weights[0] - 0.7) < 1e-6
    assert v.uvs == [(0.5, 0.5)]
