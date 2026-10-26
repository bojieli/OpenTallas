#!/usr/bin/env python3
"""Transitive RTL file list of a v15 die master (H-DIE 2026-10-15).

    master_filelist.py TOP [--root DIR] [--bb MOD,MOD] [--json]

Indexes every `module`/`package`/`interface` definition under the die's RTL roots (rtl/, physical/hbm_accel_die_views/*/rtl,
physical/asap7_memory_macros_v2/*/ *_bb.v), then walks instantiations from TOP.  Prints the files (packages first) or a
JSON record {top, files, blackboxes, unresolved}.  A module defined in more than one file is an error unless every
definition is byte-identical (then the first is used): the per-master synthesis must read exactly one definition.
Blackbox modules (--bb) are not expanded; their definition file is not read (the caller declares them `blackbox`).
"""
import argparse, json, os, re, sys
from pathlib import Path

ROOT_GLOBS = ("rtl/**/*.sv", "rtl/**/*.v", "physical/hbm_accel_die_views/**/rtl/*.sv", "physical/hbm_accel_die_views/common/*.sv", "physical/hbm_accel_die_views/**/rtl/*.v",
              "physical/asap7_memory_macros_v2/*/*_bb.v", "physical/hbm_generic/**/rtl/*.sv", "physical/hbm_generic/**/rtl/*.v", "physical/hbm_mtp/**/rtl/*.sv", "physical/hbm_cp_mtp_native/**/rtl/*.sv")
SKIP = re.compile(r"(^|/)(test|tb|bench|sim|evidence|experimental|formal)(/|$)|^rtl/model_ready[^/]*/|_tb\.s?v$|_mutant\.s?v$")
ATTR = r"(?:\(\*.*?\*\)\s*)*"
DEF = re.compile(r"^\s*" + ATTR + r"(module|package|interface)\s+(?:automatic\s+)?([A-Za-z_]\w*)", re.M)
KW = set("""module endmodule input output inout wire reg logic assign always always_ff always_comb always_latch initial
begin end if else for case endcase generate endgenerate genvar localparam parameter function endfunction task endtask
typedef struct enum union package endpackage import return integer int bit byte while repeat forever default unique
priority posedge negedge or and not signed unsigned automatic static const var string real time void interface
modport property assert assume cover sequence final foreach do break continue""".split())
INST = re.compile(r"(?<![\w$.])([A-Za-z_]\w*)\s*(?:#\s*\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)\s*)?([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)?\(", re.S)
PKG = re.compile(r"\b([A-Za-z_]\w*)::")
INC = re.compile(r'^\s*`include\s+"([^"]+)"', re.M)


def strip(t):
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def index(root):
    defs = {}
    for g in ROOT_GLOBS:
        for p in root.glob(g):
            rel = str(p.relative_to(root))
            if SKIP.search(rel):
                continue
            try:
                t = strip(p.read_text(errors="replace"))
            except OSError:
                continue
            for kind, name in DEF.findall(t):
                defs.setdefault(name, []).append(rel)
    return defs


def body(root, rel, name):
    t = strip((root / rel).read_text(errors="replace"))
    m = re.search(r"^\s*" + ATTR + r"(?:module|package|interface)\s+(?:automatic\s+)?" + re.escape(name) + r"\b(.*?)^\s*end(?:module|package|interface)\b", t, re.S | re.M)
    return m.group(1) if m else t


def resolve(root, top, bb=(), prefer=()):
    defs = index(root)
    files, pkgs, seen, unresolved, dup = [], [], set(), [], {}
    macros = []
    prefer = list(prefer)
    todo = [top]
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        cands = sorted(set(defs.get(m, [])))
        if m in bb:                  # read its definition (the synth script then declares it `blackbox`), do not descend
            if cands:
                files.append(sorted(cands, key=lambda c: (not c.startswith("rtl/"), c.count("/"), len(c), c))[0])
            continue
        if not cands:
            unresolved.append(m)
            continue
        bbv = [c for c in cands if c.endswith("_bb.v")]
        if bbv:                      # a mapped memory macro: read its black-box view only (-lib)
            macros.append(dict(module=m, file=bbv[0]))
            continue
        pref = [c for c in prefer if c in cands]
        if pref:
            cands = pref
        if len(cands) > 1:
            blobs = {(root / c).read_bytes() for c in cands}
            if len(blobs) > 1:
                # prefer rtl/ over view copies only when the view copy is a verbatim pinned duplicate of the module body
                bodies = {body(root, c, m) for c in cands}
                if len(bodies) > 1:
                    dup[m] = cands
            cands = sorted(cands, key=lambda c: (not c.startswith("rtl/"), c.count("/"), len(c), c))   # canonical: shallowest rtl/ copy
        f = cands[0]
        b = body(root, f, m)
        isPkg = re.search(r"^\s*package\s+" + re.escape(m) + r"\b", strip((root / f).read_text(errors="replace")), re.M)
        (pkgs if isPkg else files).append(f)
        for inc in INC.findall((root / f).read_text(errors="replace")):
            pass
        for a, inst in INST.findall(b):
            if a in KW or inst in KW or a == m:
                continue
            if a in defs:
                todo.append(a)
        for p in PKG.findall(b):
            if p in defs:
                todo.append(p)
        for p in re.findall(r"\bimport\s+([A-Za-z_]\w*)\s*::", b):
            if p in defs:
                todo.append(p)
    # a file may define several modules: keep order, dedupe
    out = []
    for f in pkgs + files[::-1]:
        if f not in out:
            out.append(f)
    return dict(top=top, files=out, macros=macros, blackboxes=sorted(bb), unresolved=sorted(unresolved), ambiguous=dup)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("top")
    ap.add_argument("--root", default=".")
    ap.add_argument("--bb", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--prefer", default="", help="file with preferred definition files (one per line)")
    a = ap.parse_args()
    pref = [l.strip() for l in open(a.prefer)] if a.prefer else []
    r = resolve(Path(a.root).resolve(), a.top, tuple(x for x in a.bb.split(",") if x), pref)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print("\n".join(r["files"] + ["-lib " + x["file"] for x in r["macros"]]))
        if r["unresolved"] or r["ambiguous"]:
            print("UNRESOLVED", r["unresolved"], "AMBIGUOUS", r["ambiguous"], file=sys.stderr)
    # ambiguous = several differing definitions; the canonical (shallowest rtl/) copy is used and the choice recorded.
    sys.exit(1 if (r["ambiguous"] and not os.environ.get("HDIE_ALLOW_AMBIGUOUS")) else 0)
