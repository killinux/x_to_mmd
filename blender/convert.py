"""XPS->MMD conversion pipeline (bpy). Applies the bone-map plan with weight
safety, then (later steps) completes MMD bones, sets grants/IK, and drives
mmd_tools to export PMX.

Hard constraints (CLAUDE.md): reuse XPS weights, merge = ADD (never split),
weight-integrity checked around bone completion.
"""
from __future__ import annotations

from . import weights as W


def apply_bone_plan(arm_obj, plans, source_names):
    """plans: list of core.bonemap.BonePlan. source_names[i] = original bone name.

    Returns a report dict (counts + any weight-integrity issues).
    """
    meshes = W.deform_meshes(arm_obj)
    snap0 = W.weight_snapshot(meshes)

    # 1) merge junk/twist bones: ADD their weights into the target's CURRENT name
    merged_names = []
    for p in plans:
        if p.action == "merge" and p.merge_into is not None:
            src = source_names[p.index]
            dst = source_names[p.merge_into]
            W.merge_weights(meshes, src, dst)
            merged_names.append(src)

    # 2) delete the now-weightless merged bones (reparent children to survivors)
    W.delete_bones(arm_obj, merged_names, reparent=True)

    # 3) atomic rename survivors to MMD names
    renames = {source_names[p.index]: p.mmd_name
               for p in plans if p.action == "rename"}
    W.atomic_rename(arm_obj, meshes, renames)

    # control bones must carry NO skin weight (CLAUDE.md §1); absorb any into real bones
    cleared = W.clear_control_weights(
        arm_obj, meshes, ["全ての親", "センター", "グルーブ", "腰", "操作中心"], fallback="下半身")

    snap1 = W.weight_snapshot(meshes)
    issues = W.weight_integrity_check(snap0, snap1)

    return {
        "renamed": len(renames),
        "merged": len(merged_names),
        "kept": sum(1 for p in plans if p.action == "keep"),
        "control_weight_cleared": cleared,
        "bones_after": len(arm_obj.data.bones),
        "weight_issues": issues,
    }


def fit_scale(meshes, target_height):
    """Export scale that makes the model exactly `target_height` tall (PMX units)."""
    zmin, zmax = float("inf"), float("-inf")
    for o in meshes:
        mw = o.matrix_world
        for v in o.data.vertices:
            z = (mw @ v.co).z
            if z < zmin:
                zmin = z
            if z > zmax:
                zmax = z
    h = zmax - zmin
    return (target_height / h) if h > 1e-6 else 12.5


def set_mmd_materials(arm_obj):
    """Match the reference's material flags: double-sided, no edge, shared toon 0."""
    n = 0
    for ob in W.deform_meshes(arm_obj):
        for slot in ob.material_slots:
            mat = slot.material
            mm = getattr(mat, "mmd_material", None) if mat else None
            if mm is None:
                continue
            mm.is_double_sided = True
            mm.enabled_toon_edge = False
            try:
                mm.is_shared_toon_texture = True
                mm.shared_toon_texture = 0
            except Exception:  # noqa: BLE001
                pass
            n += 1
    return n


def mmd_convert_and_export(arm_obj, filepath, scale=12.5):
    """Wrap the armature into an mmd_tools model and export PMX. Returns a report."""
    import bpy  # type: ignore

    if arm_obj.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)

    try:
        bpy.ops.mmd_tools.convert_to_mmd_model(convert_material_nodes=False)
    except TypeError:
        bpy.ops.mmd_tools.convert_to_mmd_model()
    except Exception as e:  # noqa: BLE001
        return {"error": f"convert_to_mmd_model failed: {e!r}"}

    # locate the MMD ROOT empty
    root = None
    try:
        from mmd_tools.core.model import FnModel  # type: ignore
        root = FnModel.find_root_object(arm_obj)
    except Exception:  # noqa: BLE001
        o = arm_obj
        while o is not None and getattr(o, "mmd_type", "NONE") != "ROOT":
            o = o.parent
        root = o or arm_obj

    set_mmd_materials(arm_obj)

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = root
    root.select_set(True)

    # generate _dummy_/_shadow_ helper bones from the mmd_bone 付与 metadata
    try:
        bpy.ops.mmd_tools.apply_additional_transform()
    except Exception:  # noqa: BLE001
        pass

    try:
        bpy.ops.mmd_tools.export_pmx(filepath=filepath, scale=scale, copy_textures=True)
    except TypeError:
        try:
            bpy.ops.mmd_tools.export_pmx(filepath=filepath, scale=scale,
                                         copy_textures_mode="OVERWRITE")
        except TypeError:
            bpy.ops.mmd_tools.export_pmx(filepath=filepath, scale=scale)
    return {"root": getattr(root, "name", "?"), "exported": filepath}

