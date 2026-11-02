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

# $mem_v2 / $shiftx (Codex 861); TOK-SCHED 10-25 adds the remaining combinational word-level primitives that the
# current S81 dissolved parents (ot_s81sl_vp, dsdv_svc_att, dsdv_svc_rs_c, ot_hdc_v41x_attn_s) carry and _glue does not
# re-emit: Yosys write_verilog prints each one with its own documented semantics; nothing is mapped or optimised.
SUPPORTED = {"$mem_v2", "$shiftx", "$shift", "$demux", "$bwmux", "$bmux", "$pmux", "$div", "$mod"}

# Portable representation of the *same* $shiftx operator. Some SV simulators
# mishandle a dynamic part-select wider than its input with a negative index.
# X-pad both ends and use a bounded non-negative index into the wider vector.
# Explicit signed full-width bounds also preserve large-B/OOB behavior rather
# than relying on a simulator's integer conversion of a part-select index.
SHIFTX_PORTABLE_MAP = r"""
(* techmap_celltype = "$shiftx" *)
module _ot_portable_shiftx(A, B, Y);
  parameter A_SIGNED = 0, B_SIGNED = 0;
  parameter A_WIDTH = 1, B_WIDTH = 1, Y_WIDTH = 1;
  input [A_WIDTH-1:0] A;
  input [B_WIDTH-1:0] B;
  output [Y_WIDTH-1:0] Y;
  function integer imax;
    input integer a, b;
    begin imax = a > b ? a : b; end
  endfunction
  localparam IW = imax(B_WIDTH, imax($clog2(A_WIDTH+1), $clog2(Y_WIDTH+1))) + 2;
  localparam signed [IW-1:0] PAD = Y_WIDTH;
  localparam signed [IW-1:0] LOW = 1 - PAD;
  localparam signed [IW-1:0] HIGH = A_WIDTH;
  wire signed [IW-1:0] base;
  generate if (B_SIGNED) begin
    assign base = {{(IW-B_WIDTH){B[B_WIDTH-1]}}, B};
  end else begin
    assign base = {{(IW-B_WIDTH){1'b0}}, B};
  end endgenerate
  wire [A_WIDTH+2*Y_WIDTH-1:0] padded = {{Y_WIDTH{1'bx}}, A, {Y_WIDTH{1'bx}}};
  wire signed [IW-1:0] index = base + PAD;
  assign Y = (base >= LOW && base < HIGH) ? padded[index +: Y_WIDTH] : {Y_WIDTH{1'bx}};
endmodule
"""

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
            inp.write_text(json.dumps(data))
            # All paths are generated below the output directory; reject names
            # that cannot be represented by Yosys's quoted filename syntax.
            if any('"' in str(p) or "\n" in str(p) for p in (inp, sv)):
                raise NativeGlueError("invalid native glue output path")
            # write_verilog has no expression for $bwmux / $demux / $bmux: lower only that one cell with its own
            # Yosys map pass (bit-exact by construction: and/or, shift/compare), nothing else
            lower = {"$bwmux": "bwmuxmap\n", "$demux": "demuxmap\n", "$bmux": "bmuxmap\n"}.get(cell.ytype, "")
            if cell.ytype == "$shiftx" and all(widths.get(p, 0) > 0 for p in ("A", "B", "Y")):
                mapper = self.directory / (module + "_shiftx_map.v")
                mapper.write_text(SHIFTX_PORTABLE_MAP)
                # Exactly one expansion: keep the safe wider $shiftx in the map
                # instead of recursively mapping that new cell back into itself.
                lower = f'techmap -max_iter 1 -map "{mapper}" t:$shiftx\n'
            ys.write_text(f'read_json "{inp}"\n{lower}write_verilog -noattr "{sv}"\n')
            try:
                E.run_yosys(ys, self.directory / (module + ".log"),
                            [self.directory], mem_gb=2)
            except E.ElabError as exc:
                raise NativeGlueError(str(exc)) from exc
            self.cache[key] = module
            self.files.append(sv)
        actual = [f".{p}({connections[p]})" for p, width in widths.items() if width and p in exposed]
        return f"    {module} {instance} (" + ", ".join(actual) + ");"
