#!/usr/bin/env python3
"""ANCHORDRY (RESET-ANCHOR-TAPGUARD-1123; from FAM-S81-SLICE-R6 J9 rows/anchor_dry.py): will the bind keep the release depth of
every reset relay a plan's clock.reset_tree_anchor names?

S81 J9 slice C (c1x_C t1/t10/t7, iq_C t1, lepe_nh_mus_C t1): `reset_anchor record --source tree` after a tap-changing plan row
anchored the plan's relay names on the renumbered tree, i.e. at other relays and other depths (lepe t1 local resets: bound J8
depth 8 -> anchored depth 2/4/5), and the strict bind failed EMIT 'release edge would move'.  Two parts:

  static (seconds, plan_gate_pre ANCHORDRY): per anchored type and per START / local-reset reference path, the anchored depth
    of the name at that path against the depth the BASE plan (remap base: the bind of record / --baseline-plan) anchored at the
    same path -- base anchor first, else the base's published collector_tree.  A differing depth is FAIL ANCHORDRY: the bind's
    resolve() keeps (or re-picks at) the anchored depth, so that reset's release edge moves (the bind refuses it, or worse, it
    binds a different release cycle).  Fix: restore the base raw names + anchors for those types (the old anchor is re-picked by
    depth + site at bind), or re-record with `reset_anchor.py record --repick` from the base-anchored plan.  No base, or no
    depth for that path in the base: the plan's own published collector_tree (the solve-time tree) is compared instead, and a
    difference is only WARN ANCHORDRY-ADVISORY (the snapshot may itself be pre- or post-retap).
  dry (solves reset trees; the CLI always, plan_gate_pre only with $OT_ANCHORDRY_SOLVE=1): the bind's own reset_anchor.resolve()
    on a copy of each anchored type against the tree the plan builds (reset_tree.for_type).  Kept / re-picked names are listed;
    an AnchorError (the bind refuses the type: no same-depth relay within tol) is WARN ANCHORDRY-ADVISORY here (LANDREMAP-BIND /
    the bind name it as the failure; it is not a depth move).

usage: anchor_dry.py TREE PLAN [--types T1,T2] [--base BASE] [--die-plan DIE_PLAN_JSON] [--json OUT]
  exit 1 = at least one FAIL (a depth move vs BASE) or dry-run refusal; 0 otherwise.
"""
import copy
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_anchor as RA  # noqa: E402


def _depths_of(t):
    """{name: depth} that type dict t records for its relays: its reset_tree_anchor, else its published collector_tree"""
    ck = (t or {}).get("clock") or {}
    anc = (ck.get(RA.KEY) or {}).get("relays") or {}
    if anc:
        return {n: int(a["depth"]) for n, a in anc.items() if isinstance(a, dict) and "depth" in a}, "anchor"
    snap = RA.snapshot(t or {})
    if snap:
        return {r["q"]: int(r["depth"]) for r in snap["relays"]}, "collector_tree"
    return {}, None


def static_findings(raw, braw=None, types=None, max_list=4):
    """FAIL ANCHORDRY / WARN ANCHORDRY-ADVISORY lines (see the module doc, static part).  raw / braw: plan / base plan dicts."""
    out = []
    bpt = (braw or {}).get("partition_types") or {}
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if types and tn not in types:
            continue
        anc = ((t.get("clock") or {}).get(RA.KEY) or {}).get("relays") or {}
        if not anc:
            continue
        paths = RA.ref_paths(t)
        bt = bpt.get(tn)
        bpaths = RA.ref_paths(bt) if bt else {}
        bdep, bsrc = _depths_of(bt) if bt else ({}, None)
        sdep = {r["q"]: int(r["depth"]) for r in (RA.snapshot(t) or {}).get("relays") or []}
        fail, adv = [], []
        for p, n in sorted(paths.items()):
            if n not in anc:
                continue                                  # resolve() names it ('lacks referenced relay')
            d = int(anc[n]["depth"])
            bn = bpaths.get(p)
            if bn is not None and bn in bdep:
                if bdep[bn] != d:
                    fail.append(f"{p} = {n} anchored depth {d}, base {bn} depth {bdep[bn]} ({bsrc})")
            elif n in sdep and sdep[n] != d:
                adv.append(f"{p} = {n} anchored depth {d}, published collector_tree depth {sdep[n]}")
        if fail:
            out.append(f"FAIL ANCHORDRY {tn}: {len(fail)} anchored reset relay(s) at another depth than the base anchors at the "
                       f"same plan path -- the bind keeps the anchored depth, so the release edge would move: "
                       + "; ".join(fail[:max_list]) + ("; ..." if len(fail) > max_list else "")
                       + "; fix: restore the base raw names + anchors of this type (the bind re-picks them by depth + site), "
                         "or re-record from them with reset_anchor.py record --repick")
        if adv:
            out.append(f"WARN ANCHORDRY-ADVISORY {tn}: {len(adv)} anchored reset relay(s) differ in depth from the plan's own "
                       f"published collector_tree (no base depth at that path): " + "; ".join(adv[:max_list]))
    return out


