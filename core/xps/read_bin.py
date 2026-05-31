"""Binary XPS reader: handles both the header-bearing `.xps` ("Generic Item 2")
and the legacy header-less `.mesh` layout.

Clean-room reimplementation of johnzero7/XNALaraMesh's read_bin_xps.py — faithful
in byte consumption, validated empirically against the reference importer.
"""
from __future__ import annotations

from typing import Optional

from .binreader import BinReader
from .types import XpsBone, XpsHeader, XpsMesh, XpsModel, XpsTexture, XpsVertex

MAGIC_NUMBER = 323232


def _has_tangent(vmaj: int, vmin: int, has_header: bool) -> bool:
    # Old/early XPS (and legacy .mesh) interleave a 4-float tangent per UV layer.
    return (vmin <= 12 and vmaj <= 2) if has_header else True


def _has_variable_weights(vmaj: int, vmin: int, has_header: bool) -> bool:
    # XPS >= v3 (11.8.9+) stores a per-vertex weight COUNT, not a fixed 4.
    return (vmaj >= 3) if has_header else False


def _roundup(n: int, m: int) -> int:
    return (n + m - 1) // m * m


def _basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def parse_mesh_name(name: str):
    """XPS mesh names encode "<renderGroupId>_<name>_<p1>_<p2>_<p3>".

    Returns (render_group:int|None, base_name:str). Defensive: if the first
    token is not an int, render_group is None and base_name is the whole name.
    """
    parts = name.split("_")
    if parts and parts[0].lstrip("-").isdigit():
        render_group = int(parts[0])
        rest = parts[1:]
        # strip trailing purely-numeric shader params
        while rest and _is_number(rest[-1]):
            rest.pop()
        base = "_".join(rest) if rest else name
        return render_group, base
    return None, name


def _is_number(tok: str) -> bool:
    try:
        float(tok)
        return True
    except ValueError:
        return False


def _read_header(r: BinReader) -> XpsHeader:
    """Consume the .xps header so the cursor lands exactly on the bone count."""
    magic = r.u32()
    vmaj = r.u16()
    vmin = r.u16()
    xna_aral = r.string()
    settings_len = r.u32()
    _machine = r.string()
    _user = r.string()
    _files = r.string()

    settings_start = r.tell()
    has_tangent = _has_tangent(vmaj, vmin, True)

    if has_tangent:
        # OLD format: a flat settings stream of settings_len * 4 bytes.
        r.read(settings_len * 4)
    else:
        # NEW format: hash, item count, then typed option items.
        _hash = r.u32()
        items = r.u32()
        for _ in range(items):
            opt_type = r.u32()
            opt_count = r.u32()
            _opt_info = r.u32()
            if opt_type == 0:            # None: opt_count uint32 of padding
                r.read(opt_count * 4)
            elif opt_type == 1:          # Pose: text rounded up to a multiple of 4
                r.read(_roundup(opt_count, 4))
            elif opt_type == 2:          # Flags: opt_count (flag,value) uint32 pairs
                r.read(opt_count * 8)
            else:                        # Unknown: waste to the declared block end
                consumed = r.tell() - settings_start
                rem = settings_len * 4 - consumed
                if rem > 0:
                    r.read(rem)
                break

    return XpsHeader(
        magic=magic,
        version_major=vmaj,
        version_minor=vmin,
        xna_aral=xna_aral,
        has_tangent=has_tangent,
        has_variable_weights=_has_variable_weights(vmaj, vmin, True),
    )


def _read_bones(r: BinReader):
    count = r.u32()
    if count > 1_000_000:
        raise ValueError(f"insane bone count {count} — header desync?")
    bones = []
    for _ in range(count):
        name = r.string()
        parent = r.i16()
        pos = tuple(r.floats(3))
        bones.append(XpsBone(name=name, parent_id=parent, pos=pos))
    return bones


def _read_meshes(r: BinReader, has_bones: bool, has_tangent: bool, has_var: bool):
    count = r.u32()
    if count > 1_000_000:
        raise ValueError(f"insane mesh count {count} — header/bone desync?")
    meshes = []
    for _ in range(count):
        name = r.string() or "unnamed"
        uv_count = r.u32()

        textures = []
        tex_count = r.u32()
        for _ in range(tex_count):
            tex_file = _basename(r.string())
            uv_layer = r.u32()
            textures.append(XpsTexture(file=tex_file, uv_layer=uv_layer))

        vcount = r.u32()
        verts = []
        for _ in range(vcount):
            pos = tuple(r.floats(3))
            normal = tuple(r.floats(3))
            color = (r.byte(), r.byte(), r.byte(), r.byte())

            uvs = []
            for _ in range(uv_count):
                uvs.append(tuple(r.floats(2)))
                if has_tangent:
                    r.floats(4)  # tangent — recomputed in Blender, discard

            bone_idx = []
            weights = []
            if has_bones:
                wc = r.i16() if has_var else 4
                bone_idx = [r.i16() for _ in range(wc)]
                weights = [r.f32() for _ in range(wc)]

            verts.append(XpsVertex(pos=pos, normal=normal, color=color,
                                   uvs=uvs, bones=bone_idx, weights=weights))

        tri_count = r.u32()
        faces = [(r.u32(), r.u32(), r.u32()) for _ in range(tri_count)]

        rg, base = parse_mesh_name(name)
        meshes.append(XpsMesh(name=name, textures=textures, uv_layer_count=uv_count,
                              vertices=verts, faces=faces, render_group=rg, base_name=base))
    return meshes


def read_bin(data: bytes) -> XpsModel:
    r = BinReader(data)
    has_header = r.peek_u32() == MAGIC_NUMBER

    header: Optional[XpsHeader] = _read_header(r) if has_header else None
    vmaj = header.version_major if header else 0
    vmin = header.version_minor if header else 0

    bones = _read_bones(r)
    has_bones = len(bones) > 0
    has_tangent = _has_tangent(vmaj, vmin, has_header)
    has_var = _has_variable_weights(vmaj, vmin, has_header)

    meshes = _read_meshes(r, has_bones, has_tangent, has_var)

    return XpsModel(bones=bones, meshes=meshes, header=header,
                    fmt="xps" if has_header else "mesh")
