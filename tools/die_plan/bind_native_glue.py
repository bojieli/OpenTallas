"""Opt-in faithful SV helpers emitted by the native Yosys backend.

Retain inferred memories as arrays. Never run memory_map, async2sync, opt,
or clock rewrites here. These helpers remove an RTL emission gap; they do
not qualify reset timing, physical memories, or a plan boundary.
"""
import hashlib
import json
import re
from pathlib import Path
import bind_elab as E

SUPPORTED = {"$mem_v2", "$shiftx"}

class NativeGlueError(RuntimeError):
    pass

class NativeGlue:
    def __init__(self, directory, enabled):
        if not isinstance(enabled, list) or any(t not in SUPPORTED for t in enabled):
            raise NativeGlueError("native_glue_types must name only $mem_v2 or $shiftx")
        self.enabled = set(enabled)
        self.directory = Path(directory).resolve()
        self.files = []
        self.cache = {}

    def emit(self, cell, connections, instance):
        if cell.ytype not in self.enabled:
            raise NativeGlueError("primitive is not explicitly enabled")
        params = dict(cell.yparams)
        # MEMID names the private array, not external state. Each helper instance
        # owns a distinct array; normalize its local name to share identical RTL.
        if cell.ytype == "$mem_v2":
            params["MEMID"] = "\\\\native_memory"
        widths = {p: len(b) for p, b in sorted(cell.ports.items())}
        dirs = {p: cell.dirs.get(p) for p in widths}
        if any(d not in ("input", "output") for d in dirs.values()):
            raise NativeGlueError("native glue requires explicit input/output directions")
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p) for p in widths):
            raise NativeGlueError("unsupported native glue port identifier")
        constants = {p: [b if isinstance(b, str) else None for b in cell.ports[p]] for p in widths}
        exposed = {p for p in widths if any(b is None for b in constants[p])}
        signature = json.dumps([cell.ytype, params, widths, dirs, constants], sort_keys=True)
        key = hashlib.sha256(signature.encode()).hexdigest()[:24]
        module = "ot_bind_native_" + key
        if key not in self.cache:
            self.directory.mkdir(parents=True, exist_ok=True)
            ports, conns, next_bit = {}, {}, 2
            for p, width in widths.items():
                bits = list(range(next_bit, next_bit + width))
                next_bit += width
                # Native memory validation requires static async-read enables,
                # reset values, and unused clocks to remain literal, not ports.
                conns[p] = [c if c is not None else b for b, c in zip(bits, constants[p])]
                if width and p in exposed:
                    ports[p] = {"direction": dirs[p], "bits": bits}
            data = {"modules": {module: {
                "attributes": {}, "ports": ports, "netnames": {},
                "cells": {"primitive": {"hide_name": 0, "type": cell.ytype,
                    "parameters": params, "attributes": {},
                    "port_directions": dirs, "connections": conns}}
            }}}
            inp = self.directory / (module + ".json")
            sv = self.directory / (module + ".sv")
            ys = self.directory / (module + ".ys")
            inp.write_text(json.dumps(data))
            # All paths are generated below the output directory; reject names
            # that cannot be represented by Yosys's quoted filename syntax.
            if any('"' in str(p) or "\n" in str(p) for p in (inp, sv)):
                raise NativeGlueError("invalid native glue output path")
            ys.write_text(f'read_json "{inp}"\nwrite_verilog -noattr "{sv}"\n')
            try:
                E.run_yosys(ys, self.directory / (module + ".log"),
                            [self.directory], mem_gb=2)
            except E.ElabError as exc:
                raise NativeGlueError(str(exc)) from exc
            self.cache[key] = module
            self.files.append(sv)
        actual = [f".{p}({connections[p]})" for p, width in widths.items() if width and p in exposed]
        return f"    {module} {instance} (" + ", ".join(actual) + ");"
