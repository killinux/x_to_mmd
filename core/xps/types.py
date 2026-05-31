"""Intermediate data model for a parsed XPS/XNALara model (bpy-independent).

Coordinates are RAW XPS space (left-handed, Y-up, +Z into screen). The Blender
import layer is responsible for applying the (x,y,z)->(x,-z,y) transform, winding
reversal and UV v-flip EXACTLY ONCE — the parser never transforms.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

Vec3 = Tuple[float, float, float]
Vec2 = Tuple[float, float]


@dataclass
class XpsBone:
    name: str
    parent_id: int          # index into the bone list; -1 (0xFFFF as int16) = root
    pos: Vec3               # model-space (absolute), raw XPS coords


@dataclass
class XpsTexture:
    file: str              # basename only
    uv_layer: int


@dataclass
class XpsVertex:
    pos: Vec3
    normal: Vec3
    color: Tuple[int, int, int, int]      # RGBA 0..255
    uvs: List[Vec2]                        # one per uv layer
    bones: List[int] = field(default_factory=list)     # bone indices (raw, may include 0-weight padding)
    weights: List[float] = field(default_factory=list)  # parallel to `bones`, NOT normalized


@dataclass
class XpsMesh:
    name: str
    textures: List[XpsTexture]
    uv_layer_count: int
    vertices: List[XpsVertex]
    faces: List[Tuple[int, int, int]]      # triangle vertex indices, local to this mesh
    # Parsed from the encoded mesh name "<group>_<name>_<p1>_<p2>_<p3>":
    render_group: Optional[int] = None
    base_name: Optional[str] = None


@dataclass
class XpsHeader:
    magic: int
    version_major: int
    version_minor: int
    xna_aral: str = ""
    has_tangent: bool = False
    has_variable_weights: bool = False


@dataclass
class XpsModel:
    bones: List[XpsBone] = field(default_factory=list)
    meshes: List[XpsMesh] = field(default_factory=list)
    header: Optional[XpsHeader] = None
    fmt: str = ""          # 'xps' (binary+header) | 'mesh' (legacy binary) | 'ascii'

    @property
    def has_bones(self) -> bool:
        return len(self.bones) > 0

    @property
    def total_vertices(self) -> int:
        return sum(len(m.vertices) for m in self.meshes)

    @property
    def total_faces(self) -> int:
        return sum(len(m.faces) for m in self.meshes)

    def summary(self) -> dict:
        return {
            "fmt": self.fmt,
            "version": (self.header.version_major, self.header.version_minor) if self.header else None,
            "has_tangent": self.header.has_tangent if self.header else None,
            "has_variable_weights": self.header.has_variable_weights if self.header else None,
            "bones": len(self.bones),
            "meshes": len(self.meshes),
            "vertices": self.total_vertices,
            "faces": self.total_faces,
            "bone_names_head": [b.name for b in self.bones[:30]],
            "mesh_names_head": [m.name for m in self.meshes[:15]],
        }
