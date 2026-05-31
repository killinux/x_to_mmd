"""One-call XPS->MMD orchestration (bpy). Works both as an add-on submodule
(relative imports) and when the package dirs are on sys.path directly (dev tests)."""
from __future__ import annotations

import os

try:                       # add-on context: x_to_mmd.blender.pipeline
    from ..core.xps import read_xps_model
    from ..core.bonemap import resolve
    from . import complete, convert, importer
except ImportError:        # dev context: core/ and blender/ on sys.path
    from core.xps import read_xps_model
    from core.bonemap import resolve
    from blender import complete, convert, importer


def run(filepath, name="xps_mmd", export_path="", fit_height=0.0):
    """Import an XPS file, convert toward MMD (rig + IK + weight-safe rename),
    optionally export PMX. Returns (armature, meshes, report)."""
    xps = read_xps_model(filepath)
    arm, meshes = importer.build_model(xps, name, tex_dir=os.path.dirname(filepath))

    report = {
        "source": xps.summary()["bones"],
        "apply": convert.apply_bone_plan(arm, resolve(xps), [b.name for b in xps.bones]),
        "rig": complete.add_mmd_rig(arm),
        "ik": complete.add_leg_ik(arm),
    }
    if export_path:
        scale = convert.fit_scale(meshes, fit_height) if fit_height > 0 else 12.5
        report["export"] = convert.mmd_convert_and_export(arm, export_path, scale=scale)
    return arm, meshes, report
