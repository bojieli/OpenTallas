#!/usr/bin/env python3
"""seal_derived.py -- kit seal: every derived record re-derived from the BOUND plan and digest-checked (STATION-MOVE-HELPER 11-24,
COORD flow review 78d6e61 fix 5).  REPORT ONLY (WARN, r703); --regen rewrites the records that can be regenerated.

Class: a kit tree is sealed with records derived from an older plan or older tools, found an hour later by the gen / bootstrap:
  c8 seal tree   physical/die_plan/s81/lat/s81_latency.json + s81_lat_pkg.sv (+ 2 more) copied forward from 11-16, 787 of 873
                 lane values behind the bound p6w_sg plan (the compiler table and die_ci read s81_latency.json);
  HEAD E11       bootstrap 2009725 stopped on schema field tap_reset_split_rounds: the tree's own tools/die_plan/schema.py
                 predates a field the bound plan carries;
  QC su_l0       4 types label every core tap budget_owner SIGNED, so gen requires clock_contract.json / signoff.json in the
                 selected lib dir; none exists -> ContractError at gen ("no SIGNED mean clock contract").
Forms (WARN SEAL-<FORM>), one LIST SEAL-DERIVED line:
  LATPKG     each latency package of the die in TREE/physical/die_plan/<die>/{.,lat,r8} (+ --lat-dir) whose plan digest != gen.plan_digest
             (bound plan).  --regen rewrites it from the bound plan (gen.write_latency, tmp + os.replace) when its dir is writable
             and it is not an R8-folded package (r8/ dir, an "r8" block, or a run_lat*.sh / *_r8_landing.json recipe beside it:
             needs gen.py latency --groups --fold-r8, listed only);
             each rewrite is re-read and must carry the plan digest.
  SCHEMA     the bound plan validated with the TREE's own tools/die_plan/schema.py (the tools a bootstrap / gen from that tree
             reads); every error is listed.  No regen: the fix is the rt tools overlay (or a newer tree), never a plan edit.
  CONTRACT   every type with hard cores whose gen takes a mean clock contract (gen_phys.core_mean_contract_options) has one in
             each selected lib dir (core_clock_contract.latency_table, the gen call); a refusal names the type, the lib dir and
             which of clock_contract.json / signoff.json is there.  No regen: the fix is the record or a parent_budget row.

    python3 -I tools/die_plan/seal_derived.py --tree TREE --plan BOUND_PLAN [--regen] [--lat-dir D ...] [--types T1,T2]
           [--root VIEW_ROOT] [--json OUT] [--no-schema] [--no-contract]
    exit 0 always (report only; 2 = bad input).  station_move.py regenerates the same packages on a station move.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # -I drops the script dir
MAX_LIST = 12
SCHEMA_PROBE = ("import json, sys\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "import schema as S\n"
                "print(json.dumps([str(e) for e in S.validate(json.load(open(sys.argv[2])))]))\n")


def _r8_folded(f):
    """an R8-folded package (or a dir whose recipe folds R8: run_lat*.sh / *_r8_landing.json beside it, the S81 lat/ form) is never
    regenerated plain: a plain gen.write_latency would drop the R8 pads"""
    if f.parent.name == "r8" or any(f.parent.glob("run_lat*.sh")) or any(f.parent.glob("*_r8_landing.json")):
        return True
    js = f if f.suffix == ".json" else next(iter(sorted(f.parent.glob("*_latency.json"))), None)
    try:
        return bool(js and "r8" in json.loads(js.read_text()))
    except (OSError, ValueError):
        return False


def latpkg(raw, tree, regen=False, lat_dirs=()):
    """-> (lines, counts)"""
    import gen
    import latpkg_check as LP
    import station_move as SM
    dig, die = gen.plan_digest(raw), LP.die_name(raw)
    dd = Path(tree) / "physical" / "die_plan" / die
    roots = [(dd, 0), (dd / "lat", 0), (dd / "r8", 0)] + [(Path(d), 0) for d in lat_dirs]
    seen, files = set(), []
    for r, dep in roots:
        for f in LP._walk(r, dep):
            if f.resolve() not in seen:
                seen.add(f.resolve())
                files.append(f)
    out, n, stale, done = [], 0, 0, 0
    redo = {}
    for f in sorted(files):
        pk = LP.read_package(f)
        if pk is None or (die and pk.get("die") and pk["die"] != die):
            continue
        n += 1
        if pk.get("digest") == dig:
            continue
        stale += 1
        miss, extra, diff = LP.stale_values(pk, raw)
        why = f"{len(miss) + len(extra) + len(diff)} stale value(s) (missing {len(miss)}, extra {len(extra)}, cycles differ {len(diff)})"
        if regen and not _r8_folded(f) and os.access(f.parent, os.W_OK):
            redo.setdefault(f.parent, []).append((f, pk.get("digest"), why))
            continue
        note = ("R8-folded: regenerate with gen.py latency --groups --fold-r8 [--rebase-bind] (S81: compose/postbind_lat.sh)" if _r8_folded(f)
                else "read-only dir" if regen else "run with --regen")
        out.append(f"WARN SEAL-LATPKG {f}: plan digest {pk.get('digest')} != bound plan {dig}; {why}; {note}")
    for d, rows in sorted(redo.items()):
        try:
            wrote = SM.regen_latency(raw, [d])
        except SM.MoveError as e:
            out += [f"WARN SEAL-LATPKG {f}: plan digest {old} != bound plan {dig}; {why}; regeneration refused: {e}" for f, old, why in rows]
            continue
        for f, old, why in rows:
            new = next((Path(w["path"]) for w in wrote if Path(w["path"]).suffix == f.suffix), None)
            got = (LP.read_package(new) or {}).get("digest") if new else None
            if got == dig:
                done += 1
                out.append(f"REGEN SEAL-LATPKG {new}: {old} -> {dig} ({why} before)")
            else:
                out.append(f"WARN SEAL-LATPKG {f}: regenerated but reads digest {got} != {dig}")
    return out, dict(latpkg=n, latpkg_stale=stale, latpkg_regen=done)


def schema_errors(plan, tree, timeout=600):
    """the bound plan validated by TREE/tools/die_plan/schema.py -> (lines, n errors); no tree schema: note only"""
    td = Path(tree) / "tools" / "die_plan"
    if not (td / "schema.py").is_file():
        return [f"NOTE SEAL-SCHEMA {td}/schema.py absent: tree carries no tools (the launch rt validates)"], 0
    try:
        p = subprocess.run([sys.executable, "-I", "-c", SCHEMA_PROBE, str(td), str(plan)], capture_output=True, text=True,
                           timeout=timeout, cwd=str(td))
        errs = json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 and p.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError) as e:
        return [f"WARN SEAL-SCHEMA not checked: {type(e).__name__}: {str(e)[:200]}"], 0
    if errs is None:
        return [f"WARN SEAL-SCHEMA tree schema crashed on the bound plan: {(p.stderr or '')[-300:].strip()}"], 1
    lines = [f"WARN SEAL-SCHEMA {e[:300]}  (tree tools {td} older than the plan? use the rt tools overlay)" for e in errs[:MAX_LIST]]
    if len(errs) > MAX_LIST:
        lines.append(f"WARN SEAL-SCHEMA ... {len(errs) - MAX_LIST} more")
    return lines, len(errs)


def contracts(raw, plan, types=None, root=None):
    """-> (lines, n types refused, n types checked)"""
    import schema as S
    import gen_phys as GP
    import core_clock_contract as CC
    import cores as C
    P = S.Plan(raw, plan)
    lines, bad, checked = [], 0, 0
    for tn in sorted(P.types):
        t = P.types[tn]
        if types and tn not in types or not t.get("hard_cores"):
            continue
        checked += 1
        try:
            opts = GP.core_mean_contract_options(P, tn)
            if opts.get("mean_contract"):
                CC.latency_table(P, tn, root, require_signed=opts.get("require_signed", True))
        except Exception as e:  # noqa: BLE001 - ContractError or a missing view: gen would stop the same way
            bad += 1
            dirs = []
            for c in t.get("hard_cores") or []:
                if c.get("lib"):
                    try:
                        ld = C.resolve(c["lib"], root).parent
                    except Exception:  # noqa: BLE001
                        continue
                    have = [n for n in ("clock_contract.json", "signoff.json") if (ld / n).is_file()]
                    dirs.append(f"{ld} has {have or 'neither clock_contract.json nor signoff.json'}")
            signed = [tp.get("name") for tp in (t.get("clock") or {}).get("taps") or []
                      if tp.get("kind") == "core" and str(tp.get("budget_owner", "")).startswith("SIGNED")]
            lines.append(f"WARN SEAL-CONTRACT {tn}: {type(e).__name__}: {str(e)[:240]}"
                         + (f"; SIGNED core taps {signed[:8]}" if signed else "")
                         + (f"; {'; '.join(dict.fromkeys(dirs))[:600]}" if dirs else "")
                         + "  (fix: the SIGNED record in that dir, or a parent_budget row on those taps)")
    return lines, bad, checked


def run(tree, plan, regen=False, lat_dirs=(), types=None, root=None, do_schema=True, do_contract=True):
    raw = json.loads(Path(plan).read_text())
    out, cnt = [], {}
    for name, fn in (("latpkg", lambda: latpkg(raw, tree, regen, lat_dirs)),
                     ("schema", lambda: schema_errors(plan, tree) if do_schema else ([], 0)),
                     ("contract", lambda: contracts(raw, plan, types, root or tree) if do_contract else ([], 0, 0))):
        try:
            r = fn()
        except Exception as e:  # noqa: BLE001 - a checker crash names itself, it never passes silently
            out.append(f"WARN SEAL-{name.upper()} not checked: {type(e).__name__}: {str(e)[:200]}")
            continue
        out += r[0]
        if name == "latpkg":
            cnt.update(r[1])
        elif name == "schema":
            cnt["schema_errors"] = r[1]
        else:
            cnt.update(contract_refused=r[1], contract_types=r[2])
    out.append("LIST SEAL-DERIVED " + " ".join(f"{k}={v}" for k, v in cnt.items()) + " (report only, r703)")
    return out, cnt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tree", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--regen", action="store_true")
    ap.add_argument("--lat-dir", action="append", default=[])
    ap.add_argument("--types", default="")
    ap.add_argument("--root", help="view root the gen resolves core libs against (default: --tree, the gen's --rtl-root / OT_REPO_ROOT)")
    ap.add_argument("--json")
    ap.add_argument("--no-schema", action="store_true")
    ap.add_argument("--no-contract", action="store_true")
    a = ap.parse_args(argv)
    if not Path(a.plan).is_file() or not Path(a.tree).is_dir():
        print("seal_derived: --plan must be a file and --tree a dir", file=sys.stderr)
        return 2
    lines, cnt = run(a.tree, a.plan, a.regen, a.lat_dir, {x for x in a.types.split(",") if x} or None, a.root,
                     not a.no_schema, not a.no_contract)
    print("\n".join(lines))
    if a.json:
        Path(a.json).write_text(json.dumps(dict(counts=cnt, lines=lines), indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
