"""Build a Blender scene from a parsed XpsModel.

Applies the XPS->Blender transform EXACTLY ONCE:
  position/normal: (x, y, z) -> (x, -z, y)
  triangle winding: [0,1,2] -> [0,2,1]
  UV: v -> 1 - v   (u unchanged)

XPS vertex weights are reused as-is (no normalization, no splitting) per the
project's hard constraints (CLAUDE.md §1). Returns (armature_obj, [mesh_objs]).
"""
from __future__ import annotations

import os

import bpy  # type: ignore


def _build_material(mesh, tex_dir):
    name = (mesh.base_name or mesh.name or "mat")[:40]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    if mesh.textures and tex_dir:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        path = os.path.join(tex_dir, mesh.textures[0].file)
        if bsdf and os.path.exists(path):
            try:
                img = bpy.data.images.load(path, check_existing=True)
                tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
                tex.image = img
                links = mat.node_tree.links
                links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
                links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
                mat.blend_method = "HASHED"
            except Exception:  # noqa: BLE001
                pass
    return mat


def xps_to_blender(co):
    x, y, z = co
    return (x, -z, y)


_TAIL_EPS = 1e-4


def _ensure_object_mode():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def remove_model(name: str):
    """Delete a previously-built collection + its objects (idempotent re-runs)."""
    coll = bpy.data.collections.get(name)
    if not coll:
        return
    for ob in list(coll.objects):
        data = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        # purge orphan data
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)
        elif isinstance(data, bpy.types.Armature) and data.users == 0:
            bpy.data.armatures.remove(data)
    bpy.data.collections.remove(coll)


def _build_armature(xps, name, coll):
    arm_data = bpy.data.armatures.new(name + "_arm")
    arm_obj = bpy.data.objects.new(name + "_arm", arm_data)
    coll.objects.link(arm_obj)

    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    created = []  # actual edit-bone names (Blender may dedup duplicates)
    ebs = []
    for b in xps.bones:
        eb = arm_data.edit_bones.new(b.name)
        head = xps_to_blender(b.pos)
        eb.head = head
        eb.tail = (head[0], head[1], head[2] + 0.05)  # provisional; refined below
        created.append(eb.name)
        ebs.append(eb)

    # parent
    for i, b in enumerate(xps.bones):
        if 0 <= b.parent_id < len(ebs):
            ebs[i].parent = ebs[b.parent_id]

    # point each tail at its single child (nicer rig); keep >0 length
    children = {}
    for i, b in enumerate(xps.bones):
        if 0 <= b.parent_id < len(ebs):
            children.setdefault(b.parent_id, []).append(i)
    for i, eb in enumerate(ebs):
        kids = children.get(i, [])
        if len(kids) == 1:
            tail = ebs[kids[0]].head
            if (tail - eb.head).length > _TAIL_EPS:
                eb.tail = tail

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj, created


def _build_mesh(xps, mesh, bone_names, coll, arm_obj, tex_dir=None):
    me = bpy.data.meshes.new(mesh.name)
    ob = bpy.data.objects.new(mesh.name, me)
    coll.objects.link(ob)
    me.materials.append(_build_material(mesh, tex_dir))

    verts = [xps_to_blender(v.pos) for v in mesh.vertices]
    faces = [(f[0], f[2], f[1]) for f in mesh.faces]  # reverse winding
    me.from_pydata(verts, [], faces)
    me.update()

    # UVs (v -> 1-v), first layer
    if mesh.uv_layer_count > 0:
        uvl = me.uv_layers.new(name="UV")
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                u, v = mesh.vertices[vi].uvs[0]
                uvl.data[li].uv = (u, 1.0 - v)

    # custom split normals (per-vertex), Blender 3.6 API
    try:
        normals = [xps_to_blender(v.normal) for v in mesh.vertices]
        me.use_auto_smooth = True
        me.normals_split_custom_set_from_vertices(normals)
    except Exception:
        pass

    # vertex groups + weights — REUSE XPS weights verbatim
    vg_by_name = {}
    for vi, v in enumerate(mesh.vertices):
        for bidx, w in zip(v.bones, v.weights):
            if w <= 0.0 or bidx < 0 or bidx >= len(bone_names):
                continue
            bname = bone_names[bidx]
            vg = vg_by_name.get(bname)
            if vg is None:
                vg = ob.vertex_groups.new(name=bname)
                vg_by_name[bname] = vg
            vg.add([vi], float(w), "ADD")

    ob.parent = arm_obj
    mod = ob.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = arm_obj
    return ob


def build_model(xps, name="xps_model", tex_dir=None):
    """Import an XpsModel into a fresh collection. Returns (armature_obj, meshes)."""
    _ensure_object_mode()
    remove_model(name)

    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)

    arm_obj, bone_names = _build_armature(xps, name, coll)
    meshes = [_build_mesh(xps, m, bone_names, coll, arm_obj, tex_dir) for m in xps.meshes]
    return arm_obj, meshes
