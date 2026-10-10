#!/usr/bin/env python3
"""RTL-BOUNDARY (stream struct-close, 2026-10-09): submit-time check of the registered-boundary rule (owner: register every
block boundary; no logic between a pin and its flop).  Batch drive-0212/0313: sp-ictl (in->out -815), sp-candparse
(-502), sp-candfmt (-354), pi-s81hdisp (inputs -310), qfd_pc_head_owner_cl (ack_data -> mem decode -487) all passed
reg2reg and failed only on UNREGISTERED boundaries, each after a full queue + synth + place + CTS cycle.

The job's top is elaborated at its SOURCE COMMIT with the fleet's yosys (0.68 = the ORFS synthesis front end):
    read_verilog -sv -DSYNTHESIS <sources>; chparam <params> <top>; hierarchy -top; proc; flatten; opt_clean; techmap
and the gate-level netlist (write_json) is scanned (no abc, no timing; a cheap structural count):
  * in->out  : an output bit reachable from a data input through combinational gates only (no flop on the way);
  * in->reg  : gate levels from a data input pin to any flop D / enable / sync-reset pin;
  * reg->out : gate levels from any flop Q (or macro output) to an output pin.
Clocks and asynchronous resets (ports that reach a flop clock / async-reset pin) are excluded.  Black boxes (macros)
break paths like flops.  Gate levels count every 2-input-equivalent gate ($_NOT_ / $_BUF_ count 0); techmap leaves
adders as ripple chains, so arithmetic at a boundary reads deep, by design.
Verdict: findings are WARNINGS by default; a spec with "registered_io": true -- and (review-0443 X4) every spec whose name
ends in -cl / -cx unless it sets "registered_io": false or "rtl_boundary": {"waive": "<reason>"} -- is REFUSED on any in->out path or a depth
> N (spec "rtl_boundary": {"levels": N}, default 16).  SKIP when the recipe's sources / top are not readable, the
sources exceed the size cap, or yosys fails / times out (never blocks intake on its own failure).

    rtl_boundary.py check JOB.json [--repo R]     # print the result (exit 3 on REFUSE)
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

YOSYS = os.environ.get("OT_RB_YOSYS") or next(
    (p for p in (str(Path.home() / ".local/opentallas-tools/yosys-0.68/bin/yosys"), "/usr/bin/yosys") if Path(p).exists()),
    "yosys")
LEVELS = 16   # techmap ripple arithmetic on a pin FIFO's pointer reads 10-13; the failing batch read 20-76
SRC_CAP = 2_000_000          # bytes of RTL; bigger tops are skipped (the check must stay cheap at intake)
TIMEOUT = int(os.environ.get("OT_RB_TIMEOUT", "45"))   # intake runs in the daemon tick: big tops SKIP
CACHE = Path(os.environ.get("CL_STATE", str(Path.home() / ".local/state/closure_loop"))) / "rtl_boundary_cache.json"
SEQ = re.compile(r"^\$_(S?DFF|DFFE|SDFFE|SDFFCE|ALDFF|ALDFFE|DFFSR|DFFSRE|DLATCH|SR)")
ZERO = {"$_BUF_", "$_NOT_"}
MASTER_RE = re.compile(r"(?:physical/qwen_die_masters/jobs/)?route_master\.sh\s+([A-Za-z0-9_.-]+)")


def _cfg_vars(text: str) -> dict:
    out = {}
    for m in re.finditer(r"^\s*([A-Z_][A-Z0-9_]*)=(\(.*?\)|'[^']*'|\"[^\"]*\"|\S+)", text, re.M | re.S):
        out[m.group(1)] = m.group(2)
    return out


def _params(tokens: list[str]) -> dict:
    p = {}
    for i, t in enumerate(tokens):
        if t == "--param" and i + 1 < len(tokens) and "=" in tokens[i + 1]:
            k, v = tokens[i + 1].split("=", 1)
            p[k] = v
    return p


WFC_TOKPIPE_RE = re.compile(r"tools/dsrom_wfc_tokpipe_physical\.py\s+prep\b.*?--inst\s+(src|stg)\b")
WFC_MACRO_BB = "physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2_bb.v"


def _module_params(text: str, top: str) -> set:
    """parameter names declared in the #( ... ) header of module `top`"""
    m = re.search(r"\bmodule\s+" + re.escape(top) + r"\s*#\s*\((.*?)\)\s*\(", text, re.S)
    return set(re.findall(r"\bparameter\b(?:\s+(?:integer|int|logic|bit|signed|unsigned|\[[^\]]*\]))*\s+([A-Za-z_]\w*)",
                          m.group(1))) if m else set()


