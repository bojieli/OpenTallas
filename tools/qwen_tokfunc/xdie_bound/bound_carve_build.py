#!/usr/bin/env python3
"""TOK-DS 10-26: per-type Verilator lint + hierarchical build file lists for a bound_carve.py carve.

    bound_carve_build.py --bound ROOT/out --asbuilt ROOT/physical/die_plan/<die>/bind/<asbuilt>.json --rev SHA
                         --carve DIR/<name>.json --work WORK [--tb TB.sv --tb-top NAME] [--hier-leaf M ...]

The full carve does not lint in 160 GB (two svc types x 64 attention hcores, all elaborated at once), so every kept
partition type is its own unit:
  WORK/types/<T>.f   lint-only of partition type T alone: T's emitted RTL + the as-built closure of every leaf below it
                     + the manifest defines.  Nothing stubbed: a module with no source is reported as missing.
  WORK/hier.vlt      `hier_block` for every kept partition type and every --hier-leaf master the carve reaches
                     (default ot_s81c_attn_hcore: one compile serves its 64 instances per svc type; it takes gid as a port).
                     Verilator --hierarchical makes one library per (type, strap-parameter set) the carve instantiates.
  WORK/carve.f       the carve (or --tb bench over it) with hier.vlt, for `verilator --cc|--binary --hierarchical -f`.
Sources are resolved with the BINDER's own resolver (tools/die_plan/bind_smoke.py Sources = bind_elab pick/closure:
<bound>/rtl first, then the as-built prefer / portbind_prefer files, then the macro models v2, v1, then the rtl_roots
index of --rev, as a git archive).  That order is what fixes the bound_carve_lint.py list: there the rtl/lib p192 kit
wrapper of ot_sram_1r1w_512x128_m4_r2c2 won over the macro model and pulled in ot_sram_1r1w_512x128_m4_r2c2_p192_mir
(MODMISSING), and three SRAM masters were ambiguous.  Every file is staged under WORK/src/ (repo-relative paths inside,
bound RTL under src/bound/) so the job reads only WORK, at --rev.  WORK/build_sources.json records rev, files, sha256s.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LINT_W = ["-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN"]
HIER_LEAF = ["ot_s81c_attn_hcore"]


def type_lists(kept, closure):
    """{type: [files]} per kept type; closure(mods) -> (files, ambiguous{}, missing[]).  Pure (tested)."""
    out, amb, miss = {}, {}, {}
    for t in sorted(kept):
        f, a, m = closure([t])
        out[t] = list(f)
        amb.update(a)
        if m:
            miss[t] = list(m)
    return out, amb, miss


def union_files(lists, first=()):
    """ordered union: `first` files, then each type's files in type order, no duplicates.  Pure (tested)."""
    seen, out = set(), []
    for f in list(first) + [x for t in sorted(lists) for x in lists[t]]:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def vlt_text(blocks):
    return "`verilator_config\n" + "".join(f'hier_block -module "{b}"\n' for b in sorted(set(blocks)))


def ff_text(top, defines, incdirs, files, extra=()):
    return "\n".join(list(extra) + ["--top-module", top] + [f"+define+{d}" for d in defines] +
                     [f"+incdir+{d}" for d in incdirs] + list(files)) + "\n"


