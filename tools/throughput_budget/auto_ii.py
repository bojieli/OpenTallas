#!/usr/bin/env python3
"""Generic auto-II harness (tput-gate-1010, owner 2026-10-11): measure an element's sustained items / cycle at production
shape from its EXISTING exact bench, without writing a new bench.

  record   run the element's bench command with a PATH shim in front of `iverilog`: the shim finds the element's
           instance under the bench top (regex over the compile's sources), adds a root module that dumps that instance's
           scope ($dumpvars depth 1: ports + parameters) to <run>/autoii.vcd, and compiles as before.  The bench's own
           golden check still runs (its PASS line is required).
  replay   parse the VCD (rising clk edges): reset prefix kept as recorded; every later cycle where no input
           handshake is active is dropped (back-to-back), outputs' ready-like inputs are tied 1, and the input stream is
           held while a ready-like output of the element is low.  A generated top (same sources, same parameter values
           from the VCD) drives the compressed stream into a fresh instance and checks the output transaction sequence
           (every output, sampled at each output-valid edge) against the recorded one: EXACT or not.
  result   items = input transactions, cycles = first input edge -> last output-valid edge, II = cycles / items.

Limits (reported, never hidden): only `iverilog` benches; one instance (the first found); closed-loop interfaces
(responses an element waits for) cannot be replayed open-loop -> the output sequence differs or the run hangs -> verdict
REPLAY_NOT_APPLICABLE (the element needs a bench-level back-to-back mode).

    python3 tools/throughput_budget/auto_ii.py record --block B --run DIR -- <bench command ...>
    python3 tools/throughput_budget/auto_ii.py replay --run DIR [--out DIR/autoii.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

VALID_IN = re.compile(r"(^|_)(v|valid|vld|in_v|req_v|push|go|start|wr_v|we|ld|load|issue|cmd_v|rec_v|in_valid|s_valid|i_v)$", re.I)
READY_OUT = re.compile(r"(^|_)(rdy|ready|req_r|ack|accept|in_r|s_ready|full_n|o_rdy)$", re.I)
VALID_OUT = re.compile(r"(^|_)(v|valid|vld|out_v|vo|done|o_v|m_valid|rsp_v|out_valid|o_valid|wr_en|we|wen|wr_v|push)$", re.I)
READY_IN = re.compile(r"(^|_)(rdy|ready|out_r|rsp_r|m_ready|o_rdy|out_rdy|ds_rdy)$", re.I)
CLOCK = re.compile(r"^(clk|ck|clock|clk_i|aclk|core_clk)$")
RESET = re.compile(r"^(rst_n|rstn|reset_n|rst|reset|por_n|arst_n)$")

SHIM = r'''#!/usr/bin/env python3
import json, os, re, subprocess, sys
REAL = os.environ["OT_AUTOII_REAL_IVERILOG"]; BLOCK = os.environ["OT_AUTOII_BLOCK"]; RUN = os.environ["OT_AUTOII_RUN"]
a = sys.argv[1:]
lock = os.path.join(RUN, "autoii.meta.json")
def go(args): os.execv(REAL, [REAL] + args)
if os.path.exists(lock) or "-E" in a: go(a)
top = None; srcs = []; i = 0; out = None; defs = []; pars = []; incs = []
while i < len(a):
    x = a[i]
    if x == "-s": top = a[i + 1]; i += 2; continue
    if x == "-o": out = a[i + 1]; i += 2; continue
    if x == "-I": incs.append(os.path.abspath(a[i + 1])); i += 2; continue
    if x.startswith("-I") and len(x) > 2: incs.append(os.path.abspath(x[2:])); i += 1; continue
    if x in ("-y", "-c", "-f", "-W", "-g", "-T", "-N", "-M", "-m", "-p", "-l"): i += 2; continue
    if x.startswith("-D"): defs.append(x); i += 1; continue
    if x.startswith("-P"): pars.append(x); i += 1; continue
    if not x.startswith("-") and (x.endswith(".sv") or x.endswith(".v")): srcs.append(x)
    i += 1
txt = {}
for s in srcs:
    try: txt[s] = open(s).read()
    except OSError: pass
mods = {}
for s, t in txt.items():
    t2 = re.sub(r"//.*", "", t); t2 = re.sub(r"/\*.*?\*/", "", t2, flags=re.S)
    for m in re.finditer(r"\bmodule\s+(\w+)(.*?)\bendmodule", t2, re.S):
        mods[m.group(1)] = (s, m.group(2))
def insts(body):
    for m in re.finditer(r"(?m)^\s*(\w+)\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*(\w+)\s*(\[[^\]]*\])?\s*\(", body):
        if m.group(1) in mods and m.group(1) not in ("module", "if", "for", "case", "always", "assign", "begin"):
            yield m.group(1), m.group(3), m.group(2) or ""
path = None
def find(mod, pre, depth=0):
    global path
    if depth > 8 or path: return
    for sub, name, prm in insts(mods.get(mod, ("", ""))[1]):
        if sub == BLOCK: path = (pre + "." + name, prm); return
        find(sub, pre + "." + name, depth + 1)
if top is None or BLOCK not in mods: go(a)
find(top, top)
if not path: go(a)
rec = os.path.join(RUN, "ot_autoii_rec.v")
open(rec, "w").write("module ot_autoii_rec; initial begin $dumpfile(\"%s\"); $dumpvars(1, %s); end endmodule\n"
                     % (os.path.join(RUN, "autoii.vcd"), path[0]))
import shutil as _sh
cp = os.path.join(RUN, "src"); os.makedirs(cp, exist_ok=True); kept = []
for j_, s_ in enumerate(srcs):   # benches may compile temp files: keep copies
    d_ = os.path.join(cp, "%03d_%s" % (j_, os.path.basename(s_)))
    try: _sh.copy(s_, d_); kept.append(d_)
    except OSError: pass
bsrc = next((k for k, s_ in zip(kept, srcs) if os.path.abspath(s_) == os.path.abspath(mods[BLOCK][0])), mods[BLOCK][0])
incs += [os.path.dirname(os.path.abspath(s_)) for s_ in srcs]   # `include resolves next to the original source
incs = list(dict.fromkeys(incs))
json.dump(dict(top=top, path=path[0], inst_params=path[1], sources=kept, defines=defs, incdirs=incs,
               params=pars, cwd=os.getcwd(), block=BLOCK, block_src=os.path.abspath(bsrc)), open(lock, "w"), indent=1)
go(a + ["-s", "ot_autoii_rec", rec])
'''

VSHIM = r"""#!/usr/bin/env python3
# Verilator shim (owner 2026-10-11): a generated SystemVerilog bind monitor on the element's ports (anim-1011 style):
# bind <BLOCK> ot_autoii_mon #(<the block's parameters>) u_autoii_mon (.*);  one trace file per bound instance.
import json, os, re, sys
REAL = os.environ["OT_AUTOII_REAL_VERILATOR"]; BLOCK = os.environ["OT_AUTOII_BLOCK"]; RUN = os.environ["OT_AUTOII_RUN"]
a = sys.argv[1:]
lock = os.path.join(RUN, "autoii.meta.json")
def go(args): os.execv(REAL, [REAL] + args)
if os.path.exists(lock) or "--lint-only" in a or "-E" in a: go(a)
srcs = []; i = 0; top = None; defs = []
def addf(fn):
    for ln in open(fn).read().split():
        if ln.endswith((".sv", ".v")): srcs.append(ln)