def recipe(spec: dict, show) -> dict | None:
    """{"top", "sources", "params", "incdirs"} from the job's route command at its source commit, or None.
    drive-resume (review-0542 AC1): an explicit spec "rtl_boundary": {"top": ..., "sources": [...], "params": {...}}
    wins; tools/dsrom_wfc_tokpipe_physical.py prep --inst src|stg (the WFC SOURCE / STAGE masters) is read from its
    basis json (physical/dsrom_wfc_tokpipe/<inst>_basis.json params that the top declares)."""
    cfg = spec.get("rtl_boundary") if isinstance(spec.get("rtl_boundary"), dict) else {}
    if cfg.get("top") and cfg.get("sources"):
        return {"top": cfg["top"], "sources": list(cfg["sources"]), "params": {k: str(v) for k, v in (cfg.get("params") or {}).items()},
                "incdirs": list(cfg.get("incdirs") or ["rtl/common"])}
    cmd = ((spec.get("stages") or {}).get("route") or {}).get("cmd") or ""
    commit = spec["source"]["commit"]
    w = WFC_TOKPIPE_RE.search(cmd)
    if w:
        inst = w.group(1)
        top = f"ot_dsrom_wfc_tokpipe_{inst}"
        top_src = f"rtl/dsrom_sys/mtp/{top}.sv"
        basis, text = show(commit, f"physical/dsrom_wfc_tokpipe/{inst}_basis.json"), show(commit, top_src)
        if basis is None or text is None:
            return None
        try:
            bp = json.loads(basis).get("params") or {}
        except ValueError:
            return None
        declared = _module_params(text, top)
        srcs = [top_src, "rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc_tokpipe.sv"]
        if inst == "src" and int(bp.get("REC_SRAM", 0)):
            srcs.append(WFC_MACRO_BB)
        return {"top": top, "sources": srcs, "params": {k: str(v) for k, v in bp.items() if k in declared},
                "incdirs": ["rtl/common"]}
    m = MASTER_RE.search(cmd)
    if m:
        text = show(commit, f"physical/qwen_die_masters/cfg/{m.group(1)}.env")
        if text is None:
            return None
        v = _cfg_vars(text)
        srcs = shlex.split(v.get("SRCS", "''"))[0].split() if v.get("SRCS") else []
        ptoks = shlex.split(v.get("PARAMS", "()").strip("()")) if v.get("PARAMS") else []
        top = shlex.split(v.get("TOP", ""))[0] if v.get("TOP") else None
        return {"top": top, "sources": srcs, "params": _params(ptoks), "incdirs": ["rtl/common"]} if top else None
    try:
        toks = shlex.split(cmd.replace(";", " ; "))
    except ValueError:
        return None
    srcs = [toks[i + 1] for i, t in enumerate(toks) if t == "--source" and i + 1 < len(toks)]
    top = None
    if "--top" in toks:
        top = toks[toks.index("--top") + 1]
    for i, t in enumerate(toks):
        if t.endswith("route_mtp.sh") and i + 2 < len(toks):
            top = toks[i + 2]
        if t.endswith("route_view.sh") and i + 4 < len(toks):     # route_view.sh <label> <die> <master> <top-source>
            top, srcs = toks[i + 3], srcs + [toks[i + 4]]
            em = re.search(r"\bSRCS='([^']*)'", cmd)
            if em:
                srcs += em.group(1).split()
    srcs = [s for s in srcs if s.endswith((".sv", ".v")) and "{" not in s]
    if not top or not srcs:
        return None
    return {"top": top, "sources": srcs, "params": _params(toks), "incdirs": ["rtl/common"]}


