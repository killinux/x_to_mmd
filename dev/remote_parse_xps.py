import sys, os

PATH = r"E:\mywork\mymodel\inase (purifier)_lezisell-A\xps-b.xps"
print("file exists:", os.path.exists(PATH), "size:", os.path.getsize(PATH) if os.path.exists(PATH) else -1)

# Find the already-loaded johnzero7 read_bin_xps module (addon name has a hyphen).
cands = [k for k in sys.modules if k.split(".")[-1] == "read_bin_xps"]
print("read_bin_xps module candidates:", cands)
rbx = sys.modules[cands[0]]

data = rbx.readXpsModel(PATH)

hdr = data.header
print("RESULT_BEGIN")
print("HEADER:", (hdr.version_mayor, hdr.version_minor) if hdr else None)
print("BONES:", len(data.bones))
print("MESHES:", len(data.meshes))
print("VERTS:", sum(len(m.vertices) for m in data.meshes))
print("FACES:", sum(len(m.faces) for m in data.meshes))
print("BONE_NAMES_HEAD:", [b.name for b in data.bones[:40]])
print("MESH_NAMES_HEAD:", [m.name for m in data.meshes[:12]])
print("RESULT_END")