while i < len(a):
    x = a[i]
    if x in ("--top-module", "--top"): top = a[i + 1]; i += 2; continue
    if x == "-f": addf(a[i + 1]); i += 2; continue
    if x.startswith("-D") or x.startswith("+define+"): defs.append(x)
    if not x.startswith("-") and x.endswith((".sv", ".v")): srcs.append(x)
    i += 1
body = None
for s_ in srcs:
    try: t = open(s_).read()
    except OSError: continue
    t = re.sub(r"//.*", "", t); t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    m = re.search(r"\bmodule\s+%s\b\s*(#\s*\((.*?)\)\s*)?\((.*?)\);" % re.escape(BLOCK), t, re.S)
    if m: body = (s_, m.group(2) or "", m.group(3)); break
if body is None: go(a)
src, ptxt, portxt = body
params = re.findall(r"\bparameter\s+(?:integer\s+|int\s+|logic\s+|bit\s+)?(?:\[[^\]]*\]\s*)?(\w+)\s*=\s*([^,]+?)(?=,\s*(?:parameter|localparam)|$)", ptxt.strip(), re.S)
seen_ = set(); params = [(n, v) for n, v in params if not (n in seen_ or seen_.add(n))]
ports = []; cur = None
for chunk in re.split(r",(?![^\[]*\])", portxt):
    m = re.match(r"\s*(input|output|inout)\b\s*(?:wire|reg|logic|var)?\s*(signed)?\s*(\[[^\]]+\])?\s*(\w+)\s*$", chunk.strip(), re.S)
    if m: cur = (m.group(1), m.group(3) or ""); ports.append((cur[0], cur[1], m.group(4))); continue
    m = re.match(r"\s*(\w+)\s*$", chunk.strip())
    if m and cur: ports.append((cur[0], cur[1], m.group(1)))
