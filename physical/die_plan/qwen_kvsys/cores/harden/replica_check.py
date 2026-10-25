#!/usr/bin/env python3
"""PATH-KV-ASTK2 10-25: post-synthesis register-replica COUNT gate (fails closed, runs before floorplan).

LEC cannot see a merged replica: yosys opt_merge folds same-D register copies into one flop and the netlist stays
equivalent (GEOM 10:05 FAIL on ASTK W2: per-zone kt_r/ke_r survived only in zn_2, lo_r 8/4/2/1).  This gate counts the
sequential cells under every declared replica instance in the synthesized netlist and FAILS when an instance is missing,
an extra one appears, or its flop count differs from the declared width.

Netlist forms accepted: the hierarchical yosys netlist (1_2_yosys.v: keep_hierarchy modules stay modules; instances are
expanded from the top) and the flat netlist written from 1_synth.odb (kept-instance cells named `<inst path>/<cell>`).
Both are walked into one list of (full name, cell type); a sequential cell's instance = its name up to the last '/'.

Spec (JSON): {"rules": [{"name": str, "inst_re": regex over the instance path (capture groups = group key, joined ','),
"groups": [expected keys], "ff_per_inst": int, "module": optional module name (checked when the netlist keeps it)}]}

usage: replica_check.py --expect SPEC --netlist N [--top TOP] [--out OUT.json]   exit 0 PASS, 1 FAIL, 2 error
"""
import argparse
import json
import re
import sys
from pathlib import Path

SEQ_RE = re.compile(r"^(DFF|SDF|ASYNC_DFF|DHL|DLL|ICG)")
KW = {"module", "endmodule", "input", "output", "inout", "wire", "reg", "assign", "supply0", "supply1", "parameter",
      "localparam", "always", "initial", "tri", "wand", "wor", "genvar", "generate", "endgenerate", "defparam"}
CELL_RE = re.compile(r"^\s*(\\\S+|[A-Za-z_][\w$]*)\s+(\\\S+|[A-Za-z_][\w$\[\]\.]*)\s*\(")


def parse(text):
    """{module: [(type, inst name)]} from structural Verilog (attributes / comments dropped)."""
    text = re.sub(r"\(\*.*?\*\)", " ", text, flags=re.S)
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    mods, cur = {}, None
    for line in text.splitlines():
        line = re.sub(r"//.*", "", line) if not line.lstrip().startswith("\\") else line
        m = re.match(r"^\s*module\s+(\\\S+|[\w$]+)", line)
        if m:
            cur = m.group(1).lstrip("\\")
            mods[cur] = []
            continue
        if re.match(r"^\s*endmodule\b", line):
            cur = None
            continue
        if cur is None:
            continue
        m = CELL_RE.match(line)
        if m and m.group(1) not in KW:
            mods[cur].append((m.group(1).lstrip("\\"), m.group(2).lstrip("\\")))
    return mods


def flatten(mods, top=None):
    """[(full name, type, parent module)] of every leaf cell reachable from top ('/' between hierarchy levels)."""
    if top is None:
        used = {t for cells in mods.values() for t, _ in cells}
        tops = [m for m in mods if m not in used]
        if len(tops) != 1:
            raise ValueError(f"cannot pick the top module: {tops[:6]}")
        top = tops[0]
    out, inst_mod = [], {}

    def walk(mod, prefix, depth):
        if depth > 64:
            raise ValueError("hierarchy too deep")
        for typ, name in mods[mod]:
            full = prefix + name
            if typ in mods:
                inst_mod[full] = typ
                walk(typ, full + "/", depth + 1)
            else:
                out.append((full, typ))
    walk(top, "", 0)
    return out, inst_mod, top


def check(spec, cells, inst_mod, hierarchical):
    seq = {}
    for full, typ in cells:
        if SEQ_RE.match(typ) and "/" in full:
            seq.setdefault(full.rsplit("/", 1)[0], []).append(full)
    rules, ok = [], True
    for r in spec["rules"]:
        rx = re.compile(r["inst_re"])
        found = {}
        for inst, ffs in seq.items():
            m = rx.search(inst)
            if m:
                key = ",".join(m.groups()) if m.groups() else inst
                found.setdefault(key, []).append((inst, len(ffs)))
        want = [str(g) for g in r["groups"]]
        missing = sorted(set(want) - set(found))
        extra = sorted(set(found) - set(want))
        bad = {k: v for k, v in found.items() if k in want and (len(v) != 1 or v[0][1] != r["ff_per_inst"])}
        mod_bad = []
        if hierarchical and r.get("module"):
            for k, v in found.items():
                for inst, _ in v:
                    if inst_mod.get(inst) != r["module"]:
                        mod_bad.append(f"{inst}: {inst_mod.get(inst)}")
        rok = not (missing or extra or bad or mod_bad)
        ok &= rok
        rules.append(dict(name=r["name"], verdict="PASS" if rok else "FAIL", expected_insts=len(want),
                          found_insts=len(found), ff_per_inst=r["ff_per_inst"],
                          ff_total=sum(n for v in found.values() for _, n in v),
                          missing=missing, extra=extra, bad={k: v for k, v in list(bad.items())[:16]},
                          module_mismatch=mod_bad[:16]))
    return ok, rules


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--expect", required=True, type=Path)
    ap.add_argument("--netlist", required=True, type=Path)
    ap.add_argument("--top")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    try:
        spec = json.loads(a.expect.read_text())
        if not spec.get("rules"):
            raise ValueError("spec has no rules")
        mods = parse(a.netlist.read_text())
        cells, inst_mod, top = flatten(mods, a.top)
        if not cells:
            raise ValueError("no cells parsed")
    except (OSError, ValueError, KeyError) as e:
        print(f"REPLICA_CHECK ERROR {e}")
        if a.out:
            a.out.write_text(json.dumps(dict(verdict="ERROR", reason=str(e)), indent=1) + "\n")
        return 2
    ok, rules = check(spec, cells, inst_mod, hierarchical=len(mods) > 1)
    res = dict(verdict="PASS" if ok else "FAIL", netlist=str(a.netlist), top=top, cells=len(cells),
               hierarchical=len(mods) > 1, rules=rules)
    if a.out:
        a.out.write_text(json.dumps(res, indent=1) + "\n")
    for r in rules:
        print(f"REPLICA_CHECK {r['verdict']} {r['name']}: {r['found_insts']}/{r['expected_insts']} insts, "
              f"{r['ff_total']} FF (want {r['ff_per_inst']}/inst)"
              + (f" missing {r['missing'][:8]}" if r["missing"] else "") + (f" extra {r['extra'][:8]}" if r["extra"] else "")
              + (f" bad {list(r['bad'].items())[:4]}" if r["bad"] else "")
              + (f" module {r['module_mismatch'][:4]}" if r["module_mismatch"] else ""))
    print(f"REPLICA_CHECK {res['verdict']} {a.netlist}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
