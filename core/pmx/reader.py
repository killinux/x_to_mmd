"""PMX 2.0/2.1 binary reader (bpy-independent).

Parses the full section chain so the cursor stays in sync; surfaces a structural
model (counts + bones/materials/morphs/frames/physics) for diffing against a
reference PMX. Little-endian; text is UTF-16LE or UTF-8 per the globals header.
"""
from __future__ import annotations

import io
import struct

from .types import (
    PmxBone,
    PmxDisplayFrame,
    PmxJoint,
    PmxMaterial,
    PmxModel,
    PmxMorph,
    PmxRigidBody,
)


class _R:
    def __init__(self, data: bytes):
        self._io = io.BytesIO(data)
        self.encoding = "utf-16-le"
        self.add_uv = 0
        self.sz = {}  # index sizes

    def read(self, n):
        b = self._io.read(n)
        if len(b) != n:
            raise EOFError(f"short read {len(b)}/{n} at {self._io.tell()}")
        return b

    def byte(self):
        return self.read(1)[0]

    def i8(self):
        return struct.unpack("<b", self.read(1))[0]

    def u16(self):
        return struct.unpack("<H", self.read(2))[0]

    def i32(self):
        return struct.unpack("<i", self.read(4))[0]

    def f(self):
        return struct.unpack("<f", self.read(4))[0]

    def vec(self, n):
        return struct.unpack("<%df" % n, self.read(4 * n))

    def text(self):
        n = self.i32()
        return self.read(n).decode(self.encoding, errors="replace")

    def idx(self, kind):
        """Signed index for bone/texture/material/morph/rigidbody (-1 = none)."""
        size = self.sz[kind]
        if size == 1:
            return struct.unpack("<b", self.read(1))[0]
        if size == 2:
            return struct.unpack("<h", self.read(2))[0]
        return struct.unpack("<i", self.read(4))[0]

    def vidx(self):
        """Unsigned vertex index."""
        size = self.sz["vertex"]
        if size == 1:
            return self.read(1)[0]
        if size == 2:
            return struct.unpack("<H", self.read(2))[0]
        return struct.unpack("<i", self.read(4))[0]