clk = next((n for d, r, n in ports if re.match(r"^(clk|ck|clock|clk_i|aclk|core_clk)$", n)), None)
if not clk or not ports: go(a)
pl = ", ".join("parameter %s = %s" % (n, v.strip()) for n, v in params)
decl = ", ".join("input wire %s %s" % (r, n) for d, r, n in ports)
names = [n for d, r, n in ports if n != clk]
mon = os.path.join(RUN, "ot_autoii_mon.sv")
fmt = " ".join(["%h"] * len(names))
open(mon, "w").write(
    "module ot_autoii_mon %s (%s);\n" % ("#(" + pl + ")" if pl else "", decl) +
    "  integer fd; initial begin fd = $fopen($sformatf(\"%s/mon.%%m.txt\")); $fwrite(fd, \"#W %s\\n\", %s); end\n"
    % (RUN, " ".join(["%0d"] * len(names)), ", ".join("$bits(%s)" % n for n in names)) +
    "  always @(posedge %s) $fwrite(fd, \"%s\\n\", %s);\n" % (clk, fmt, ", ".join(names)) +
    "endmodule\n" +
    "bind %s ot_autoii_mon %s u_autoii_mon (.*);\n" % (BLOCK, "#(" + ", ".join(".%s(%s)" % (n, n) for n, v in params) + ")" if params else ""))
json.dump(dict(fmt="mon", top=top, path=None, sources=[os.path.abspath(x) for x in srcs], defines=defs, cwd=os.getcwd(),
               block=BLOCK, block_src=os.path.abspath(src), ports=[dict(dir=d, range=r, name=n) for d, r, n in ports],
               names=names, clk=clk), open(lock, "w"), indent=1)
import subprocess
r_ = subprocess.run([REAL] + a + [mon, "-Wno-fatal"])
if r_.returncode != 0:          # fail-safe: the bench must still run; record that the monitor did not build
    os.rename(lock, os.path.join(RUN, "autoii.mon_failed.json"))
    go(a)