def analyse(netlist: dict, top: str) -> dict:
    mods = netlist["modules"]
    mod = mods.get(top) or next((m for m in mods.values() if str((m.get("attributes") or {}).get("top", "0")).strip("0") != ""),
                                None) or next(m for n, m in mods.items() if top in n)
    ports = mod["ports"]
    in_bits, out_bits = {}, {}
    for name, p in ports.items():
        for i, b in enumerate(p["bits"]):
            if isinstance(b, int):
                (in_bits if p["direction"] == "input" else out_bits)[b] = f"{name}[{i}]" if len(p["bits"]) > 1 else name
    drivers, sinks, seq_d, seq_q, clk_bits = {}, {}, set(), set(), set()
    for cname, c in mod["cells"].items():
        t = c["type"]
        dirs = c.get("port_directions", {})
        conns = c["connections"]
        if SEQ.match(t) or not t.startswith("$_"):       # flops, latches, black boxes / macros break paths
            for pn, bits in conns.items():
                for b in bits:
                    if not isinstance(b, int):
                        continue
                    if dirs.get(pn) == "output":
                        seq_q.add(b)
                    elif pn in ("C", "R", "S", "CLK", "clk", "CLR", "SET") and SEQ.match(t) and not t.startswith(("$_SDFF", "$_SDFFE", "$_SDFFCE")):
                        clk_bits.add(b)
                    elif pn == "C" or pn.lower() in ("clk", "clock"):
                        clk_bits.add(b)
                    else:
                        seq_d.add(b)
            continue
        ins = [b for pn, bits in conns.items() if dirs.get(pn) == "input" for b in bits if isinstance(b, int)]
        outs = [b for pn, bits in conns.items() if dirs.get(pn) == "output" for b in bits if isinstance(b, int)]
        w = 0 if t in ZERO else 1
        for o in outs:
            drivers[o] = (ins, w)
    # clocks / async resets reached through buffers / inverters only
    ctrl_ports = set()
    memo_src = {}

    def roots(b, depth=0):
        if b in memo_src:
            return memo_src[b]
        r = set()
        if b in in_bits:
            r.add(b)
        elif b in drivers and depth < 6:
            ins, w = drivers[b]
            if w == 0:
                for i in ins:
                    r |= roots(i, depth + 1)
        memo_src[b] = r
        return r
    for b in clk_bits:
        ctrl_ports |= roots(b)
    data_in = {b for b in in_bits if b not in ctrl_ports}
    sys.setrecursionlimit(100000)
    memo = {}

    def depth(b):
        """(levels from a data input or -1, levels from a flop/macro output or -1) at net bit b"""
        if b in memo:
            return memo[b]
        memo[b] = (-1, -1)
        if b in data_in:
            r = (0, -1)
        elif b in seq_q:
            r = (-1, 0)
        elif b in drivers:
            ins, w = drivers[b]
            di, dq = -1, -1
            for i in ins:
                a, q = depth(i)
                if a >= 0:
                    di = max(di, a + w)
                if q >= 0:
                    dq = max(dq, q + w)
            r = (di, dq)
        else:
            r = (-1, -1)
        memo[b] = r
        return r
    in2reg = max(((depth(b)[0], b) for b in seq_d), default=(-1, None))
    io = [(depth(b)[0], n) for b, n in out_bits.items() if depth(b)[0] >= 0]
    r2o = max(((depth(b)[1], n) for b, n in out_bits.items()), default=(-1, None))
    io.sort(reverse=True)
    return {"in_to_out_bits": len(io), "in_to_out_max": io[0][0] if io else -1,
            "in_to_out_example": [n for _, n in io[:3]],
            "in_to_reg_max": in2reg[0], "reg_to_out_max": r2o[0], "reg_to_out_example": r2o[1],
            "cells": len(mod["cells"]), "ctrl_ports": sorted({in_bits[b] for b in ctrl_ports})[:8]}


