from mmd_tools.core.pmx import load

PATH = r"E:\mywork\mymodel\Purifier Inase 18\Purifier Inase 18 None.pmx"
p = load(PATH)
print("MMDTOOLS_PMX_COUNTS_BEGIN")
for a in ["vertices", "faces", "textures", "materials", "bones", "morphs", "display", "rigids", "joints"]:
    v = getattr(p, a, None)
    print(a, len(v) if v is not None else "N/A")
print("model_name", repr(getattr(p, "name", "")))
print("MMDTOOLS_PMX_COUNTS_END")