sys.exit(0)
"""


def record(a):
    run = Path(a.run).resolve()
    run.mkdir(parents=True, exist_ok=True)
    for f in ("autoii.meta.json", "autoii.vcd"):
        (run / f).unlink(missing_ok=True)
    shim = run / "shim"
    shim.mkdir(exist_ok=True)
    (shim / "iverilog").write_text(SHIM)
    (shim / "iverilog").chmod(0o755)
    (shim / "verilator").write_text(VSHIM)
    (shim / "verilator").chmod(0o755)
    for f in run.glob("mon.*.txt"):
        f.unlink()
    real = shutil.which("iverilog")
    env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}", OT_AUTOII_REAL_IVERILOG=real or "/usr/bin/iverilog",
               OT_AUTOII_REAL_VERILATOR=shutil.which("verilator") or "/usr/bin/verilator", OT_AUTOII_BLOCK=a.block,
               OT_AUTOII_RUN=str(run))
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    p = subprocess.run(cmd if len(cmd) > 1 else ["bash", "-c", cmd[0]], env=env, capture_output=True, text=True,
                       timeout=a.timeout)
    (run / "bench.log").write_text(p.stdout + p.stderr)
    ok = (run / "autoii.meta.json").exists() and ((run / "autoii.vcd").exists() or any(run.glob("mon.*.txt")))
    print(json.dumps(dict(recorded=ok, rc=p.returncode)))
    return 0 if ok else 2


# ---------------------------------------------------------------- VCD
def parse_vcd(path):
    """-> (signals {name: (id, width, kind)}, params {name: int}, edges: list of {name: value} at each clk rising edge)"""
    ids, sig, params = {}, {}, {}
    vals, edges = {}, []
    clk_id = None
    with open(path) as f:
        head = True
        for ln in f:
            ln = ln.strip()
            if head:
                if ln.startswith("$var"):
                    p = ln.split()
                    kind, w, i, name = p[1], int(p[2]), p[3], p[4]
                    ids.setdefault(i, []).append(name)
                    sig[name] = (i, w, kind)
                    if CLOCK.match(name) and clk_id is None:
                        clk_id = i
                elif ln.startswith("$enddefinitions"):
                    head = False
                continue
            if not ln:
                continue
            if ln[0] == "#":
                continue
            if ln[0] in "01xzXZ" and len(ln) >= 2 and ln[1:] in ids:
                v, i = ln[0], ln[1:]
                old = vals.get(i)
                vals[i] = v
                if i == clk_id and v == "1" and old == "0":
                    edges.append(dict(vals))   # values BEFORE this edge's updates in the same timestep are what flops see
            elif ln[0] in "bB":
                v, i = ln[1:].split()
                vals[i] = v
            elif ln[0] in "rR":
                v, i = ln[1:].split()
                vals[i] = v
    for name, (i, w, kind) in sig.items():
        if kind == "parameter" and i in vals:
            try:
                params[name] = int(vals[i], 2) if set(vals[i]) <= set("01") else None
            except ValueError:
                params[name] = None
    return sig, params, edges, clk_id


def ports_of(src_file, block):
    t = Path(src_file).read_text()
    t = re.sub(r"//.*", "", t)
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    m = re.search(r"\bmodule\s+%s\b(.*?)\bendmodule" % re.escape(block), t, re.S)
    body = m.group(1)
    head = body.split(";", 1)[0]
    ins, outs, params = [], [], []
    for d, rng, names in re.findall(r"\b(input|output|inout)\s+(?:wire|reg|logic|signed|\s)*(\[[^\]]*\])?\s*([\w\s,]+?)(?=[,;)]\s*(?:input|output|inout|\)|$|;))", body, re.S):
        for n in re.split(r"[,\s]+", names.strip()):
            if re.fullmatch(r"[A-Za-z_]\w*", n) and n not in ("wire", "reg", "logic", "signed"):
                (ins if d == "input" else outs).append(n)
    for n in re.findall(r"\bparameter\s+(?:integer\s+|\[[^\]]*\]\s*)?(\w+)\s*=", head):
        params.append(n)
    return list(dict.fromkeys(ins)), list(dict.fromkeys(outs)), params


def b0(edge, sig, name):
    """handshake active: f_* / t_* die buses = bit 0; a valid-named vector = any bit"""
    v = edge.get(sig[name][0])
    if v is None:
        return False
    return v[-1] == "1" if name.startswith(("f_", "t_")) and sig[name][1] > 1 else "1" in v


def val(edge, sig, name):
    s = sig.get(name)
    if not s:
        return None
    return edge.get(s[0])


def parse_mon(run, meta):
    """bind-monitor trace (Verilator) -> the parse_vcd shapes: sig {name: (name, width, 'wire')}, edges of binary strings"""
    fs = sorted(run.glob("mon.*.txt"), key=lambda f: -f.stat().st_size)
    if not fs:
        return {}, {}, [], None
    lines = fs[0].read_text().split("\n")
    wd = [int(x) for x in lines[0].split()[1:]]
    names = meta["names"]
    sig = {n: (n, w, "wire") for n, w in zip(names, wd)}
    sig[meta["clk"]] = (meta["clk"], 1, "wire")
    edges = []
    for ln in lines[1:]:
        p = ln.split()
        if len(p) != len(names):
            continue
        e = {}
        for n, w, v in zip(names, wd, p):
            try:
                e[n] = format(int(v, 16), "b").zfill(w)[-w:] if "x" not in v.lower() else "x" * w
            except ValueError:
                e[n] = "x" * w
        edges.append(e)
    return sig, {}, edges, meta["clk"]


def accept_ii(edges, sig, pairs, k0):
    """closed-loop interfaces (owner 2026-10-11): II from the recorded steady-state accept spacing at full rate = the
    cycles the producer offered (valid high) / the transfers accepted (valid & ready), per handshake pair; the pair with
    the most transfers is the element's input"""
    best = None
    for v, r_ in pairs:
        off = acc = 0
        for e in edges[k0:]:
            vv, rr = e.get(sig[v][0]), e.get(sig[r_][0])
            if vv is None or rr is None:
                continue
            on = (vv[-1] == "1") if v.startswith("f_") and sig[v][1] > 1 else ("1" in vv)
            if on:
                off += 1
                if (rr[-1] == "1") if sig[r_][1] == 1 or v.startswith("f_") else any(a_ == "1" and b_ == "1" for a_, b_ in zip(vv, rr)):
                    acc += 1
        if acc and (best is None or acc > best[2]):
            best = (v, r_, acc, off)
    if not best:
        return None
    return dict(valid=best[0], ready=best[1], accepts=best[2], offered_cycles=best[3], ii=round(best[3] / best[2], 3))


