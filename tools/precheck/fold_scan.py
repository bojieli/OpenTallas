#!/usr/bin/env python3
"""fold_scan.py -- PRECHECK-1119 FOLD on a kit's synthesis output (FABLE-FIX-S81-LEAF's method, 11-18): declared
register bits of the bound RTL per register class vs the flops of that class in the kit's 1_2_yosys.v.

  fold_scan.py --kit-work KIT/work [--min-bits 64] [--frac 0.6] [--json OUT]

Light (text only), runs minutes after a kit starts (synth is its first stage), long before place/route.  A class whose
netlist flops are < frac x its declared bits lost registers to synthesis merging (S81 leaf: hig 8,200 -> 2,048, ln cst_hi
4,112 -> 1,024).  Memories (native_memory) and ot_dp_st station modules (kept by ot_dp_st:q) are not counted.

Why not a private yosys run: proc/flatten/opt_merge -share_all and even `synth -run coarse:` on the kit's own inputs
keep the hig stations (11-19: 6 of 8,200 bits lost); only the ORFS synth flow folds them, so the kit netlist is the
evidence.
"""
import argparse
import collections
import glob
import json
import re
import sys
from pathlib import Path

REG = re.compile(r"^\s*reg\s+(?:signed\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?\\?([A-Za-z_][\w$.]*)\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*;", re.M)
FF = re.compile(r"^\s*\S*DFF\S*\s+(\\?\S+)\s*\(", re.M)


def reg_class(name):
    s = name.lstrip("\\")
    s = re.sub(r"^u_bound\.", "", s)
    s = re.sub(r"\$_?DFF\w*_?$", "", s)
    s = re.sub(r"\[\d+\]", "", s)
    s = re.sub(r"src_[0-9a-f]{8,}", "src_H", s)
    s = re.sub(r"_\d+_", "_N_", s)
    return s


def declared(texts):
    out = collections.Counter()
    for t in texts:
        for m in REG.finditer(t):
            w = abs(int(m.group(1)) - int(m.group(2))) + 1 if m.group(1) else 1
            d = abs(int(m.group(4)) - int(m.group(5))) + 1 if m.group(4) else 1
            out[reg_class(m.group(3))] += w * d
    return out


def netlist_flops(text):
    out = collections.Counter()
    for m in FF.finditer(text):
        out[reg_class(m.group(1))] += 1
    return out


def scan(kit_work, min_bits=64, frac=0.6):
    kw = Path(kit_work)
    cfg = (kw / "config.mk").read_text(errors="replace")
    m = re.search(r"^export\s+DESIGN_NAME\s*\??=\s*(\S+)", cfg, re.M)
    top = m.group(1) if m else None
    files = [f for f in re.search(r"^export\s+VERILOG_FILES\s*\??=\s*(.*)$", cfg, re.M).group(1).split()
             if Path(f).name.startswith(top or "~")] if top else []
    texts = [(kw / f[len("/work/"):]).read_text(errors="replace") for f in files if f.startswith("/work/")]
    nl = sorted(glob.glob(str(kw / "run/results/*/*/base/1_2_yosys.v")))
    if not nl:
        return dict(kit=str(kw), top=top, error="no 1_2_yosys.v yet")
    dec = declared(texts)
    got = netlist_flops(Path(nl[0]).read_text(errors="replace"))
    folds = []
    for c, b in dec.items():
        if b < min_bits or "native_memory" in c:
            continue
        n = got.get(c, 0)
        if n and n < frac * b:
            folds.append([c, b, n])
    folds.sort(key=lambda r: -(r[1] - r[2]))
    return dict(kit=str(kw), top=top, netlist=nl[0], declared_bits=sum(dec.values()), netlist_flops=sum(got.values()),
                folds=folds, lost=sum(b - n for _, b, n in folds))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit-work", required=True)
    ap.add_argument("--min-bits", type=int, default=64)
    ap.add_argument("--frac", type=float, default=0.6)
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    r = scan(a.kit_work, a.min_bits, a.frac)
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1))
    print(json.dumps({k: r.get(k) for k in ("top", "declared_bits", "netlist_flops", "lost", "error")}))
    for c, b, n in r.get("folds", [])[:12]:
        print(f"FOLD {c}: {b} declared bits -> {n} flops")
    return 0


if __name__ == "__main__":
    sys.exit(main())
