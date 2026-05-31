import bpy, os

PMX = r"E:\_x2m_dev\out.pmx"
VMD = r"E:\mywork\mymodel\yaoxiang\yaoxiang.vmd"

print("RESULT_BEGIN")
print("pmx_exists", os.path.exists(PMX), "vmd_exists", os.path.exists(VMD))

before = set(o.name for o in bpy.data.objects)
try:
    bpy.ops.mmd_tools.import_model(filepath=PMX, scale=0.08, clean_model=False)
except TypeError:
    bpy.ops.mmd_tools.import_model(filepath=PMX, scale=0.08)

new = [o for o in bpy.data.objects if o.name not in before]
arms = [o for o in new if o.type == "ARMATURE"]
arm = arms[0] if arms else None
print("imported_new_objs", len(new), "armature", arm.name if arm else None)
print("imported_bones", len(arm.data.bones) if arm else 0)

bpy.ops.object.select_all(action="DESELECT")
for o in new:
    try:
        o.select_set(True)
    except Exception:
        pass
if arm:
    bpy.context.view_layer.objects.active = arm

try:
    bpy.ops.mmd_tools.import_vmd(filepath=VMD)
    print("vmd_imported", True)
except Exception as e:  # noqa: BLE001
    print("vmd_error", repr(e))

nfc = 0
animated_bones = set()
if arm and arm.animation_data and arm.animation_data.action:
    fcs = arm.animation_data.action.fcurves
    nfc = len(fcs)
    for fc in fcs:
        dp = fc.data_path
        if dp.startswith('pose.bones["'):
            animated_bones.add(dp.split('"')[1])
print("armature_fcurves", nfc, "animated_bone_tracks", len(animated_bones))

# how many animated bones actually exist in the model (= VMD matched our names)
if arm:
    have = set(b.name for b in arm.data.bones)
    matched = animated_bones & have
    print("vmd_bones_matched", len(matched), "of", len(animated_bones))
    print("sample_matched", sorted(matched)[:25])
    print("sample_unmatched", sorted(animated_bones - have)[:15])

sc = bpy.context.scene
mid = int((sc.frame_start + sc.frame_end) / 2) or 60
sc.frame_set(mid)
print("frame_range", sc.frame_start, sc.frame_end, "set_to", mid)
print("RESULT_END")
