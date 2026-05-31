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

from blender import pipeline
import bpy

XPS = r"E:\mywork\mymodel\inase (purifier)_lezisell-A\xps-b.xps"
OUT = r"E:\_x2m_dev\out.pmx"

arm, meshes, report = pipeline.run(XPS, name="inase_test", export_path=OUT, fit_height=20.836)

print("RESULT_BEGIN")
print("report", json.dumps(report, ensure_ascii=False))
print("out_exists", os.path.exists(OUT), "size", os.path.getsize(OUT) if os.path.exists(OUT) else -1)
print("RESULT_END")
