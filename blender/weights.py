"""Weight-safe transfer module (bpy) — the bedrock per CLAUDE.md §1/§2.

Guarantees:
  * rename carries weights atomically (mesh vertex-group renamed/merged FIRST,
    then the bone, then a depsgraph refresh);
  * merge = ADD source weights into the target group, never a split;
  * weight_integrity_check flags any total-weight loss or new zero-weight verts.

NEVER splits weights. Splitting requires explicit user confirmation (CLAUDE.md).
"""
from __future__ import annotations

import bpy  # type: ignore


def deform_meshes(arm_obj):
    out = []
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        if any(m.type == "ARMATURE" and m.object == arm_obj for m in ob.modifiers):
            out.append(ob)
    return out


# ---------------------------------------------------------------------------
# integrity
# ---------------------------------------------------------------------------
def weight_snapshot(meshes):
    snap = {}
    for ob in meshes:
        names = [vg.name for vg in ob.vertex_groups]
        per_group = {}
        zero = 0
        for v in ob.data.vertices:
            s = 0.0
            for g in v.groups:
                if g.weight > 0:
                    per_group[names[g.group]] = per_group.get(names[g.group], 0.0) + g.weight
                    s += g.weight
            if s <= 1e-6:
                zero += 1
        snap[ob.name] = {"total": sum(per_group.values()), "groups": per_group,
                         "zero": zero, "nverts": len(ob.data.vertices)}
    return snap


def weight_integrity_check(before, after, tol=1.0):
    issues = []
    for name, b in before.items():
        a = after.get(name)
        if a is None:
            issues.append(f"{name}: mesh missing after")
            continue
        if abs(a["total"] - b["total"]) > tol:
            issues.append(f"{name}: total weight {b['total']:.1f} -> {a['total']:.1f}")
        if a["zero"] > b["zero"]:
            issues.append(f"{name}: zero-weight verts {b['zero']} -> {a['zero']}")
    return issues


# ---------------------------------------------------------------------------
# vertex-group ops (object mode)
# ---------------------------------------------------------------------------
def _merge_vgroup(ob, src_name, dst_name):
    vg_src = ob.vertex_groups.get(src_name)
    if vg_src is None:
        return
    si = vg_src.index
    payload = []
    for v in ob.data.vertices:
        for g in v.groups:
            if g.group == si and g.weight > 0:
                payload.append((v.index, g.weight))
                break
    vg_dst = ob.vertex_groups.get(dst_name) or ob.vertex_groups.new(name=dst_name)
    for vi, w in payload:
        vg_dst.add([vi], w, "ADD")
    ob.vertex_groups.remove(vg_src)


def merge_weights(meshes, src_name, dst_name):
    for ob in meshes:
        _merge_vgroup(ob, src_name, dst_name)


def atomic_rename(arm_obj, meshes, renames):
    """renames: {old_bone_name: new_name}. Mesh groups first, then bones."""
    for ob in meshes:
        for old, new in renames.items():
            vg_old = ob.vertex_groups.get(old)
            if vg_old is None:
                continue
            if ob.vertex_groups.get(new) is not None:
                _merge_vgroup(ob, old, new)   # destination exists -> merge to avoid dup
            else:
                vg_old.name = new
    arm = arm_obj.data
    for old, new in renames.items():
        b = arm.bones.get(old)
        if b is not None and old != new:
            b.name = new
    arm_obj.data.update_tag()
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------
# bone deletion (edit mode, batched)
# ---------------------------------------------------------------------------
def clear_control_weights(arm_obj, meshes, control_names, fallback="下半身"):
    """Control bones (全ての親/センター/…) MUST be empty-weight (CLAUDE.md §1).

    Any skin weight a control bone inherited from the source (e.g. 'root ground')
    is removed and absorbed by the vertex's OTHER (real deform) bones, renormalized
    so each vertex's total weight is conserved — fixes the 'stays at origin while the
    body moves' spike. This enforces the constraint; it is not an aesthetic split.
    """
    cleared = 0
    for ob in meshes:
        ctrl_idx = {ob.vertex_groups[n].index for n in control_names if ob.vertex_groups.get(n)}
        if not ctrl_idx:
            continue
        fb = ob.vertex_groups.get(fallback) or ob.vertex_groups.new(name=fallback)
        ctrl_groups = [ob.vertex_groups[n] for n in control_names if ob.vertex_groups.get(n)]
        for v in ob.data.vertices:
            ctrl_w = sum(g.weight for g in v.groups if g.group in ctrl_idx and g.weight > 0)
            if ctrl_w <= 0:
                continue
            others = [(g.group, g.weight) for g in v.groups
                      if g.group not in ctrl_idx and g.weight > 0]
            other_sum = sum(w for _, w in others)
            total = ctrl_w + other_sum
            if other_sum > 1e-6:
                factor = total / other_sum   # absorb ctrl weight, conserve vertex total
                for gi, w in others:
                    ob.vertex_groups[gi].add([v.index], w * factor, "REPLACE")
            else:
                fb.add([v.index], total, "REPLACE")   # control-only vertex -> fallback bone
            for vg in ctrl_groups:
                vg.remove([v.index])
            cleared += 1
    return cleared


def delete_bones(arm_obj, names, reparent=True):
    if not names:
        return
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_obj.data.edit_bones
    for name in names:
        b = eb.get(name)
        if b is None:
            continue
        if reparent:
            for c in list(b.children):
                c.parent = b.parent
        eb.remove(b)
    bpy.ops.object.mode_set(mode="OBJECT")
