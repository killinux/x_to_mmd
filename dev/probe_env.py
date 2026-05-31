import bpy, addon_utils, sys, importlib.util

print("blender:", bpy.app.version_string, "| python:", sys.version.split()[0])

# Addons of interest to this project
of_interest = [
    "mmd_tools", "MMD-Blender", "blender_mmd_tools",
    "XNALaraMesh", "xps_tools", "io_scene_xps", "io_xnalara",
    "cats-blender-plugin", "Cats", "tuxedo",
]
print("\n-- addons of interest --")
for name in of_interest:
    try:
        _, state = addon_utils.check(name)
        print(f"  {name:24s} enabled={state}")
    except Exception as e:
        print(f"  {name:24s} err={e}")

# Can we import mmd_tools (any module path)?
print("\n-- import probes --")
for mod in ("mmd_tools", "mmd_tools.core.pmx.exporter", "mmd_tools.core.model"):
    spec = importlib.util.find_spec(mod) if "." not in mod else None
    try:
        __import__(mod)
        print(f"  import {mod}: OK")
    except Exception as e:
        print(f"  import {mod}: FAIL ({type(e).__name__}: {e})")

# All currently-enabled addons
enabled = sorted(m.__name__ for m in addon_utils.modules() if addon_utils.check(m.__name__)[1])
print("\n-- all enabled addons --")
print("  " + ", ".join(enabled))

# Capability flags that differ across Blender versions (3.6 vs 4.x)
print("\n-- API capability flags (3.6 vs 4.x) --")
me = bpy.data.meshes.new("_probe_tmp")
print("  mesh.use_auto_smooth attr:", hasattr(me, "use_auto_smooth"))          # 3.6 True, 4.1+ False
print("  mesh.create_normals_split:", hasattr(me, "create_normals_split"))      # 3.6 True
print("  armature has .collections (4.0+):", hasattr(bpy.types.Armature, "collections"))
print("  pose has bone_groups (<=3.6):", hasattr(bpy.types.Pose, "bone_groups"))
bpy.data.meshes.remove(me)
