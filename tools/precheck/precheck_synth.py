#!/usr/bin/env python3
"""precheck_synth.py -- PRECHECK-1119 checks 1-2 on the BOUND RTL of one type (yosys, generic gates, no liberty).

  precheck_synth.py --bind-out BIND/out --type TYPE --work DIR [--yosys BIN] [--depth-limit 14]

FOLD   flops after `proc; flatten` vs after `opt -full; opt_merge -share_all` (the merge that folded the S81 leaf
       station registers, hig 8,200 -> 2,048).  Reports the lost bits per register-name class (src hashes and lane
       indices normalised), so a station class that folds shows as one row.
DEPTH  after `synth -flatten -run coarse:` + `abc -g AND,NAND,OR,NOR,XOR,XNOR,MUX` the longest flop-to-flop / port path in
       generic 2-input gates (`ltp -noff`).  ASAP7 maps about 1.3-1.6 generic levels per cell level; the default limit
       is calibrated on signed types (see the record).
Undefined modules (hard cores, macros) become black boxes with the ports and parameters their instances use.
Heavy: run it through ot-run (one type per job).  Writes <work>/<type>.synth.json.
"""
import argparse
import collections
import os
import json
import re
import subprocess
import sys
from pathlib import Path

YOSYS = "/home/ubuntu/.local/opentallas-tools/bin/yosys"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "die_plan"))
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import cbc_rules as CBC  # noqa: E402  (owner r713: depth <= 13 levels, shared with the CBC generator)
_INST = re.compile(r"^\s*(?:\(\*[^)]*\*\)\s*)?([A-Za-z_]\w*)\s*(#\s*\((?:[^;]*?)\))?\s+\\?([A-Za-z_][\w.\[\]$]*)\s*\((.*?)\);", re.S | re.M)
_KW = {"module", "endmodule", "input", "output", "inout", "wire", "reg", "assign", "always", "if", "else", "begin", "end", "case",
       "endcase", "parameter", "localparam", "genvar", "generate", "endgenerate", "for", "function", "endfunction", "initial", "logic"}


def defined_modules(text):
    return set(re.findall(r"^\s*module\s+([A-Za-z_]\w*)", text, re.M))


def driven_names(text):
    """identifiers the module drives itself: assign LHS, nonblocking/blocking LHS, input ports"""
    d = set(re.findall(r"\bassign\s+\\?([A-Za-z_][\w$]*)", text))
    d |= set(re.findall(r"\b([A-Za-z_][\w$]*)\s*(?:\[[^\]]*\])?\s*<=", text))
    d |= set(re.findall(r"\binput\s+(?:wire\s+|logic\s+)?(?:\[[^\]]*\]\s*)?([A-Za-z_]\w*)", text))
    d |= set(re.findall(r"\b(?:parameter|localparam)\s+(?:\w+\s+)?(?:\[[^\]]*\]\s*)?([A-Za-z_]\w*)", text))
    return d


_DECL = re.compile(r"\b(?:wire|reg|logic|input|output|inout)\s+(?:wire\s+|reg\s+|logic\s+)?(?:signed\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?\\?([A-Za-z_][\w$]*)")


def decl_widths(texts):
    w = {}
    for t in texts:
        for m in _DECL.finditer(t):
            w[m.group(3)] = abs(int(m.group(1)) - int(m.group(2))) + 1 if m.group(1) else 1
    return w


def expr_width(expr, widths):
    """bit width of a port connection: a name (its declared width), a bit/part select, a sized literal, a {concat}"""
    e = expr.strip()
    if not e:
        return 1
    if e.startswith("{") and e.endswith("}"):
        return max(1, sum(expr_width(x, widths) for x in re.split(r",(?![^{]*})", e[1:-1])))
    m = re.fullmatch(r"(\d+)'[sS]?[bBhHdDoO][0-9a-fA-FxXzZ_]+", e)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"\\?([A-Za-z_][\w$]*)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]", e)
    if m:
        return abs(int(m.group(2)) - int(m.group(3))) + 1
    m = re.fullmatch(r"\\?([A-Za-z_][\w$]*)\s*\[[^\]:]+\]", e)
    if m:
        return 1
    m = re.fullmatch(r"\\?([A-Za-z_][\w$]*)", e)
    if m:
        return widths.get(m.group(1), 1)
    return 64


def blackbox_stubs(texts):
    """(* blackbox *) stubs for every instantiated module that no text defines: ports = the named connections (input when
    the connected signal is driven in the parent, else output; an inout stub makes yosys resolve driver conflicts to x and
    drop the flops behind them), params = the named parameter overrides"""
    defined = set()
    driven = set()
    for t in texts:
        defined |= defined_modules(t)
        driven |= driven_names(t)
    ports, params = collections.defaultdict(dict), collections.defaultdict(set)
    pw = collections.defaultdict(lambda: collections.defaultdict(int))
    widths = decl_widths(texts)
    for t in texts:
        for m in _INST.finditer(t):
            mod = m.group(1)
            if mod in _KW or mod in defined:
                continue
            for p, expr in re.findall(r"\.\s*([A-Za-z_]\w*)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)", m.group(4)):
                ids = re.findall(r"\\?([A-Za-z_][\w$]*)", expr)
                dirn = "input" if (not ids or any(i in driven for i in ids) or "'" in expr) else "output"
                if ports[mod].get(p) != "input":
                    ports[mod][p] = dirn
                pw[mod][p] = max(pw[mod][p], expr_width(expr, widths))
            if m.group(2):
                for p in re.findall(r"\.\s*([A-Za-z_]\w*)\s*\(", m.group(2)):
                    params[mod].add(p)
    out = []
    for mod in sorted(ports):
        ps = sorted(ports[mod])
        pr = sorted(params[mod])
        hdr = ("#(" + ", ".join(f"parameter {p} = 0" for p in pr) + ") ") if pr else ""
        out.append(f"(* blackbox *) module {mod} {hdr}(" + ", ".join(ps) + ");\n"
                   + "".join(f"  {ports[mod][p]} [{max(1, pw[mod][p]) - 1}:0] {p};\n" for p in ps) + "endmodule\n")
    return "".join(out)