def read_pmx(path_or_bytes) -> PmxModel:
    if isinstance(path_or_bytes, (bytes, bytearray)):
        data = bytes(path_or_bytes)
    else:
        with open(path_or_bytes, "rb") as fh:
            data = fh.read()

    r = _R(data)
    sig = r.read(4)
    if sig != b"PMX ":
        raise ValueError(f"not a PMX file (sig={sig!r})")
    version = round(r.f(), 4)
    g_count = r.byte()
    globals_ = r.read(g_count)
    encoding, add_uv = globals_[0], globals_[1]
    r.encoding = "utf-16-le" if encoding == 0 else "utf-8"
    r.add_uv = add_uv
    r.sz = {
        "vertex": globals_[2], "texture": globals_[3], "material": globals_[4],
        "bone": globals_[5], "morph": globals_[6], "rigidbody": globals_[7],
    }

    m = PmxModel(version=version, encoding=encoding, add_uv=add_uv)
    m.name = r.text(); m.name_en = r.text()
    _comment = r.text(); _comment_en = r.text()

    # --- vertices ---
    vcount = r.i32()
    m.vertex_count = vcount
    inf = float("inf")
    mn = [inf, inf, inf]
    mx = [-inf, -inf, -inf]
    for _ in range(vcount):
        px, py, pz = r.vec(3)                     # position
        if px < mn[0]: mn[0] = px
        if py < mn[1]: mn[1] = py
        if pz < mn[2]: mn[2] = pz
        if px > mx[0]: mx[0] = px
        if py > mx[1]: mx[1] = py
        if pz > mx[2]: mx[2] = pz
        r.vec(3); r.vec(2)                         # normal, uv
        for _ in range(add_uv):
            r.vec(4)
        wt = r.byte()
        if wt == 0:                               # BDEF1
            r.idx("bone")
        elif wt == 1:                             # BDEF2
            r.idx("bone"); r.idx("bone"); r.f()
        elif wt == 2:                             # BDEF4
            for _ in range(4):
                r.idx("bone")
            r.vec(4)
        elif wt == 3:                             # SDEF
            r.idx("bone"); r.idx("bone"); r.f(); r.vec(3); r.vec(3); r.vec(3)
        elif wt == 4:                             # QDEF (2.1)
            for _ in range(4):
                r.idx("bone")
            r.vec(4)
        else:
            raise ValueError(f"unknown weight deform type {wt}")
        r.f()                                     # edge scale

    if vcount:
        m.vmin = tuple(mn)
        m.vmax = tuple(mx)

    # --- faces ---
    icount = r.i32()
    m.face_count = icount // 3
    for _ in range(icount):
        r.vidx()

    # --- textures ---
    tcount = r.i32()
    m.textures = [r.text() for _ in range(tcount)]

    # --- materials ---
    mcount = r.i32()
    for _ in range(mcount):
        name = r.text(); name_en = r.text()
        diffuse = r.vec(4); specular = r.vec(3); spec_str = r.f(); ambient = r.vec(3)
        flags = r.byte()
        edge_color = r.vec(4); edge_size = r.f()
        tex_i = r.idx("texture"); sph_i = r.idx("texture"); sph_mode = r.byte()
        toon_shared = r.byte() == 1
        toon_i = r.byte() if toon_shared else r.idx("texture")
        _memo = r.text()
        surface = r.i32()
        m.materials.append(PmxMaterial(
            name=name, name_en=name_en, diffuse=diffuse, specular=specular,
            specular_strength=spec_str, ambient=ambient, flags=flags,
            edge_color=edge_color, edge_size=edge_size, texture_index=tex_i,
            sphere_index=sph_i, sphere_mode=sph_mode, toon_shared=toon_shared,
            toon_index=toon_i, surface_count=surface))

    # --- bones ---
    bcount = r.i32()
    for _ in range(bcount):
        name = r.text(); name_en = r.text()
        pos = r.vec(3)
        parent = r.idx("bone")
        layer = r.i32()
        flags = r.u16()
        tail_is_bone = bool(flags & 0x0001)
        tail = r.idx("bone") if tail_is_bone else r.vec(3)
        inherit_rot = bool(flags & 0x0100)
        inherit_tr = bool(flags & 0x0200)
        grant_parent, grant_weight = -1, 0.0
        if inherit_rot or inherit_tr:
            grant_parent = r.idx("bone"); grant_weight = r.f()
        if flags & 0x0400:                        # fixed axis
            r.vec(3)
        if flags & 0x0800:                        # local coord
            r.vec(3); r.vec(3)
        if flags & 0x2000:                        # external parent
            r.i32()
        has_ik = bool(flags & 0x0020)
        ik_target, ik_links = -1, []
        if has_ik:
            ik_target = r.idx("bone")
            r.i32()                               # loop count
            r.f()                                 # limit angle
            link_count = r.i32()
            for _ in range(link_count):
                lb = r.idx("bone")
                ik_links.append(lb)
                if r.byte() == 1:                 # has angle limit
                    r.vec(3); r.vec(3)
        m.bones.append(PmxBone(
            name=name, name_en=name_en, parent=parent, position=pos, layer=layer,
            flags=flags, tail_is_bone=tail_is_bone, tail=tail,
            inherit_rotation=inherit_rot, inherit_translation=inherit_tr,
            grant_parent=grant_parent, grant_weight=grant_weight, transform_order=layer,
            has_ik=has_ik, ik_target=ik_target, ik_links=ik_links))

    # --- morphs ---
    mocount = r.i32()
    for _ in range(mocount):
        name = r.text(); name_en = r.text()
        panel = r.byte(); mtype = r.byte()
        ocount = r.i32()
        for _ in range(ocount):
            _skip_morph_offset(r, mtype)
        m.morphs.append(PmxMorph(name=name, name_en=name_en, panel=panel,
                                 morph_type=mtype, offset_count=ocount))

    # --- display frames ---
    dcount = r.i32()
    for _ in range(dcount):
        name = r.text(); name_en = r.text()
        special = r.byte() == 1
        ecount = r.i32()
        elems = []
        for _ in range(ecount):
            target = r.byte()
            ei = r.idx("morph") if target == 1 else r.idx("bone")
            elems.append((target, ei))
        m.display_frames.append(PmxDisplayFrame(name=name, name_en=name_en,
                                                special=special, elements=elems))

    # --- rigid bodies ---
    rcount = r.i32()
    for _ in range(rcount):
        name = r.text(); _en = r.text()
        bone = r.idx("bone")
        group = r.byte(); r.u16()                 # group, non-collision mask
        shape = r.byte(); r.vec(3); r.vec(3); r.vec(3)  # shape,size,pos,rot
        r.f(); r.f(); r.f(); r.f(); r.f()         # mass, damps, restitution, friction
        mode = r.byte()
        m.rigid_bodies.append(PmxRigidBody(name=name, bone=bone, group=group,
                                           shape=shape, mode=mode))

    # --- joints ---
    jcount = r.i32()
    for _ in range(jcount):
        name = r.text(); _en = r.text()
        _jtype = r.byte()
        rb_a = r.idx("rigidbody"); rb_b = r.idx("rigidbody")
        r.vec(3); r.vec(3)                        # pos, rot
        r.vec(3); r.vec(3); r.vec(3); r.vec(3)    # pos/rot limits
        r.vec(3); r.vec(3)                        # spring pos/rot
        m.joints.append(PmxJoint(name=name, rb_a=rb_a, rb_b=rb_b))

    return m


def _skip_morph_offset(r: _R, mtype: int):
    if mtype == 0 or mtype == 9:                  # group / flip
        r.idx("morph"); r.f()
    elif mtype == 1:                              # vertex
        r.vidx(); r.vec(3)
    elif mtype == 2:                              # bone
        r.idx("bone"); r.vec(3); r.vec(4)
    elif 3 <= mtype <= 7:                         # uv / uv1-4
        r.vidx(); r.vec(4)
    elif mtype == 8:                              # material
        r.idx("material"); r.byte()
        r.vec(4); r.vec(3); r.f(); r.vec(3); r.vec(4); r.f()  # diffuse..edge
        r.vec(4); r.vec(4); r.vec(4)              # texture/sphere/toon tints
    elif mtype == 10:                             # impulse (2.1)
        r.idx("rigidbody"); r.byte(); r.vec(3); r.vec(3)
    else:
        raise ValueError(f"unknown morph type {mtype}")
