#!/usr/bin/env python3
"""TOK-DS 10-26: Verilator lint-only of a bound_carve.py carve against the SAME sources the strict bind used.

    bound_carve_lint.py --cohort ROOT --manifest physical/die_plan/<die>/bind/<asbuilt>.json --bound ROOT/out
                        --carve DIR/<name>.json [--run]

File list = the carve + the bound partition / native-glue RTL the bind emitted (bind_report.json "files", minus the
bound top) + ot_reset_sync + the as-built RTL closure (tools/die_plan/bind_elab.py module_index/closure, manifest
prefer + bind extra_lib + OUT/bind.f) of every leaf master the KEPT partitions instantiate.  Defines = the manifest's
"defines" (+define+ each).  Writes DIR/<name>_lint.f (Verilator -f file); --run runs it and writes <name>_lint.{log,json}.
Nothing is substituted: a leaf with no source is reported as missing, not stubbed; a child module with several
definitions and no manifest/bind.f preference is listed under "ambiguous" (bind_elab.pick: first non-_bb file).
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys
from pathlib import Path

SKIP = {"ot_dp_st", "ot_dp_dly", "ot_dp_or", "ot_dp_and", "ot_dp_rsync", "ot_reset_sync", "ot_dp_rrelay", "ot_dp_rgate",
        "ot_dp_rsync_s2", "ot_dp_rsync_s3", "ot_dp_lockq"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", required=True, type=Path)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--bound", required=True, type=Path)
    ap.add_argument("--carve", required=True, type=Path)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--src-tree", type=Path, default=None,
                    help="the full source checkout of the bound revision (the staged cohort carries only what the bind "
                         "reads: leaf masters, not their children); --roots are indexed under it, and a file the cohort "
                         "also stages at the same relative path is taken from the cohort")
    ap.add_argument("--roots", default="rtl,physical/asap7_memory_macros_v2,physical/asap7_memory_macros",
                    help="RTL roots indexed for the leaves' own children (the bind black-boxes leaves, so the manifest "
                         "files list stops at the leaf masters); manifest prefer + bind.f still win every ambiguity")
    a = ap.parse_args()
    root = a.cohort.resolve()
    sys.path.insert(0, str(root / "tools" / "die_plan"))
    import bind_elab as E                                   # the cohort's own copy (REPO = cohort root)
    man_p = root / a.manifest
    ab0 = json.loads(man_p.read_text())
    base = str((man_p.parent / ab0.get("base", ".")).resolve())
    rep = json.loads((a.bound / "bind_report.json").read_text())
    cv = json.loads(a.carve.read_text())
    gen = [str((root / f).resolve()) if not Path(f).is_absolute() else f for f in rep["files"]]
    gen = [f for f in gen if not f.endswith("_bound_top.sv")]
    kept = set(cv["seeds"].values())
    leafm = set()
    for f in gen:
        t = Path(f).read_text(errors="replace")
        mods = set(re.findall(r"^module\s+(\w+)", t, re.M))
        if mods & kept:
            leafm |= set(re.findall(r"^\s+(\w+)\s+(?:#\(.*?\)\s+)?u_\w+\s*\(", t, re.M)) - mods - SKIP
    # emitted RTL: only the files of the kept partitions and of the bind cells / native glue they instantiate
    # (a file the carve does not reach is not read: e.g. one Verilator cannot preprocess cannot block an unrelated carve)
    gdef = {}
    for f in gen:
        for m in re.findall(r"^module\s+(\w+)", Path(f).read_text(errors="replace"), re.M):
            gdef.setdefault(m, f)
    need, todo, gsel = set(), sorted(kept), []
    while todo:
        m = todo.pop()
        if m in need or m not in gdef:
            continue
        need.add(m)
        f = gdef[m]
        if f not in gsel:
            gsel.append(f)
            t = Path(f).read_text(errors="replace")
            todo += [x for x in set(re.findall(r"^\s+(\w+)\s+(?:#\(.*?\)\s+)?\w+\s*\(", t, re.M)) if x in gdef]
    leafm -= set(gdef)                                       # native glue / bind cells come from the emitted RTL
    gen = gsel
    roots = list(ab0.get("rtl_roots") or []) + [r for r in a.roots.split(",") if r]
    st = (a.src_tree or root).resolve()
    idx = E.module_index([str(st / r) for r in roots], ab0.get("files", []), base)
    for m, fl in idx.items():                                # same relative path staged in the cohort -> cohort copy
        nl = []
        for f in fl:
            rp = Path(f).resolve()
            if st != root and rp.is_relative_to(st) and (root / rp.relative_to(st)).is_file():
                f = str(root / rp.relative_to(st))
            if f not in nl:
                nl.append(f)
        idx[m] = nl
    prefer = [str(Path(base) / f) if not Path(f).is_absolute() else f for f in ab0.get("prefer", [])]
    prefer += rep.get("extra_lib", []) or []
    bf = a.bound / "bind.f"
    if bf.is_file():
        prefer += [str(Path(x) if Path(x).is_absolute() else Path(base) / x) for x in bf.read_text().split()]
    cl, missing = E.closure(sorted(leafm), idx, prefer)
    pres = {str(Path(p).resolve()) for p in prefer}
    clm = {m: f for f in cl for m in re.findall(r"^\s*module\s+(\w+)", Path(f).read_text(errors="replace"), re.M)}
    ambiguous = sorted(m for m in clm if len(idx.get(m, [])) > 1 and not any(str(Path(c).resolve()) in pres
                                                                             for c in idx[m]))
    rs = str(root / "rtl/lib/ot_reset_sync.sv")
    files = [str(a.carve.with_suffix(".v").resolve())] + gen + [rs] + [f for f in cl if f not in gen and f != rs]
    defs = ab0.get("defines", [])
    incs = sorted({f"-I{Path(f).parent}" for f in files})
    name = cv["name"]
    out = a.carve.parent
    args = ["--lint-only", "-Wno-fatal", "-Wno-DECLFILENAME", "-Wno-UNUSEDSIGNAL", "-Wno-PINCONNECTEMPTY",
            "--top-module", name] + [f"+define+{d}" for d in defs] + incs + files
    (out / f"{name}_lint.f").write_text("\n".join(args) + "\n")
    res = dict(schema="opentallas.tok_ds.bound_carve_lint.v1", carve=str(a.carve), manifest=a.manifest, defines=defs,
               kept_types=len(kept), leaf_masters=len(leafm), closure_files=len(cl), files=len(files),
               missing_leaves=missing, src_tree=str(st), roots=roots, ambiguous=ambiguous)
    print(json.dumps(res))
    if missing:
        return 2
    if a.run:
        v = os.environ.get("VERILATOR", str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
        r = subprocess.run([v, "-f", str(out / f"{name}_lint.f")], capture_output=True, text=True, cwd=out)
        (out / f"{name}_lint.log").write_text(r.stderr)
        errs = [ln for ln in r.stderr.splitlines() if ln.startswith("%Error") and not ln.startswith("%Error: Exiting")]
        res.update(rc=r.returncode, errors=len(errs), first_errors=errs[:30],
                   warnings=sum(ln.startswith("%Warning") for ln in r.stderr.splitlines()))
        (out / f"{name}_lint.json").write_text(json.dumps(res, indent=1) + "\n")
        print(json.dumps({k: res[k] for k in ("rc", "errors", "warnings")}))
        return 1 if errs or r.returncode else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
