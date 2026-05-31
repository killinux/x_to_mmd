"""ASCII XPS reader (.mesh.ascii / .ascii) — line-based, '#' starts a comment.

Mirrors johnzero7/XNALaraMesh's read_ascii_xps.py field order. ASCII never carries
tangents and always stores 4 bone indices/weights per vertex (zero-padded).
"""
from __future__ import annotations

from typing import List

from .read_bin import _basename, parse_mesh_name
from .types import XpsBone, XpsMesh, XpsModel, XpsTexture, XpsVertex


class _Cursor:
    def __init__(self, text: str):
        self._lines = text.split("\n")
        self._i = 0

    def line(self) -> str:
        ln = self._lines[self._i].strip()
        self._i += 1
        return ln


def _ignore_comment(line: str) -> str:
    # numeric value lines: '53 # bone count' -> '53'
    return line.replace("#", " ").split()[0]


def _ignore_str_comment(line: str) -> str:
    # string lines keep internal spaces ('root ground'), drop a trailing '# ...'
    return line.split("#")[0].strip()


def _split_values(line: str) -> List[str]:
    return line.replace("#", " ").split()


def _fill(arr: List[str], n: int, val):
    return arr + [val] * (n - len(arr))


def _read_int(c: _Cursor) -> int:
    return int(_ignore_comment(c.line()))


def _read_string(c: _Cursor) -> str:
    return _ignore_str_comment(c.line())


def _read_floats(c: _Cursor, n: int):
    vals = _fill(_split_values(c.line()), n, "0")
    return [float(vals[i]) for i in range(n)]


def _read_ints(c: _Cursor, n: int):
    vals = _fill(_split_values(c.line()), n, "0")
    return [int(vals[i]) for i in range(n)]


def _read_bones(c: _Cursor):
    count = _read_int(c)
    bones = []
    for _ in range(count):
        name = _read_string(c)
        parent = _read_int(c)
        pos = tuple(_read_floats(c, 3))
        bones.append(XpsBone(name=name, parent_id=parent, pos=pos))
    return bones


def _read_meshes(c: _Cursor, has_bones: bool):
    count = _read_int(c)
    meshes = []
    for _ in range(count):
        name = _read_string(c) or "unnamed"
        uv_count = _read_int(c)

        textures = []
        tex_count = _read_int(c)
        for _ in range(tex_count):
            tex_file = _basename(_read_string(c))
            uv_layer = _read_int(c)
            textures.append(XpsTexture(file=tex_file, uv_layer=uv_layer))

        vcount = _read_int(c)
        verts = []
        for _ in range(vcount):
            pos = tuple(_read_floats(c, 3))
            normal = tuple(_read_floats(c, 3))
            color = tuple(_read_ints(c, 4))

            uvs = []
            for _ in range(uv_count):
                uvs.append(tuple(_read_floats(c, 2)))

            bone_idx: List[int] = []
            weights: List[float] = []
            if has_bones:
                bone_idx = _read_ints(c, 4)
                weights = _read_floats(c, 4)

            verts.append(XpsVertex(pos=pos, normal=normal, color=color,
                                   uvs=uvs, bones=bone_idx, weights=weights))

        tri_count = _read_int(c)
        faces = [tuple(_read_ints(c, 3)) for _ in range(tri_count)]

        rg, base = parse_mesh_name(name)
        meshes.append(XpsMesh(name=name, textures=textures, uv_layer_count=uv_count,
                              vertices=verts, faces=faces, render_group=rg, base_name=base))
    return meshes


def read_ascii(text: str) -> XpsModel:
    c = _Cursor(text)
    bones = _read_bones(c)
    meshes = _read_meshes(c, has_bones=len(bones) > 0)
    return XpsModel(bones=bones, meshes=meshes, header=None, fmt="ascii")