def check(spec: dict, show, repo: str | None = None) -> dict:
    cfg = spec.get("rtl_boundary", {})
    if cfg is False or (isinstance(cfg, dict) and cfg.get("skip")):
        return {"verdict": "SKIP", "message": "rtl_boundary opted out"}
    levels = int((cfg or {}).get("levels", LEVELS)) if isinstance(cfg, dict) else LEVELS
    # review-0443 X4: REFUSE by default for new dual-track structural specs (name ending -cl / -cx, the registered-boundary
    # rule's own lines); WARN for everything else.  "registered_io": false or "rtl_boundary": {"waive": "<reason>"} downgrades
    # a -cl/-cx spec to WARN (a documented, intentional unregistered port, e.g. TA15's immediate-drop ready).
    name = str(spec.get("name", ""))
    waived = isinstance(cfg, dict) and bool(cfg.get("waive"))
    if "registered_io" in spec:
        strict = bool(spec.get("registered_io"))
    else:
        strict = bool(re.search(r"-c[lx]$", name)) and not waived
    r = recipe(spec, show)
    if not r:
        return _cannot_run(spec, "sources / top not readable from the recipe")
    commit = spec["source"]["commit"]
    import hashlib
    ckey = hashlib.sha256(json.dumps([commit, r, levels], sort_keys=True).encode()).hexdigest()[:24]
    try:
        cache = json.loads(CACHE.read_text())
    except Exception:  # noqa: BLE001
        cache = {}
    if ckey in cache:
        res = dict(cache[ckey]); res["cached"] = True
        return _verdict(res, r, levels, strict)
    with tempfile.TemporaryDirectory(prefix="rtlb_") as td:
        tdp = Path(td)
        files, total = [], 0
        for s in r["sources"]:
            t = show(commit, s)
            if t is None:
                return _cannot_run(spec, f"{s} not at {commit[:12]}")
            total += len(t)
            # yosys cannot elaborate procedural $fatal / $error (an `initial if (bad) $fatal(...)` parameter guard): the
            # scan only needs structure, so such calls become $display (review-0542 AC1: the WFC SOURCE ctrl has them)
            t = re.sub(r"\$(fatal|error)\s*\(\s*\d+\s*,", "$display(", t)
            t = re.sub(r"\$(fatal|error)\b", "$display", t)
            f = tdp / s
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(t)
            files.append(str(f))
        if total > SRC_CAP:
            return _cannot_run(spec, f"{total} B of RTL > cap {SRC_CAP}")
        for inc in r["incdirs"]:                       # include files the sources pull in (`include "x.svh")
            for s in r["sources"]:
                for name in re.findall(r'`include\s+"([^"]+)"', (tdp / s).read_text()):
                    t = show(commit, f"{inc}/{name}")
                    if t is not None:
                        (tdp / inc).mkdir(parents=True, exist_ok=True)
                        (tdp / inc / name).write_text(t)
        chp = " ".join(f"-set {k} {v}" for k, v in r["params"].items() if re.fullmatch(r"-?\d+|'?[0-9a-fA-FxXhHbBdD']+", v))
        script = (f"read_verilog -sv -DSYNTHESIS " + " ".join(f"-I{tdp / i}" for i in r["incdirs"]) + " "
                  + " ".join(files) + "; "
                  + (f"chparam {chp} {r['top']}; " if chp else "")
                  + f"hierarchy -top {r['top']}; proc; flatten; opt_clean; techmap; opt_clean; write_json {tdp / 'n.json'}")
        try:
            p = subprocess.run([YOSYS, "-q", "-p", script], capture_output=True, text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            return _cannot_run(spec, f"yosys > {TIMEOUT} s")
        if p.returncode or not (tdp / "n.json").exists():
            return _cannot_run(spec, "yosys failed: " + (p.stderr or p.stdout)[-300:])
        res = analyse(json.loads((tdp / "n.json").read_text()), r["top"])
    try:
        cache[ckey] = res
        CACHE.write_text(json.dumps(cache))
    except Exception:  # noqa: BLE001
        pass
    return _verdict(res, r, levels, strict)


def _cannot_run(spec: dict, why: str) -> dict:
    """review-0542 AC1: a spec that explicitly asks for the check ("registered_io": true) is REFUSED when the check
    cannot run -- never a silent SKIP.  Fix: give "rtl_boundary": {"top", "sources", "params"} or a waiver
    ("rtl_boundary": {"waive": "<reason>"}).  Default-strict -cl/-cx names without the flag keep SKIP."""
    cfg = spec.get("rtl_boundary") if isinstance(spec.get("rtl_boundary"), dict) else {}
    if spec.get("registered_io") is True and not cfg.get("waive"):
        return {"verdict": "REFUSE", "message": f"rtl_boundary: registered_io:true requested but the check cannot run "
                                                f"({why}); add \"rtl_boundary\": {{\"top\": ..., \"sources\": [...], "
                                                f"\"params\": {{...}}}} or \"rtl_boundary\": {{\"waive\": \"<reason>\"}}"}
    if spec.get("registered_io") is True:
        return {"verdict": "WARN", "message": f"rtl_boundary: check could not run ({why}); waived: {cfg['waive']}"}
    return {"verdict": "SKIP", "message": f"rtl_boundary: {why}"}


def _verdict(res: dict, r: dict, levels: int, strict: bool) -> dict:
    res = dict(res)
    res.update(top=r["top"], levels=levels, strict=strict)
    bad = []
    if res["in_to_out_bits"]:
        bad.append(f"{res['in_to_out_bits']} output bit(s) combinational from data inputs (max {res['in_to_out_max']} "
                   f"levels, e.g. {', '.join(res['in_to_out_example'])})")
    if res["in_to_reg_max"] > levels:
        bad.append(f"input->register {res['in_to_reg_max']} gate levels > {levels}")
    if res["reg_to_out_max"] > levels:
        bad.append(f"register->output {res['reg_to_out_max']} gate levels > {levels} (e.g. {res['reg_to_out_example']})")
    if not bad:
        res.update(verdict="PASS", message=f"rtl_boundary {r['top']}: registered boundary (in->reg {res['in_to_reg_max']}, "
                                            f"reg->out {res['reg_to_out_max']} levels)")
    elif strict:
        res.update(verdict="REFUSE", message=f"rtl_boundary {r['top']} (registered_io): " + "; ".join(bad))
    else:
        res.update(verdict="WARN", message=f"rtl_boundary {r['top']}: " + "; ".join(bad))
    return res


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("file")
    c.add_argument("--repo", default=os.environ.get("CL_REPO", "/home/ubuntu/OpenTallas"))
    a = ap.parse_args(argv)

    def show(commit, path):
        q = subprocess.run(["git", "-C", a.repo, "show", f"{commit}:{path}"], capture_output=True, text=True, timeout=60)
        return q.stdout if q.returncode == 0 else None
    spec = json.loads(Path(a.file).read_text())
    spec = spec.get("spec", spec)
    res = check(spec, show, a.repo)
    print(json.dumps(res, indent=1))
    return 3 if res["verdict"] == "REFUSE" else 0


if __name__ == "__main__":
    sys.exit(main())
