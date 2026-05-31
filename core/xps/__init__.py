"""Native XPS/XNALara model parser (bpy-independent).

    from core.xps import read_xps_model
    model = read_xps_model("foo.xps")   # .xps / .mesh / .mesh.ascii / .ascii
    print(model.summary())

Returns RAW XPS-space data; the Blender import layer applies the coordinate
transform exactly once.
"""
from __future__ import annotations

import struct

from .read_ascii import read_ascii
from .read_bin import MAGIC_NUMBER, parse_mesh_name, read_bin
from .types import (
    XpsBone,
    XpsHeader,
    XpsMesh,
    XpsModel,
    XpsTexture,
    XpsVertex,
)

__all__ = [
    "read_xps_model", "read_bin", "read_ascii", "parse_mesh_name",
    "XpsModel", "XpsBone", "XpsMesh", "XpsVertex", "XpsTexture", "XpsHeader",
    "MAGIC_NUMBER",
]


def _looks_text(head: bytes) -> bool:
    if b"\x00" in head:
        return False
    return all(0x09 <= b <= 0x7E or b in (0x0A, 0x0D) for b in head)


def read_xps_model(path: str) -> XpsModel:
    """Dispatch by extension + magic number to the right reader."""
    low = path.lower()
    if low.endswith(".ascii"):
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return read_ascii(f.read())

    with open(path, "rb") as f:
        data = f.read()

    if len(data) >= 4 and struct.unpack_from("<I", data, 0)[0] == MAGIC_NUMBER:
        return read_bin(data)            # .xps (header-bearing)

    # No magic: legacy header-less .mesh — unless it is really ASCII mis-named.
    if _looks_text(data[:64]):
        return read_ascii(data.decode("utf-8-sig", errors="replace"))
    return read_bin(data)                # legacy .mesh
