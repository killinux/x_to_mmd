"""Little-endian byte cursor for XPS binary files, plus the .NET 7-bit string length.

All multi-byte values are little-endian (matches XNALara/XPS). Strings are length-
prefixed with a .NET BinaryReader 7-bit variable-length integer, then UTF-8 bytes
(decoded utf-8-sig to absorb a stray BOM).
"""
from __future__ import annotations

import io
import struct


class BinReader:
    def __init__(self, data: bytes):
        self._io = io.BytesIO(data)
        self._len = len(data)

    # --- position ---
    def tell(self) -> int:
        return self._io.tell()

    def seek(self, pos: int) -> None:
        self._io.seek(pos)

    def eof(self) -> bool:
        return self._io.tell() >= self._len

    def read(self, n: int) -> bytes:
        b = self._io.read(n)
        if len(b) != n:
            raise EOFError(f"wanted {n} bytes, got {len(b)} at pos {self.tell()}")
        return b

    # --- scalars ---
    def byte(self) -> int:
        return self.read(1)[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.read(2))[0]

    def i16(self) -> int:
        return struct.unpack("<h", self.read(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.read(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.read(4))[0]

    def f32(self) -> float:
        return struct.unpack("<f", self.read(4))[0]

    def floats(self, n: int):
        return list(struct.unpack("<%df" % n, self.read(4 * n)))

    def peek_u32(self) -> int:
        p = self.tell()
        v = self.u32()
        self.seek(p)
        return v

    # --- strings (.NET 7-bit length-prefixed, UTF-8) ---
    def varint(self) -> int:
        result = 0
        shift = 0
        while True:
            b = self.byte()
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
            if shift > 35:
                raise ValueError("varint too long (corrupt string length)")
        return result

    def string(self) -> str:
        n = self.varint()
        return self.read(n).decode("utf-8-sig", errors="replace")
