"""Lightweight PMX data model (bpy-independent) — enough to diff two PMX files
at the structural level (bones / materials / morphs / display frames / physics).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class PmxBone:
    name: str                 # Japanese (local) name — what VMD matches
    name_en: str
    parent: int               # bone index, -1 = none
    position: Tuple[float, float, float]
    layer: int
    flags: int
    tail_is_bone: bool
    tail: object              # bone index (int) or vec3
    # append/grant (付与):
    inherit_rotation: bool = False
    inherit_translation: bool = False
    grant_parent: int = -1
    grant_weight: float = 0.0
    transform_order: int = 0  # == layer (deform tier)
    has_ik: bool = False
    ik_target: int = -1
    ik_links: List[int] = field(default_factory=list)

    @property
    def visible(self) -> bool:
        return bool(self.flags & 0x0008)


@dataclass
class PmxMaterial:
    name: str
    name_en: str
    diffuse: Tuple[float, float, float, float]
    specular: Tuple[float, float, float]
    specular_strength: float
    ambient: Tuple[float, float, float]
    flags: int
    edge_color: Tuple[float, float, float, float]
    edge_size: float
    texture_index: int
    sphere_index: int
    sphere_mode: int          # 0 none,1 mult,2 add,3 subtex
    toon_shared: bool
    toon_index: int           # texture index, or internal toon 0..9 if shared
    surface_count: int        # number of face-indices (= triangles*3)

    @property
    def has_edge(self) -> bool:
        return bool(self.flags & 0x10)

    @property
    def double_sided(self) -> bool:
        return bool(self.flags & 0x01)


@dataclass
class PmxMorph:
    name: str
    name_en: str
    panel: int                # 0 hidden,1 eyebrow,2 eye,3 mouth,4 other
    morph_type: int           # 0 group,1 vertex,2 bone,3-7 uv,8 material,9 flip,10 impulse
    offset_count: int


@dataclass
class PmxDisplayFrame:
    name: str
    name_en: str
    special: bool
    elements: List[Tuple[int, int]]   # (target 0=bone/1=morph, index)


@dataclass
class PmxRigidBody:
    name: str
    bone: int
    group: int
    shape: int                # 0 sphere,1 box,2 capsule
    mode: int                 # 0 static(bone),1 dynamic,2 dynamic+bone


@dataclass
class PmxJoint:
    name: str
    rb_a: int
    rb_b: int


@dataclass
class PmxModel:
    version: float = 2.0
    encoding: int = 0
    add_uv: int = 0
    name: str = ""
    name_en: str = ""
    vertex_count: int = 0
    face_count: int = 0       # triangles
    vmin: tuple = (0.0, 0.0, 0.0)   # vertex bounding box (PMX space, Y up)
    vmax: tuple = (0.0, 0.0, 0.0)
    textures: List[str] = field(default_factory=list)
    materials: List[PmxMaterial] = field(default_factory=list)
    bones: List[PmxBone] = field(default_factory=list)
    morphs: List[PmxMorph] = field(default_factory=list)
    display_frames: List[PmxDisplayFrame] = field(default_factory=list)
    rigid_bodies: List[PmxRigidBody] = field(default_factory=list)
    joints: List[PmxJoint] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "version": self.version,
            "name": self.name,
            "vertices": self.vertex_count,
            "faces": self.face_count,
            "textures": len(self.textures),
            "materials": len(self.materials),
            "bones": len(self.bones),
            "morphs": len(self.morphs),
            "display_frames": len(self.display_frames),
            "rigid_bodies": len(self.rigid_bodies),
            "joints": len(self.joints),
            "bones_with_ik": sum(1 for b in self.bones if b.has_ik),
            "bones_with_grant": sum(1 for b in self.bones if b.inherit_rotation or b.inherit_translation),
        }
