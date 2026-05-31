import sys, os, zipfile, shutil, json

DEV = r"E:\_x2m_dev"
PKG = os.path.join(DEV, "pkg")
ZIP = os.path.join(DEV, "x2m.zip")
if os.path.isdir(ZIP):
    ZIP = os.path.join(ZIP, "x2m.zip")
if os.path.isdir(PKG):
    shutil.rmtree(PKG, ignore_errors=True)
os.makedirs(PKG, exist_ok=True)
with zipfile.ZipFile(ZIP) as z:
    z.extractall(PKG)
if PKG not in sys.path:
    sys.path.insert(0, PKG)
for k in [k for k in sys.modules if k == "core" or k.startswith("core.") or k == "blender" or k.startswith("blender.")]:
    del sys.modules[k]

from core.xps import read_xps_model
from core.bonemap import resolve
from blender import importer as imp, convert as cv
import bpy

XPS = r"E:\mywork\mymodel\inase (purifier)_lezisell-A\xps-b.xps"
xps = read_xps_model(XPS)
arm, meshes = imp.build_model(xps, "inase_test")
plans = resolve(xps)
report = cv.apply_bone_plan(arm, plans, [b.name for b in xps.bones])

print("RESULT_BEGIN")
print("report", json.dumps(report, ensure_ascii=False))
names = set(b.name for b in arm.data.bones)
need = ["全ての親", "センター", "下半身", "上半身", "上半身2", "上半身3",
        "左足", "右ひざ", "左足首", "右つま先", "左肩", "左腕", "左ひじ", "左手首",
        "左親指０", "左人指１", "頭", "首", "左目", "右目", "左胸", "右胸"]
print("missing", [n for n in need if n not in names])
# elbow should now carry forearm weight (merged from foretwist)
o = meshes[0]
print("RESULT_END")
