import bpy, os, math
from mathutils import Vector

# clean up leftovers from prior test runs (user restarted Blender; these are ours)
for o in list(bpy.data.objects):
    if o.name.startswith(("Out", "rcam", "rl", "inase", "New MMD", "_x2m")):
        try:
            bpy.data.objects.remove(o, do_unlink=True)
        except Exception:
            pass

PMX = r"E:\_x2m_dev\out.pmx"
VMD = r"E:\mywork\mymodel\yaoxiang\yaoxiang.vmd"
OUT = r"E:\_x2m_dev\pose.png"

print("STEP import_model")
before = set(o.name for o in bpy.data.objects)
bpy.ops.mmd_tools.import_model(filepath=PMX, scale=0.08, clean_model=False)
new = [o for o in bpy.data.objects if o.name not in before]
arm = [o for o in new if o.type == "ARMATURE"][0]

print("STEP import_vmd")
bpy.ops.object.select_all(action="DESELECT")
for o in new:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.mmd_tools.import_vmd(filepath=VMD)

sc = bpy.context.scene
fr = int((sc.frame_start + sc.frame_end) / 2)
sc.frame_set(fr)
print("STEP posed at frame", fr)

# bounding box of the posed meshes
deg = bpy.context.evaluated_depsgraph_get()
mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
for o in new:
    if o.type == "MESH":
        oe = o.evaluated_get(deg)
        for c in oe.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
center = (mn + mx) / 2
size = mx - mn
dist = max(size.x, size.z) * 2.4 + 0.5

cam_d = bpy.data.cameras.new("rcam"); cam = bpy.data.objects.new("rcam", cam_d)
sc.collection.objects.link(cam)
cam.location = center + Vector((0, -dist, 0))
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.camera = cam

ld = bpy.data.lights.new("rl", type="SUN"); lt = bpy.data.objects.new("rl", ld)
sc.collection.objects.link(lt); lt.rotation_euler = (math.radians(55), 0, math.radians(25))
ld.energy = 3.0

try:
    sc.render.engine = "BLENDER_EEVEE"
except Exception:
    pass
sc.render.resolution_x = 460
sc.render.resolution_y = 760
sc.render.film_transparent = False
sc.render.filepath = OUT
sc.render.image_settings.file_format = "PNG"
print("STEP render")
bpy.ops.render.render(write_still=True)
print("DONE exists", os.path.exists(OUT), "size", os.path.getsize(OUT) if os.path.exists(OUT) else -1)
