#!/usr/bin/env python3
"""RTLGAP2-HEADTB: complete a Verilator file list with the definitions of every missing (child) module.

port_bind.json rtl_files lists the files of the die's MASTERS; their children (SerDes column, SRAM macro models, link
layers ...) are not in it.  This loops: verilator --lint-only (top = --top) -> %Error-MODMISSING names -> add the defining
file from an index of SRC (rtl/ and physical/ .sv/.v), until nothing is missing.  Choice per module (logged in
--log json, with every alternative): never test/, pinned/, results/, *_bb.v (black boxes) or tb_ files; prefer rtl/ over
physical/, asap7_memory_macros_v2 over asap7_memory_macros, then the shortest path.  Fails if a module has no candidate.

    resolve_files.py --src SRC --filelist IN.f --out OUT.f --top TOP --verilator V [--extra file ...] [-- vflags...]
"""
import argparse
import json
import os
import re
import subprocess
import sys

MOD = re.compile(r"^\s*module\s+(\w+)", re.M)


def index(src):
    idx = {}
    for top in ("rtl", "physical"):
        for d, _, fs in os.walk(os.path.join(src, top)):
            for f in fs:
                if not f.endswith((".sv", ".v")):
                    continue
                p = os.path.join(d, f)
                try:
                    t = open(p, errors="replace").read()
                except OSError:
                    continue
                for m in MOD.findall(t):
                    idx.setdefault(m, []).append(p)
    return idx


def pick(src, cands):
    ok = [p for p in cands if not re.search(r"/(test|tests|pinned|results)/|_bb\.v$|/tb_[^/]*$", os.path.relpath(p, src))]
    if not ok:
        return None
    def key(p):
        r = os.path.relpath(p, src)
        return (0 if r.startswith("rtl/") else 1, 0 if "asap7_memory_macros_v2" in r else 1, len(r), r)
    return sorted(ok, key=key)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--filelist", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", required=True)
    ap.add_argument("--verilator", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--extra", nargs="*", default=[])
    a, vflags = ap.parse_known_args()
    vflags = [x for x in vflags if x != "--"]
    idx = index(a.src)
    base = [ln.strip() for ln in open(a.filelist) if ln.strip()]
    added, log = [], {}
    for it in range(40):
        fl = base + added
        open(a.out, "w").write("\n".join(fl) + "\n")
        r = subprocess.run([a.verilator, "--lint-only", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-WIDTH",
                            "-Wno-MULTIDRIVEN", "-Wno-MODDUP", "-Wno-TIMESCALEMOD", "--top-module", a.top, "-f", a.out]
                           + a.extra + vflags, capture_output=True, text=True)
        miss = sorted(set(re.findall(r"%Error-MODMISSING:.*Cannot find file containing module: '(\w+)'", r.stderr)))
        if not miss:
            errs = [ln for ln in r.stderr.splitlines() if ln.startswith("%Error")]
            json.dump(dict(iterations=it, added=log, lint_errors=errs[:50]), open(a.log, "w"), indent=1)
            print(f"RESOLVED after {it} iterations: +{len(added)} files, lint errors {len(errs)}")
            for e in errs[:10]:
                print(e)
            return 2 if errs else 0
        for m in miss:
            p = pick(a.src, idx.get(m, []))
            if p is None:
                json.dump(dict(iterations=it, added=log, unresolved=m, candidates=idx.get(m, [])), open(a.log, "w"), indent=1)
                print(f"UNRESOLVED module {m}: candidates {idx.get(m, [])}")
                return 2
            log[m] = dict(file=p, alternatives=[q for q in idx[m] if q != p])
            if p not in added:
                d = "+incdir+" + os.path.dirname(p)
                if d not in base + added:
                    added.append(d)
                added.append(p)
        print(f"iteration {it}: +{len(miss)} modules ({', '.join(miss[:8])}{' ...' if len(miss) > 8 else ''})", flush=True)
    print("NOT RESOLVED in 40 iterations")
    return 3


if __name__ == "__main__":
    sys.exit(main())
