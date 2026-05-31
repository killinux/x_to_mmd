"""x_to_mmd — Blender add-on: convert any XPS/XNALara model to MMD (PMX).

Legacy bl_info (Blender 3.x) + blender_manifest.toml (4.2+ Extensions) both present.
The heavy lifting lives in `core/` (bpy-independent, unit-tested) and `blender/`.
"""

bl_info = {
    "name": "XPS to MMD",
    "author": "x_to_mmd",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > XPS→MMD",
    "description": "Convert XPS/XNALara models to MMD (PMX): import, auto bone-map, "
                   "weight-safe rename/merge, complete MMD rig + leg IK + 付与, drive mmd_tools to export.",
    "warning": "Requires the mmd_tools add-on for PMX export.",
    "category": "Import-Export",
}

import bpy  # type: ignore
from bpy.props import FloatProperty, StringProperty  # type: ignore
from bpy_extras.io_utils import ImportHelper  # type: ignore


class XPS2MMD_OT_convert(bpy.types.Operator, ImportHelper):
    """Import an XPS/XNALara model and convert it toward an MMD (PMX) rig."""
    bl_idname = "xps2mmd.convert"
    bl_label = "Import & Convert XPS → MMD"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".xps"
    filter_glob: StringProperty(default="*.xps;*.mesh;*.ascii", options={"HIDDEN"})
    model_name: StringProperty(name="Model name", default="xps_mmd")
    export_pmx: StringProperty(name="Export PMX (optional)", subtype="FILE_PATH", default="")
    fit_height: FloatProperty(name="Fit height (0 = scale 12.5)", default=0.0, min=0.0)

    def execute(self, context):
        from .blender import pipeline
        try:
            _arm, _meshes, report = pipeline.run(
                self.filepath, name=self.model_name,
                export_path=self.export_pmx, fit_height=self.fit_height,
            )
        except Exception as e:  # noqa: BLE001
            self.report({"ERROR"}, f"XPS→MMD failed: {e}")
            return {"CANCELLED"}
        a = report.get("apply", {})
        r = report.get("rig", {})
        self.report({"INFO"}, "XPS→MMD: %d renamed, %d merged, +%d bones, %d grants, IK %s"
                    % (a.get("renamed", 0), a.get("merged", 0), r.get("added_bones", 0),
                       r.get("grants", 0), report.get("ik", {}).get("ik_constraints", 0)))
        return {"FINISHED"}


class XPS2MMD_PT_panel(bpy.types.Panel):
    bl_label = "XPS → MMD"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "XPS→MMD"

    def draw(self, context):
        col = self.layout.column()
        col.operator("xps2mmd.convert", icon="ARMATURE_DATA")
        col.label(text="Needs mmd_tools for PMX export")


_classes = (XPS2MMD_OT_convert, XPS2MMD_PT_panel)


def register():
    for c in _classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