def bound_sv(bo, tn):
    """the bind's RTL file of a type: rtl/<type>.sv or rtl/s81p_<type>.sv (S81 slice partitions)"""
    for n in (f"{tn}.sv", f"s81p_{tn}.sv"):
        if (bo / "rtl" / n).is_file():
            return bo / "rtl" / n
    c = sorted((bo / "rtl").glob(f"*{tn}.sv"))
    return c[0] if c else bo / "rtl" / f"{tn}.sv"


def stat_dffs(path):
    n = 0
    for ln in Path(path).read_text(errors="replace").splitlines():
        m = re.match(r"\s*(\d+)\s+\$_?\w*dff\w*", ln, re.I) or re.match(r"\s*\$_?\w*dff\w*_?\s+(\d+)", ln, re.I)
        if m:
            n += int(m.group(1))
    return n


def dff_bits_by_name(il_dump):
    """{reg class: bits} from a `dump` of $dff/$adff cells (Q wire names)"""
    out = collections.Counter()
    cur = None
    width = 0
    for ln in Path(il_dump).read_text(errors="replace").splitlines():
        m = re.match(r"\s*cell \$\w*dff\w* ", ln)
        if m:
            cur, width = "?", 1
            continue
        if cur is not None:
            m = re.match(r"\s*parameter \\WIDTH (\d+)", ln)
            if m:
                width = int(m.group(1))
            m = re.match(r"\s*connect \\Q (.*)", ln)
            if m:
                cur = m.group(1)
            if ln.strip() == "end":
                out[reg_class(cur)] += width
                cur = None
    return out


def reg_class(sig):
    s = re.sub(r"\[\d+(?::\d+)?\]", "", sig.split()[0] if sig else "?").lstrip("\\")
    s = re.sub(r"src_[0-9a-f]{8,}", "src_H", s)
    return re.sub(r"_\d+_", "_N_", s)[-80:]


def run(a):
    bo = Path(a.bind_out)
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    sv = bound_sv(bo, a.type)
    cells = bo / "rtl" / "bind_cells.sv"
    texts = [sv.read_text(errors="replace")] + ([cells.read_text(errors="replace")] if cells.is_file() else [])
    stub = work / f"{a.type}.stubs.sv"
    stub.write_text(blackbox_stubs(texts))
    pre, post, dpre, dpost, ltp = (work / f"{a.type}.{k}" for k in ("pre.stat", "post.stat", "pre.il", "post.il", "ltp.txt"))
    top = (defined_modules(texts[0]) or {a.type}).pop() if len(defined_modules(texts[0])) == 1 else a.type
    reads = f"read_verilog -sv {stub}\n" + (f"read_verilog -sv {cells}\n" if cells.is_file() else "") + f"read_verilog -sv {sv}\n"
    ys = work / f"{a.type}.ys"
    ys.write_text(reads + f"hierarchy -top {top}\nproc\nflatten\nopt_clean\ntee -q -o {pre} stat\nselect -set ff t:$*dff*\n"
                  f"tee -q -o {dpre} dump @ff\nopt -full\nopt_merge -share_all\nopt_clean\ntee -q -o {post} stat\nselect -set ff2 t:$*dff*\n"
                  f"tee -q -o {dpost} dump @ff2\n"
                  + ("" if a.no_depth else f"synth -flatten -run coarse:\nabc -g AND,NAND,OR,NOR,XOR,XNOR,MUX\nopt_clean\ntee -q -o {ltp} ltp -noff\n"))
    r = subprocess.run([a.yosys, "-q", "-s", str(ys)], capture_output=True, text=True, timeout=a.timeout)
    rec = dict(type=a.type, rc=r.returncode, err=(r.stderr or "")[-400:])
    if r.returncode == 0:
        b0, b1 = dff_bits_by_name(dpre), dff_bits_by_name(dpost)
        lost = {k: b0[k] - b1.get(k, 0) for k in b0 if b0[k] > b1.get(k, 0)}
        rec.update(dff_bits_pre=sum(b0.values()), dff_bits_post=sum(b1.values()),
                   fold_classes=sorted(lost.items(), key=lambda kv: -kv[1])[:20])
        if ltp.is_file():
            ls = [int(x) for x in re.findall(r"Longest topological path in \S+ \(length=(\d+)\)", ltp.read_text())]
            rec["depth_generic"] = max(ls) if ls else None
            rec["depth_limit"] = a.depth_limit
    (work / f"{a.type}.synth.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec.get(k) for k in ("type", "rc", "dff_bits_pre", "dff_bits_post", "depth_generic")}))
    return 0 if r.returncode == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind-out", required=True)
    ap.add_argument("--type", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--yosys", default=YOSYS)
    ap.add_argument("--no-depth", action="store_true")
    ap.add_argument("--timeout", type=int, default=3000)
    ap.add_argument("--depth-limit", type=int, default=CBC.DEPTH_LEVELS_MAX)
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
