"""Opt-in faithful SV helpers emitted by the native Yosys backend.

Retain inferred memories as arrays. Never run memory_map, async2sync, opt,
or clock rewrites here. These helpers remove an RTL emission gap; they do
not qualify reset timing, physical memories, or a plan boundary.
"""
import fcntl
import hashlib
import json
import re
from pathlib import Path
import bind_elab as E
from native_mem2reg import mark_mem2reg
from native_memwr_merge import merge_memwr
import os

# $mem_v2 / $shiftx (Codex 861); TOK-SCHED 10-25 adds the remaining combinational word-level primitives that the
# current S81 dissolved parents (ot_s81sl_vp, dsdv_svc_att, dsdv_svc_rs_c, ot_hdc_v41x_attn_s) carry and _glue does not
# re-emit: Yosys write_verilog prints each one with its own documented semantics; nothing is mapped or optimised.
SUPPORTED = {"$mem_v2", "$shiftx", "$shift", "$demux", "$bwmux", "$bmux", "$pmux", "$div", "$mod"}

class NativeGlueError(RuntimeError):
    pass

class NativeGlue:
    def __init__(self, directory, enabled):
        if not isinstance(enabled, list) or any(t not in SUPPORTED for t in enabled):
            raise NativeGlueError("native_glue_types must name only " + ", ".join(sorted(SUPPORTED)))
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
        # TOK-SCHED 10-25: input bits that are the SAME design net (e.g. the one clock of several write ports,
        # WR_CLK [2, 2]) must stay one net inside the helper too; otherwise Yosys sees distinct write clocks with a
        # priority relation (mem.cc assert port.clk == wport.clk) and the helper would not be faithful anyway.
        first, share = {}, {}
        for p in widths:
            if dirs[p] != "input":
                continue
            for i, b in enumerate(cell.ports[p]):
                if isinstance(b, str):
                    continue
                if b in first:
                    share[(p, i)] = first[b]
                else:
                    first[b] = (p, i)
        signature = json.dumps([cell.ytype, params, widths, dirs, constants,
                                sorted([list(k) + list(v) for k, v in share.items()])], sort_keys=True)
        key = hashlib.sha256(signature.encode()).hexdigest()[:24]
        module = "ot_bind_native_" + key
        if key not in self.cache:
            self.directory.mkdir(parents=True, exist_ok=True)
            ports, conns, next_bit, allbits = {}, {}, 2, {}
            for p, width in widths.items():
                bits = list(range(next_bit, next_bit + width))
                next_bit += width
                allbits[p] = bits
            for p, width in widths.items():
                bits = allbits[p]
                # Native memory validation requires static async-read enables,
                # reset values, and unused clocks to remain literal, not ports.
                inner = [allbits[share[(p, i)][0]][share[(p, i)][1]] if (p, i) in share else b
                         for i, b in enumerate(bits)]
                conns[p] = [c if c is not None else b for b, c in zip(inner, constants[p])]
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
            # All paths are generated below the output directory; reject names
            # that cannot be represented by Yosys's quoted filename syntax.
            if any('"' in str(p) or "\n" in str(p) for p in (inp, sv)):
                raise NativeGlueError("invalid native glue output path")
            # write_verilog has no expression for $bwmux / $demux / $bmux: lower only that one cell with its own
            # Yosys map pass (bit-exact by construction: and/or, shift/compare), nothing else
            lower = {"$bwmux": "bwmuxmap\n", "$demux": "demuxmap\n", "$bmux": "bmuxmap\n"}.get(cell.ytype, "")
            # Forked type workers have separate caches but share these paths.
            # Keep the same input inode and lock it before truncating it or
            # updating any of the helper's Yosys inputs, outputs and logs.
            with inp.open("a") as input_file:
                fcntl.flock(input_file, fcntl.LOCK_EX)
                input_file.truncate(0)
                input_file.write(json.dumps(data))
                input_file.flush()
                ys.write_text(f'read_json "{inp}"\n{lower}write_verilog -noattr "{sv}"\n')
                try:
                    E.run_yosys(ys, self.directory / (module + ".log"),
                                [self.directory], mem_gb=2)
                except E.ElabError as exc:
                    raise NativeGlueError(str(exc)) from exc
                merged = []
                if cell.ytype == "$mem_v2":
                    # write_verilog expands every per-bit write enable into its own statement (S81 svc hi: 4096 $memwr on one
                    # 256 x 40 memory); register-ise such arrays before Yosys's superlinear memory passes (exact, see native_mem2reg)
                    text, marked = mark_mem2reg(sv.read_text())
                    # S81-SVC-SYNTH 11-15: the same per-bit statements stall canonicalize (PROC_PRUNE/PROC_DFF, hours) even as
                    # registers; merge each run of one port into chunk-wide read-modify-write statements (exact, see native_memwr_merge).
                    # mem2reg is decided on the per-bit count BEFORE the merge: a 262144-bit memory left as $mem fails ORFS
                    # SYNTH_MEMORY_MAX_BITS (svc_hi t3, 37 min into 1_2_yosys), the register form is what the kits have always had.
                    if os.environ.get("OT_NATIVE_MEMWR_MERGE", "1") != "0":
                        text, merged = merge_memwr(text)
                        if merged:
                            (self.directory / (module + ".memwr_merge.txt")).write_text(
                                "".join(f"{m} {b} -> {a}\n" for m, b, a in merged))
                    if marked or merged:
                        sv.write_text(text)
            self.cache[key] = module
            self.files.append(sv)
        actual = [f".{p}({connections[p]})" for p, width in widths.items() if width and p in exposed]
        return f"    {module} {instance} (" + ", ".join(actual) + ");"
