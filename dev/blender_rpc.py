#!/usr/bin/env python3
"""Dev-only helper: run Python in the remote Blender via the blender-mcp socket.

Talks to the blender-mcp addon TCP socket (default 49.233.189.223:9876) exposed
through the remote_win VPS tunnel. NOT shipped with the add-on (kept under dev/).

Protocol (blender-mcp addon):
    {"type":"execute_code","params":{"code":"..."}}  -> {"status","result":{"executed","result":<stdout>}}
    {"type":"get_scene_info"}                          -> {"status","result":{...}}

Usage:
    python3 dev/blender_rpc.py --scene
    python3 dev/blender_rpc.py --code 'import bpy; print(bpy.app.version_string)'
    python3 dev/blender_rpc.py --file dev/snippet.py
    python3 dev/blender_rpc.py --file dev/snippet.py --raw   # full JSON, not just stdout
"""
import sys
import json
import socket
import argparse

HOST = "49.233.189.223"
PORT = 9876


def call(host, port, message, timeout=180):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((host, port))
    s.sendall(json.dumps(message).encode())
    buf = b""
    while True:
        try:
            chunk = s.recv(8192)
            if not chunk:
                break
            buf += chunk
            json.loads(buf)  # complete?
            break
        except json.JSONDecodeError:
            continue
        except socket.timeout:
            break
    s.close()
    return json.loads(buf) if buf else {"error": "No response"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--scene", action="store_true", help="get_scene_info")
    ap.add_argument("--code", default=None, help="inline python code")
    ap.add_argument("--file", default=None, help="read python code from a file")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--raw", action="store_true", help="print full JSON response")
    args = ap.parse_args()

    if args.scene:
        resp = call(args.host, args.port, {"type": "get_scene_info"}, args.timeout)
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        return

    code = args.code
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            code = f.read()
    resp = call(args.host, args.port,
                {"type": "execute_code", "params": {"code": code or ""}},
                args.timeout)

    if args.raw:
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        return

    # Friendly: print captured stdout, surface errors with non-zero exit.
    status = resp.get("status")
    result = resp.get("result") or {}
    if status == "success":
        sys.stdout.write(result.get("result", "") or "")
        if not result.get("result"):
            print("[ok] (no stdout)")
    else:
        print("[BLENDER ERROR] " + json.dumps(resp, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
