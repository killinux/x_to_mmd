import bpy
from mathutils import Vector

arms = [o for o in bpy.data.objects if o.type == "ARMATURE"
        and o.animation_data and o.animation_data.action]
arm = arms[-1]
pb = arm.pose.bones
meshes = [o for o in bpy.data.objects if o.type == "MESH"
          and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]

sc = bpy.context.scene
sc.frame_set(int((sc.frame_start + sc.frame_end) / 2))
deg = bpy.context.evaluated_depsgraph_get()

ref = arm.matrix_world @ (pb["上半身"].head if "上半身" in pb else Vector((0, 0, 0)))

print("RESULT_BEGIN")
print("armature", arm.name, "meshes", len(meshes))

# find the 5 farthest evaluated vertices and their groups
worst = []
for o in meshes:
    oe = o.evaluated_get(deg)
    mw = o.matrix_world
    vs = oe.data.vertices
    for v in vs:
        d = (mw @ v.co - ref).length
        if d > 3.0:                       # body is ~1.7 units tall; >3 is a spike
            worst.append((d, o.name, v.index))
worst.sort(reverse=True)
print("spike_verts (>3 units from chest):", len(worst))

seen_groups = {}
for d, oname, vi in worst[:300]:
    o = bpy.data.objects[oname]
    for g in o.data.vertices[vi].groups:
        if g.weight > 0.0:
            nm = o.vertex_groups[g.group].name
            seen_groups[nm] = seen_groups.get(nm, 0) + 1

print("groups on spike verts (bone -> #verts):")
for nm, c in sorted(seen_groups.items(), key=lambda t: -t[1]):
    bp = pb.get(nm)
    posed = (arm.matrix_world @ bp.head) if bp else None
    rest = (arm.matrix_world @ arm.data.bones[nm].head_local) if nm in arm.data.bones else None
    print("  %-22s spikeverts=%d posedhead=%s resthead=%s" % (
        nm, c,
        tuple(round(x, 2) for x in posed) if posed else None,
        tuple(round(x, 2) for x in rest) if rest else None))
print("RESULT_END")