def modules_in(f):
    return set(re.findall(r"^\s*module\s+(\w+)", Path(f).read_text(errors="replace"), re.M))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bound", required=True, type=Path)
    ap.add_argument("--asbuilt", required=True, type=Path)
    ap.add_argument("--rev", required=True)
    ap.add_argument("--repo", type=Path, default=Path.home() / "OpenTallas")
    ap.add_argument("--carve", required=True, type=Path)
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--tb", type=Path, default=None, help="bench over the carve (top for carve.f)")
    ap.add_argument("--tb-top", default=None)
    ap.add_argument("--hier-leaf", action="append", default=None)
    a = ap.parse_args(argv)
    os.environ.setdefault("CAL_SMOKE_CACHE_ROOT", str(a.work.resolve() / "srccache"))
    sys.path.insert(0, str(REPO / "tools/die_plan"))
    import bind_smoke as B
    cv = json.loads(a.carve.read_text())
    S = B.Sources(a.bound.resolve(), a.asbuilt.resolve(), a.rev, a.repo)
    # The recipe's rtl_roots is [] (the bind black-boxes leaves, so Sources indexes only the recipe files): the leaves'
    # own children would be invisible (instantiated() drops names with no index entry, so they are not even reported
    # missing).  Index the full rtl tree + the macro dirs of --rev, keeping the binder's preference order.
    ab = json.loads(a.asbuilt.read_text())
    pref = list(ab.get("prefer", [])) + list(ab.get("portbind_prefer", []))
    os.environ["CAL_SMOKE_CACHE_ROOT"] = str(a.work.resolve() / "srcfull")
    S.base = B.src_tree(a.rev, a.repo, ["rtl"] + B.MACRO_DIRS + list(ab.get("files", [])) + pref)
    # bound RTL = the bind report's own file list (partitions + bind_cells.sv + native_glue/), as the bind verify read it
    rep0 = json.loads((S.bound / "bind_report.json").read_text())
    brtl = [str(Path(f) if Path(f).is_absolute() else (S.bound.parent / f).resolve()) for f in rep0["files"]]
    brtl = [f for f in brtl if not f.endswith("_bound_top.sv")]
    S.idx = S.E.module_index(list(ab.get("rtl_roots") or []) + ["rtl"] + B.MACRO_DIRS,
                             list(ab.get("files", [])) + pref + brtl, S.base)
    S.prefer = brtl + [str(S.base / f) for f in pref] + [str(S.base / d) for d in B.MACRO_DIRS]
    pick0, memo, bb_model = S.E.pick, {}, {}      # pick() resolves every candidate x prefer path: memoise per module

    def pick(idx, name, prefer):                  # (idx and prefer are fixed for S, so the answer is too)
        if name not in memo:
            f, amb = pick0(idx, name, prefer)
            if f and f.endswith("_bb.v"):         # a recipe may prefer a macro's synthesis black box; simulation
                m = f[:-len("_bb.v")] + ".v"      # needs the same macro's behavioural model (same dir, same module)
                if Path(m).is_file() and name in modules_in(m):
                    bb_model[name] = [f, m]
                    f = m
            memo[name] = (f, amb)
        return memo[name]
    S.E.pick = pick
    pkgs = {}                                     # package -> file over the same tree (bind_elab indexes modules only)
    for f in sorted(set(x for v in S.idx.values() for x in v)) + [str(p) for p in (S.base / "rtl").rglob("*pkg*.sv")]:
        for m in re.findall(r"^\s*package\s+(\w+)\s*;", Path(f).read_text(errors="replace"), re.M):
            pkgs.setdefault(m, f)

    def closure(mods):
        """S.closure + what it cannot see: modules named only inside `define bodies outside any module (e.g.
        ot_s81sl_xs4's `OT_S81SL_XS4_ROM -> ot_rom_4096x72_m8), and imported / scoped packages (listed first)."""
        files, amb, missing = S.closure(mods)
        files, done = list(files), set()
        while True:
            new = set()
            for f in files:
                if f in done:
                    continue
                done.add(f)
                txt = S.E._strip(Path(f).read_text(errors="replace"))
                for d in re.findall(r"^\s*`define\b((?:[^\n]*\\\n)*[^\n]*)", txt, re.M):
                    new |= {w for w in re.findall(r"\b([A-Za-z_]\w*)\b", d) if w in S.idx}
            f2, a2, m2 = S.closure(sorted(new)) if new else ([], {}, [])
            add = [f for f in f2 if f not in files]
            amb.update(a2)
            missing = sorted(set(missing) | set(m2))
            if not add:
                break
            files += add
        pk, todo = [], list(files)
        while todo:
            f = todo.pop()
            for p in re.findall(r"\b([A-Za-z_]\w*)\s*::", S.E._strip(Path(f).read_text(errors="replace"))):
                if p in pkgs and pkgs[p] not in pk and pkgs[p] not in files:
                    pk.append(pkgs[p])
                    todo.append(pkgs[p])
        return list(reversed(pk)) + files, amb, missing
    kept = sorted(set(cv["seeds"].values()))
    lists, amb, miss = type_lists(kept, closure)
    allf = union_files(lists)
    incs, incdirs = S.includes(allf)
    W = a.work.resolve()
    if (W / "src").exists():
        shutil.rmtree(W / "src")

    def rel(f):
        f = Path(f)
        if f.is_relative_to(S.bound):
            return Path("src/bound") / f.relative_to(S.bound)
        return Path("src") / f.relative_to(S.base)
    for f in allf + list(incs):
        d = W / rel(f)
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, d)
    il = sorted({str(rel(Path(d) / "x").parent) for d in incdirs})
    (W / "types").mkdir(exist_ok=True)
    for t, fl in lists.items():
        (W / "types" / f"{t}.f").write_text(ff_text(t, S.defines, il, [str(rel(f)) for f in fl], ["--lint-only"] + LINT_W))
    cvv = W / "carve" / a.carve.with_suffix(".v").name
    cvv.parent.mkdir(exist_ok=True)
    shutil.copyfile(a.carve.with_suffix(".v"), cvv)
    top_files = [str(cvv.relative_to(W))]
    top = cv["name"]
    if a.tb:
        shutil.copyfile(a.tb, W / "carve" / a.tb.name)
        top_files.append(f"carve/{a.tb.name}")
        top = a.tb_top or a.tb.stem
    reached = set().union(*(modules_in(f) for f in allf))
    bbs = [str(rel(f)) for f in allf if f.endswith("_bb.v")]
    if bbs:                                       # a black box left in the list is a stub: report, do not build
        miss["<black-box files>"] = bbs
    leaves = [m for m in (a.hier_leaf if a.hier_leaf is not None else HIER_LEAF) if m in reached]
    blocks = kept + leaves
    (W / "hier.vlt").write_text(vlt_text(blocks))
    (W / "carve.f").write_text(ff_text(top, S.defines, il, [str(rel(f)) for f in allf] + top_files, ["hier.vlt"]))
    (W / "kept_types.txt").write_text("\n".join(kept) + "\n")
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    rep = dict(schema="opentallas.tok_ds.bound_carve_build.v1", rev=a.rev, bound=str(a.bound), asbuilt=str(a.asbuilt),
               carve=str(a.carve), carve_top_sha256=cv.get("top_sha256"), top=top, kept_types=len(kept),
               hier_blocks=sorted(blocks), files=len(allf), includes=[str(rel(i)) for i in incs], incdirs=il,
               defines=S.defines, missing=miss,
               bb_replaced_by_model={k: [str(rel(x)) for x in v] for k, v in bb_model.items()}, ambiguous={k: [str(x) for x in v] for k, v in amb.items()},
               per_type_files={t: len(v) for t, v in lists.items()},
               sources={str(rel(f)): sha(f) for f in allf})
    (W / "build_sources.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("kept_types", "files", "missing", "hier_blocks")})[:2000])
    print("ambiguous:", sorted(amb))
    return 2 if miss else 0


if __name__ == "__main__":
    sys.exit(main())