def replay(a):
    run = Path(a.run).resolve()
    meta = json.loads((run / "autoii.meta.json").read_text())
    if meta.get("fmt") == "mon":
        sig, params, edges, clk_id = parse_mon(run, meta)
    else:
        sig, params, edges, clk_id = parse_vcd(run / "autoii.vcd")
    ins, outs, pnames = ports_of(meta["block_src"], meta["block"])
    w = {n: sig[n][1] for n in sig}
    clk = next((n for n in ins if CLOCK.match(n)), None)
    rst = next((n for n in ins if RESET.match(n)), None)
    # 1-bit valid-named ports, plus the die-bus convention f_* / t_* {data, valid} buses (valid = bit 0)
    vin = [n for n in ins if 0 < (w.get(n) or 0) <= 64 and VALID_IN.search(n)] + \
          [n for n in ins if (w.get(n) or 0) > 1 and n.startswith("f_")]
    rdy_out = [n for n in outs if w.get(n) == 1 and READY_OUT.search(n)]
    vout = [n for n in outs if 0 < (w.get(n) or 0) <= 64 and VALID_OUT.search(n)] + \
           [n for n in outs if (w.get(n) or 0) > 1 and n.startswith("t_")]
    rdy_in = [n for n in ins if w.get(n) == 1 and READY_IN.search(n)]
    res = dict(block=meta["block"], path=meta["path"], clk=clk, rst=rst, valid_in=vin, ready_out=rdy_out, valid_out=vout,
               ready_in=rdy_in, edges=len(edges))
    # handshake pairs: valid input <prefix>{v,valid,vld} with ready output <prefix>{r,rdy,ready}
    pairs = []
    for v in vin:
        m_ = re.match(r"(.*?)(v|valid|vld)$", v)
        if m_:
            for r_ in (m_.group(1) + "r", m_.group(1) + "rdy", m_.group(1) + "ready"):
                if r_ in outs and w.get(r_) == w.get(v):
                    pairs.append((v, r_))
    for v in vin:
        if v.startswith("f_") and ("t_" + v[2:]) in outs and w.get("t_" + v[2:]) == 1:
            pairs.append((v, "t_" + v[2:]))      # die-bus grant protocol: {data, valid} in, grant out
    res["pairs"] = pairs
    if not clk or not vin or not vout or not edges:
        res.update(verdict="REPLAY_NOT_APPLICABLE", why="no clock / input valid / output valid recognised")
        return finish(run, a, res)
    # reset prefix: until rst released (+2 edges)
    k0 = 0
    if rst:   # released level = the reset's value at the last edge; the prefix runs to its first edge at that level + 2
        rel = edges[-1].get(sig[rst][0])
        for k, e in enumerate(edges):
            if e.get(sig[rst][0]) == rel:
                k0 = k + 2
                break
    drive = [n for n in ins if n not in (clk,) and n not in rdy_in]
    stim = []
    for k, e in enumerate(edges):
        if k < k0 or any(b0(e, sig, n) for n in vin):
            stim.append([e.get(sig[n][0], "0") for n in drive])
    items = sum(1 for k, e in enumerate(edges) if k >= k0 and any(b0(e, sig, n) for n in vin))
    golden = [[e.get(sig[n][0], "x") for n in outs] for e in edges if any(b0(e, sig, n) for n in vout)]
    acc = accept_ii(edges, sig, pairs, k0)
    res["accept"] = acc
    if meta.get("fmt") == "mon":     # Verilator recording: no open-loop replay; recorded-dense or accept spacing
        rec_t0 = next((k for k, e in enumerate(edges) if k >= k0 and any(b0(e, sig, n) for n in vin)), 0)
        rec_tl = max((k for k, e in enumerate(edges) if any(b0(e, sig, n) for n in vout)), default=0)
        last_in = max((k for k, e in enumerate(edges) if k >= k0 and any(b0(e, sig, n) for n in vin)), default=rec_t0)
        dens = items / max(1, last_in - rec_t0 + 1)
        res.update(items=items, input_density=round(dens, 3), cycles_recorded=rec_tl - rec_t0 + 1,
                   ii_recorded=round((rec_tl - rec_t0 + 1) / items, 3) if items else None)
        if acc:
            res["verdict"], res["ii"] = "MEASURED_ACCEPT", acc["ii"]
        elif dens >= 0.9 and res["ii_recorded"]:
            res["verdict"], res["ii"] = "MEASURED_RECORDED", res["ii_recorded"]
        else:
            res["verdict"], res["ii"] = "NOT_MEASURABLE", None
        return finish(run, a, res)
    # generated top
    pv = {n: params[n] for n in pnames if params.get(n) is not None}
    def hexv(bits):
        bits = "".join(c if c in "01" else "0" for c in bits)
        return format(int(bits, 2), "x") if bits else "0"
    def binv(bits, wd):
        bits = "".join(c if c in "01" else "0" for c in (bits or "0"))
        return bits.rjust(wd, bits[0] if bits[0] in "01" and False else "0")[-wd:]
    W = [w[n] for n in drive]
    (run / "autoii_stim.hex").write_text("\n".join("".join(binv(v, wd) for v, wd in zip(row, W)) for row in stim) + "\n")
    tot = sum(W)
    lines = ["`timescale 1ns/1ps", "module ot_autoii_tb;",
             f"  reg {clk} = 0; always #0.5 {clk} = ~{clk};",
             f"  reg [{tot - 1}:0] mem [0:{len(stim) - 1}]; reg [{tot - 1}:0] cur; integer k = 0, cyc = 0, t0 = -1, tl = -1, nout = 0, fo;"]
    for n in drive:
        lines.append(f"  wire [{w[n] - 1}:0] {n};")
    for n in rdy_in:
        lines.append(f"  wire [{w[n] - 1}:0] {n} = {w[n]}'h{'f' * ((w[n] + 3) // 4)} ;")
    for n in outs:
        lines.append(f"  wire [{max(w.get(n, 1), 1) - 1}:0] {n};")
    off = tot
    for n in drive:
        off -= w[n]
        lines.append(f"  assign {n} = cur[{off + w[n] - 1}:{off}];")
    prm = ", ".join(f".{n}({v})" for n, v in pv.items())
    conn = ", ".join(f".{n}({n})" for n in ins + outs if n in w)
    lines.append(f"  {meta['block']} {'#(' + prm + ')' if prm else ''} dut ({conn});")
    hold = " || ".join(f"(|({v} & ~{r_}))" for v, r_ in pairs) or "1'b0"
    def act(n):
        return f"{n}[0]" if n.startswith(("f_", "t_")) and w[n] > 1 else f"(|{n})"
    VI = " || ".join(act(n) for n in vin)
    VO = " || ".join(act(n) for n in vout)
    lines += ["  initial begin",
              f"    $readmemb(\"{run / 'autoii_stim.hex'}\", mem); cur = mem[0]; fo = $fopen(\"{run / 'autoii_out.txt'}\", \"w\");",
              "  end",
              f"  always @(posedge {clk}) begin",
              "    cyc <= cyc + 1;",
              f"    if (k >= {k0} && t0 < 0 && ({VI})) t0 = cyc;",
              f"    if (!(k >= {k0} && ({hold}))) begin",
              f"      if (k + 1 < {len(stim)}) begin k = k + 1; cur <= mem[k]; end else cur <= {{{tot}{{1'b0}}}} | (cur & 0);",
              "    end",
              f"    if ({VO}) begin tl = cyc; nout = nout + 1; $fwrite(fo, \"%s\\n\", {{" + ", \"_\", ".join(
                  f"$sformatf(\"%b\", {n})" for n in outs) + "}); end",
              f"    if (cyc > {len(edges) * 4 + 1000} || (k + 1 >= {len(stim)} && nout >= {len(golden)} && cyc > tl + 64)) begin",
              "      $display(\"AUTOII t0 %0d tlast %0d nout %0d cyc %0d\", t0, tl, nout, cyc); $fclose(fo); $finish;",
              "    end",
              "  end",
              "endmodule"]
    tb = run / "ot_autoii_tb.sv"
    tb.write_text("\n".join(lines) + "\n")
    exe = run / "autoii.vvp"
    real = shutil.which("iverilog")
    cmd = [real, "-g2012", "-s", "ot_autoii_tb", "-o", str(exe)] + meta["defines"] + ["-I" + d for d in meta.get("incdirs", [])] + [str(tb)] + meta["sources"]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=meta["cwd"])
    if p.returncode:
        res.update(verdict="REPLAY_BUILD_FAIL", why=(p.stderr or p.stdout)[-600:])
        return finish(run, a, res)
    p = subprocess.run(["vvp", "-n", str(exe)], capture_output=True, text=True, cwd=run, timeout=a.timeout)
    m = re.search(r"AUTOII t0 (-?\d+) tlast (-?\d+) nout (\d+)", p.stdout)
    got = [ln.split("_") for ln in (run / "autoii_out.txt").read_text().split("\n") if ln] if (run / "autoii_out.txt").exists() else []
    gold = ["_".join(row) for row in golden]
    rep = ["_".join(row) for row in got]
    def norm(s):
        return s.replace("x", "0").replace("z", "0")
    exact = len(gold) == len(rep) and all(norm(x) == norm(y) for x, y in zip(gold, rep))
    t0, tl = (int(m.group(1)), int(m.group(2))) if m else (-1, -1)
    rec_t0 = next((k for k, e in enumerate(edges) if k >= k0 and any(b0(e, sig, n) for n in vin)), 0)
    rec_tl = max((k for k, e in enumerate(edges) if any(b0(e, sig, n) for n in vout)), default=0)
    res.update(items=items, outputs_recorded=len(gold), outputs_replayed=len(rep), exact=exact,
               cycles_replay=(tl - t0 + 1) if t0 >= 0 and tl >= t0 else None, cycles_recorded=rec_tl - rec_t0 + 1,
               ii_replay=round((tl - t0 + 1) / items, 3) if items and t0 >= 0 and tl >= t0 else None,
               ii_recorded=round((rec_tl - rec_t0 + 1) / items, 3) if items else None, params=pv)
    # input density of the recorded run (input-active edges / edges between the first and the last input): a dense
    # recorded stream already IS back-to-back, so its II (exact by the bench's own golden check) is the measurement
    last_in = max((k for k, e in enumerate(edges) if k >= k0 and any(b0(e, sig, n) for n in vin)), default=rec_t0)
    dens = items / max(1, last_in - rec_t0 + 1)
    res["input_density"] = round(dens, 3)
    if exact and res["ii_replay"]:
        res["verdict"], res["ii"] = "MEASURED_REPLAY", res["ii_replay"]
    elif acc:
        res["verdict"], res["ii"] = "MEASURED_ACCEPT", acc["ii"]
    elif dens >= 0.9 and res["ii_recorded"]:
        res["verdict"], res["ii"] = "MEASURED_RECORDED", res["ii_recorded"]
    else:
        res["verdict"], res["ii"] = "REPLAY_NOT_APPLICABLE", None
    if not exact:
        res["why"] = f"output sequence differs ({len(rep)} vs {len(gold)} transactions): closed-loop interface or handshake heuristic miss"
    return finish(run, a, res)


def finish(run, a, res):
    out = Path(a.out) if getattr(a, "out", None) else run / "autoii.json"
    out.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res.get(k) for k in ("block", "verdict", "items", "ii_replay", "ii_recorded", "exact", "why")}))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd_", required=True)
    r = sp.add_parser("record")
    r.add_argument("--block", required=True)
    r.add_argument("--run", required=True)
    r.add_argument("--timeout", type=int, default=3600)
    r.add_argument("cmd", nargs=argparse.REMAINDER)
    p = sp.add_parser("replay")
    p.add_argument("--run", required=True)
    p.add_argument("--out")
    p.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()
    return record(a) if a.cmd_ == "record" else replay(a)


if __name__ == "__main__":
    raise SystemExit(main())
