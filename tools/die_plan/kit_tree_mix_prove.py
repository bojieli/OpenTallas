#!/usr/bin/env python3
"""HBM-HUB-RTL-1 11-11: prove a kit tree-mix edge neutral -> a registry entry kit_tree_mix_lint.py accepts.

    kit_tree_mix_prove.py --kit KIT_RTL.f --module M --param NAME=v1,v2,... [--param ...] --registry REG.json [--yosys Y]

The kit picks M from one tree (pick) while a parent comes from the other tree, whose own copy of M is the twin.  For
every combination of the parameter values given (the parameters the parents set; every other parameter takes its
default), yosys proves the pick (with the kit's own sources) sequentially equivalent to the twin (twin file in place of
the pick's file, plus the twin tree's sources for modules only the twin needs): flatten, opt, equiv_make,
equiv_simple -seq, equiv_induct -seq, equiv_status -assert.  All combinations PROVEN -> one registry entry keyed by the
sha256 of every source file either side read for M's closure; any byte change of those files voids it.
"""
import argparse, hashlib, itertools, json, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_tree_mix_lint as L


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def closure(top, defs):
    """files defining top and every module it reaches (by the defining file map)"""
    seen, files, todo = set(), [], [top]
    while todo:
        m = todo.pop()
        if m in seen or m not in defs:
            continue
        seen.add(m)
        f = defs[m]
        if f not in files:
            files.append(f)
        todo += [c for c, _, _ in L.instances(L.modules(f)[m][1], set(defs)) if c]
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", required=True)
    ap.add_argument("--module", required=True)
    ap.add_argument("--param", action="append", default=[])
    ap.add_argument("--registry", required=True)
    ap.add_argument("--yosys", default=str(Path.home() / ".local/opentallas-tools/yosys-0.68/bin/yosys"))
    ap.add_argument("--work", default=None)
    a = ap.parse_args(argv)
    M = a.module
    kit_files = L.read_list(a.kit)
    kdefs = {}
    for f in kit_files:
        for m in L.modules(f):
            kdefs.setdefault(m, f)
    pick = kdefs[M]
    twin = L.counterpart(pick)
    if twin is None or not twin.is_file() or M not in L.modules(twin):
        sys.exit(f"{M}: pick {pick} has no twin copy in the other tree")
    pick_files = closure(M, kdefs)
    # twin side: the twin file replaces the pick file; modules the twin needs that the kit lacks come from the twin tree
    tdefs = dict(kdefs)
    for m in L.modules(twin):
        tdefs[m] = str(twin)
    # the twin's children are the kit's picks (one definition per module in a kit); a module the kit lacks, or holds
    # only as a kit-local alias (tree "other"), comes from the twin's own directory (its tree)
    for f in sorted(Path(twin).parent.glob("*.sv")):
        for m in L.modules(f):
            if m not in L.modules(twin) and (m not in kdefs or L.tree(kdefs[m])[0] == "other"):
                tdefs[m] = str(f)
    twin_files = closure(M, tdefs)
    grid = []
    names = []
    for p in a.param:
        n, vs = p.split("=", 1)
        names.append(n)
        grid.append(vs.split(","))
    work = Path(a.work or tempfile.mkdtemp(prefix="ktmprove_"))
    work.mkdir(parents=True, exist_ok=True)
    results = []
    for combo in itertools.product(*grid) if grid else [()]:
        ch = " ".join(f"-chparam {n} {v}" for n, v in zip(names, combo))
        tag = "_".join(f"{n}{v}" for n, v in zip(names, combo)) or "default"
        side = []
        for nm, files in (("gold", pick_files), ("gate", twin_files)):
            side += ["design -reset"] + [f"read_verilog -defer -sv {f}" for f in files] + [
                f"hierarchy -check -top {M} {ch}", "proc", "flatten", "async2sync", "opt -fast", "opt_dff", "opt_clean",
                f"rename {M} {nm}", f"design -stash {nm}"]
        ys = side + ["design -reset", "design -copy-from gold -as gold gold", "design -copy-from gate -as gate gate",
                     "equiv_make gold gate eq", "hierarchy -top eq", "equiv_struct", "equiv_induct -seq 4", "equiv_simple -seq 8", "equiv_induct -seq 8",
                     "equiv_status -assert"]
        (work / f"{tag}.ys").write_text("\n".join(ys) + "\n")
        r = subprocess.run([a.yosys, "-q", "-l", str(work / f"{tag}.log"), "-s", str(work / f"{tag}.ys")],
                           capture_output=True, text=True)
        ok = r.returncode == 0
        results.append(dict(params=dict(zip(names, combo)), proven=ok, log=str(work / f"{tag}.log")))
        print(f"{'PROVEN' if ok else 'NOT_PROVEN'} {M} {tag}" + ("" if ok else f": {(r.stderr or r.stdout).strip()[-300:]}"))
    allok = all(x["proven"] for x in results)
    entry = dict(module=M, pick_tree=L.tree(pick)[0], twin_tree=L.tree(twin)[0],
                 pick_files={L.tree(f)[2] and f"{L.tree(f)[0]}:{L.tree(f)[2]}" or f: sha(f) for f in pick_files},
                 twin_files={L.tree(f)[2] and f"{L.tree(f)[0]}:{L.tree(f)[2]}" or f: sha(f) for f in twin_files},
                 domain={n: g for n, g in zip(names, grid)}, results=[dict(params=x["params"], proven=x["proven"])
                                                                     for x in results],
                 method="yosys flatten+async2sync+opt_dff, equiv_make/equiv_struct/equiv_induct -seq 4/equiv_simple -seq 8/equiv_induct -seq 8/equiv_status -assert",
                 kit=str(a.kit))
    if allok:
        reg = Path(a.registry)
        data = json.loads(reg.read_text()) if reg.is_file() else dict(schema="opentallas.kit_tree_mix_proofs.v1", proofs=[])
        data["proofs"] = [p for p in data["proofs"] if not (p["module"] == M and p["pick_files"] == entry["pick_files"]
                                                            and p["twin_files"] == entry["twin_files"])] + [entry]
        reg.write_text(json.dumps(data, indent=1) + "\n")
    print(f"KIT_TREE_MIX_PROVE {'PASS' if allok else 'FAIL'} {M} combos={len(results)}")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
