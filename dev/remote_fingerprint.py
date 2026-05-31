import sys, json

PATH = r"E:\mywork\mymodel\inase (purifier)_lezisell-A\xps-b.xps"
rbx = sys.modules[[k for k in sys.modules if k.split(".")[-1] == "read_bin_xps"][0]]
d = rbx.readXpsModel(PATH)


def vtx(v):
    return dict(
        co=[round(x, 5) for x in v.co],
        norm=[round(x, 5) for x in v.norm],
        color=list(v.vColor),
        uv=[[round(x, 5) for x in u] for u in v.uv],
        bones=[bw.id for bw in v.boneWeights],
        weights=[round(bw.weight, 5) for bw in v.boneWeights],
    )


out = dict(
    parents=[b.parentId for b in d.bones],
    bone_pos5=[[round(x, 5) for x in b.co] for b in d.bones[:5]],
    m0_name=d.meshes[0].name,
    m0_v0=vtx(d.meshes[0].vertices[0]),
    m0_vlast=vtx(d.meshes[0].vertices[-1]),
    m0_f0=list(d.meshes[0].faces[0]),
    m0_flast=list(d.meshes[0].faces[-1]),
    m7_v0=vtx(d.meshes[7].vertices[0]),
)
print("FP_BEGIN")
print(json.dumps(out))
print("FP_END")
