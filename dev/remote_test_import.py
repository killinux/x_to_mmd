# Runs ON the remote Blender (sent via dev/blender_rpc.py --file).
# Extracts the freshly-uploaded package, imports it, builds the model, validates.
import sys, os, zipfile, shutil

DEV = r"E:\_x2m_dev"
PKG = os.path.join(DEV, "pkg")
XPS = r"E:\mywork\mymodel\inase (purifier)_lezisell-A\xps-b.xps"

# resolve uploaded zip (cli.py upload may nest it as ...\x2m.zip\x2m.zip)
ZIP = os.path.join(DEV, "x2m.zip")
if os.path.isdir(ZIP):
    ZIP = os.path.join(ZIP, "x2m.zip")

# fresh extract
if os.path.isdir(PKG):
    shutil.rmtree(PKG, ignore_errors=True)
os.makedirs(PKG, exist_ok=True)
with zipfile.ZipFile(ZIP) as z:
    z.extractall(PKG)
if PKG not in sys.path:
    sys.path.insert(0, PKG)

# drop any cached copies so edits take effect
for k in [k for k in sys.modules if k == "core" or k.startswith("core.") or k == "blender" or k.startswith("blender.")]:
    del sys.modules[k]

from core.xps import read_xps_model
from blender import importer as imp
import bpy

xps = read_xps_model(XPS)
arm, meshes = imp.build_model(xps, "inase_test")

nb = len(arm.data.bones)
nv = sum(len(o.data.vertices) for o in meshes)
nf = sum(len(o.data.polygons) for o in meshes)
print("RESULT_BEGIN")
print("source_bones", len(xps.bones), "source_verts", xps.total_vertices, "source_faces", xps.total_faces)
print("blender_bones", nb, "blender_meshes", len(meshes), "blender_verts", nv, "blender_polys", nf)

# sample weight check: mesh0 vertex0 should follow XPS bone idx 15 ("spine upper") w=1.0
o = meshes[0]
v0 = o.data.vertices[0]
groups0 = sorted(((o.vertex_groups[g.group].name, round(g.weight, 4)) for g in v0.groups),
                 key=lambda t: -t[1])
print("v0_co", tuple(round(c, 5) for c in v0.co))
print("v0_weights", groups0)
print("xps_v0_bones", xps.meshes[0].vertices[0].bones, "weights", xps.meshes[0].vertices[0].weights)
print("xps_bone15_name", xps.bones[15].name)
print("RESULT_END")
