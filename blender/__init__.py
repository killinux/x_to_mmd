"""x_to_mmd Blender layer — bpy-DEPENDENT (runs only inside Blender).

Imports XPS into a Blender scene, then converts the rig/materials toward MMD and
drives mmd_tools to export PMX. Tested against a live Blender 3.6 via the remote
MCP socket (see dev/blender_rpc.py).
"""