def dry_rows(tree, raw, plan_path, types=None, tree_fn=None, die_plan=None, ported_fn=RA.ported):
    """the bind's reset_anchor.resolve() on a copy of each anchored type -> [row]: {type, status OK|FAIL|UNCHECKED, receipt |
    error, detail}.  tree_fn(tn) -> reset tree; default reset_tree.for_type on schema.Plan(raw) with --tree as cwd."""
    if tree_fn is None:
        import schema
        import reset_tree as RT
        P = schema.Plan(json.loads(json.dumps(raw)), Path(die_plan) if die_plan else Path(plan_path).parent / "die_plan.json")
        tree_fn = lambda tn: RT.for_type(P, tn)  # noqa: E731
    rows = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if (types and tn not in types) or not (t.get("clock") or {}).get(RA.KEY):
            continue
        row = dict(type=tn)
        try:
            tr = tree_fn(tn)
        except Exception as e:  # noqa: BLE001 - the bind reports the tree error itself
            rows.append(dict(row, status="UNCHECKED", error=f"{type(e).__name__}: {str(e)[:300]}"))
            continue
        row["relays"] = len(tr["relays"])
        try:
            rc = RA.resolve(tn, copy.deepcopy(t), tr, tree, ported_fn)
            row.update(status="OK", receipt=rc)
        except (RA.AnchorError, OSError) as e:
            try:
                port = ported_fn(tr)
            except Exception:  # noqa: BLE001 - detail only
                port = set()
            det = []
            for n, a in sorted(((t["clock"].get(RA.KEY) or {}).get("relays") or {}).items()):
                same = [r for r in tr["relays"] if int(r["depth"]) == int(a["depth"]) and r["q"] not in port and RA.NAME.match(r["q"])]
                d = min((RA._d(r["xy"], a["xy"]), r["q"]) for r in same) if same else (None, None)
                det.append(dict(name=n, depth=a["depth"], xy=a["xy"], n_same_depth=len(same), nearest=d[1],
                                nearest_um=None if d[0] is None else round(d[0], 1)))
            row.update(status="FAIL", error=str(e)[:400], detail=det)
        rows.append(row)
    return rows


def dry_findings(rows):
    """plan_gate_pre lines of dry_rows: a refusal is advisory here (not a depth move; LANDREMAP-BIND / the bind fail it)"""
    out = []
    for r in rows:
        if r["status"] == "FAIL":
            out.append(f"WARN ANCHORDRY-ADVISORY {r['type']}: the bind's anchor re-pick refuses this type: {r['error'][:300]}")
        elif r["status"] == "UNCHECKED":
            out.append(f"WARN ANCHORDRY-ADVISORY {r['type']}: reset tree not built ({r['error'][:200]}); dry re-pick skipped")
        elif r["receipt"] and r["receipt"]["remaps"]:
            rm = r["receipt"]["remaps"]
            out.append(f"WARN ANCHORDRY-ADVISORY {r['type']}: the bind re-picks {len(rm)} anchored name(s) at the same depth: "
                       + ", ".join(f"{m['name']}->{m['to']} d{m['depth']} {m['moved_um']}um" for m in rm[:4]))
    return out


def main(argv):
    if len(argv) < 3 or argv[1].startswith("-"):
        print(__doc__.strip().splitlines()[-2], file=sys.stderr)
        return 2
    tree, plan = argv[1], argv[2]

    def opt(k):
        return argv[argv.index(k) + 1] if k in argv else None
    types = set(filter(None, (opt("--types") or "").split(","))) or None
    raw = json.loads(Path(plan).read_text())
    braw = json.loads(Path(opt("--base")).read_text()) if opt("--base") else None
    plan_abs = str(Path(plan).absolute())
    lines = static_findings(raw, braw, types)
    here = os.getcwd()
    try:
        os.chdir(tree)
        rows = dry_rows(str(Path(tree).resolve()), raw, plan_abs, types, die_plan=opt("--die-plan"))
    finally:
        os.chdir(here)
    for r in rows:
        if r["status"] == "OK":
            rc = r["receipt"]
            print(f"OK   {r['type']}: anchored {rc['anchored']} kept {rc['kept']} remaps "
                  + ", ".join(f"{m['name']}->{m['to']} d{m['depth']} {m['moved_um']}um" for m in rc["remaps"]), flush=True)
        else:
            print(f"{r['status']:<4} {r['type']}: {r['error'][:300]}", flush=True)
            for x in r.get("detail") or []:
                print(f"     {x['name']} d{x['depth']} @{x['xy']}: {x['n_same_depth']} same-depth, nearest {x['nearest']} "
                      f"{x['nearest_um']} um", flush=True)
    for x in lines:
        print(x)
    nfail = sum(1 for r in rows if r["status"] == "FAIL") + sum(1 for x in lines if x.startswith("FAIL "))
    print(f"ANCHOR_DRY types={len(rows)} fail={nfail}")
    if opt("--json"):
        Path(opt("--json")).write_text(json.dumps(dict(rows=rows, findings=lines), indent=1) + "\n")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
