#!/usr/bin/env python3
"""FSTART-DEPTH-CLASS (S81-OPEN-FSTART 11-23, S81-ALLFIX-INT spec 19:12): scan EVERY type of a plan for the landing_local_resets
depth mismatch the bind refuses at EMIT, and re-pick the raw relays as one ops file (old values carried).

Class: clock_landings._local_resets refuses a copy whose raw relay depth + 1 differs from the depth of the reset its consumer
had ("landing_local_resets.<name>: consumer C reset R depth D != copy depth D' (raw X): release edge would move").  On S81
this hit serdes__t13 fstart_0 (10 != 9), the 12 col_h9_r0_p5 fstart_1 (9 != 8) and more, one family at a time, each only after
a multi-hour strict bind.  This tool asks the SAME rule up front, with the bind's own code, for every type that carries
clock.landing_local_resets:

  * the reset tree the bind builds (reset_tree.for_type on the plan), the bind's anchor re-pick (reset_anchor.resolve, on a
    copy of the type), the landing emitter (clock_landings.Landings.type_rtl on a header synthesised from the type's landed
    buses + the tree RTL), and the generator's own _local_resets check, asked once PER CONSUMER (so every mismatch of a type
    is listed, not only the first one the bind would stop at);
  * a mismatch (MISMATCH) is fixed by re-picking the entry's raw onto the non-ported rst_rl relay of depth D-1 (D = the
    consumer's reset depth) nearest to the entry's xy_um, within --reach-um (default 300, the reset hop cap), whose name does
    not collide with another anchor row; the anchor row of the new name is recorded from the bound tree (depth + site), so the
    bind's resolve() keeps it; the old anchor row is removed when nothing references it any more.  0 cycles: the copy then
    releases at depth D, exactly the edge the consumer had (START release == its old reset release);
  * these are DEPTH-CHANGING re-picks (the plan's anchored depth for the raw changes);
  * SAME-DEPTH re-picks are the ones the bind would make silently anyway (reset_anchor.resolve remap of an anchored name, or the
    generator's LOCAL-RESET-RAW-1 re-derivation of a gone / far raw): listed apart, and written into the ops only with
    --pin-same-depth;
  * entries whose consumers need DIFFERENT depths (no single raw can serve them) or with no candidate in reach are UNFIXED
    (exit 1) with the nearest candidate's distance.

The die maximum release (reset_tree.wf_plan max_release) is reported before and after: this tool never edits a reset tree
input, so it must be equal.

    python3 -I fstart_depth_fix.py scan  PLAN --asbuilt AB [--tree T] [--tools D] [--types GLOB,..] [-j N] [--json R.json]
    python3 -I fstart_depth_fix.py fix   PLAN OUT_PLAN --ops OPS.json --asbuilt AB [--tree T] [--tools D] [--reach-um 300]
                                       [--pin-same-depth] [-j N] [--json R.json]     (fix re-scans OUT_PLAN: must be 0)
    python3 -I fstart_depth_fix.py apply PLAN OPS.json OUT_PLAN      (old values checked; the last step of the S81 tail)

--tree: the repository tree the bind runs in (relative plan inputs, OT_REPO_ROOT); --tools: the tools/die_plan the bind uses
(default: this tool's folder).  Exit 0 = nothing left to fix (scan) / fixed and re-scan clean (fix) / applied (apply); 1 = mismatch
or unfixed rows remain; 2 = usage or unreadable input.
"""
import argparse
import copy
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

SCHEMA = "opentallas.fstart_depth_fix.v1"
MISMATCH = re.compile(r"landing_local_resets\.(\w+): consumer (\w+) reset (\w+) depth (\d+) != copy depth (\d+) \(raw (\w+)\): "
                      r"release edge would move")
ANCHOR_KEY = "reset_tree_anchor"
NAME = re.compile(r"^rst_rl_\d+$")
SITE_EPS_UM = 1e-3
TOL_EPS_UM = 1e-6


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ---------------------------------------------------------------- pure parts (unit-tested without a plan)

def classify(probe):
    """probe = {entry name: {"consumers": {c: {"ok": bool, "old": net|None, "old_depth": int|None, "copy_depth": int|None,
    "raw": name, "rederived_from": name|None, "error": str|None}}}} -> {name: row} with row["cls"] in OK / SAME-DEPTH / MISMATCH /
    SPLIT / OTHER and row["need_depth"] (the raw depth every consumer needs, MISMATCH only)."""
    out = {}
    for name, e in probe.items():
        cs = e["consumers"]
        errs = {c: v for c, v in cs.items() if not v["ok"]}
        mism = {c: v for c, v in errs.items() if v.get("old_depth") is not None}
        other = {c: v for c, v in errs.items() if v.get("old_depth") is None}
        row = dict(e, cls="OK")
        if other:
            row.update(cls="OTHER", error=next(iter(other.values())).get("error"))
        elif mism:
            need = {(v["old_depth"] if v.get("old_depth") is not None else v["copy_depth"]) - 1 for v in cs.values()}
            if len(need) != 1:
                row.update(cls="SPLIT", need_depths=sorted(need))
            else:
                row.update(cls="MISMATCH", need_depth=need.pop())
        elif any(v.get("rederived_from") for v in cs.values()) or (e.get("plan_raw") and e["plan_raw"] != e["raw"]):
            row.update(cls="SAME-DEPTH")
        out[name] = row
    return out


def pick(xy, need_depth, relays, ported, reach_um, anchor_rows, avoid=()):
    """-> (name, relay, dist) or (None, nearest_or_None, dist_or_None).  relays = [{"q","depth","xy"}] of the bound tree; a
    candidate is a non-ported rst_rl relay of need_depth; a name already in anchor_rows with another depth / site is skipped
    (one anchor row per name)."""
    cand = []
    for r in relays:
        q = r["q"]
        if int(r["depth"]) != int(need_depth) or q in ported or not NAME.match(q) or q in avoid:
            continue
        a = anchor_rows.get(q)
        if a is not None and (int(a["depth"]) != int(r["depth"]) or man(a["xy"], r["xy"]) > SITE_EPS_UM):
            continue
        cand.append((man(r["xy"], xy), q, r))
    cand.sort(key=lambda c: (c[0], c[1]))
    if not cand:
        return None, None, None
    d, q, r = cand[0]
    if d > reach_um + TOL_EPS_UM:
        return None, r, d
    return q, r, d


def refs(ck):
    """every rst_rl_<k> string the START / local reset sections of clock dict ck reference (reset_anchor.refs form)"""
    used = set()

    def walk(o):
        it = o.items() if isinstance(o, dict) else enumerate(o) if isinstance(o, list) else ()
        for _k, v in it:
            if isinstance(v, str) and NAME.match(v):
                used.add(v)
            else:
                walk(v)
    for s in ("landing_reader_start", "landing_writer_start", "landing_local_resets"):
        walk(ck.get(s) or {})
    return used


def type_ops(tn, ck_old, ck_new):
    """fine-grained ops (old values carried) turning clock dict ck_old into ck_new: landing_local_resets[i].raw and
    reset_tree_anchor.relays.<name> only"""
    base = f"/partition_types/{tn}/clock"
    ops = []
    for i, (a, b) in enumerate(zip(ck_old.get("landing_local_resets") or [], ck_new.get("landing_local_resets") or [])):
        if a.get("raw") != b.get("raw"):
            ops.append(dict(op="replace", path=f"{base}/landing_local_resets/{i}/raw", old=a.get("raw"), value=b.get("raw"),
                            name=b.get("name")))
    ra = ((ck_old.get(ANCHOR_KEY) or {}).get("relays") or {})
    rb = ((ck_new.get(ANCHOR_KEY) or {}).get("relays") or {})
    for n in sorted(set(ra) | set(rb)):
        p = f"{base}/{ANCHOR_KEY}/relays/{n}"
        if n not in rb:
            ops.append(dict(op="remove", path=p, old=ra[n]))
        elif n not in ra:
            ops.append(dict(op="add", path=p, value=rb[n]))
        elif ra[n] != rb[n]:
            ops.append(dict(op="replace", path=p, old=ra[n], value=rb[n]))
    return ops


def repick_type(tn, t, rows, tree, ported, reach_um, pin_same=False, resolved_raws=None):
    """-> (new clock dict, [repick records], [unfixed records]) for type dict t given classify() rows.  The new raw of a MISMATCH
    entry is the nearest legal relay of need_depth (pick()); with pin_same, a SAME-DEPTH entry is pinned to the raw the bind would
    re-derive.  resolved_raws = {entry: raw name after the bind's anchor resolve} (for SAME-DEPTH pins)."""
    ck = copy.deepcopy(t.get("clock") or {})
    llr = ck.get("landing_local_resets") or []
    anc = ck.get(ANCHOR_KEY)
    rows_a = dict((anc or {}).get("relays") or {})
    by = {r["q"]: r for r in tree["relays"]}
    reps, unfixed = [], []
    for i, e in enumerate(llr):
        row = rows.get(e.get("name"))
        if row is None or row["cls"] in ("OK", "OTHER"):
            continue
        if row["cls"] == "SPLIT":
            unfixed.append(dict(type=tn, name=e["name"], cls="SPLIT", need_depths=row["need_depths"]))
            continue
        old = e["raw"]
        old_anchor = rows_a.get(old)
        if row["cls"] == "SAME-DEPTH":
            if not pin_same:
                continue
            new = next((v["raw"] for v in row["consumers"].values() if v.get("rederived_from")), None) or row.get("raw")
            if not new or new not in by:
                continue
            r, d = by[new], man(by[new]["xy"], e["xy_um"])
            cls = "SAME-DEPTH"
        else:
            new, r, d = pick(e["xy_um"], row["need_depth"], tree["relays"], ported, reach_um, rows_a)
            if new is None:
                unfixed.append(dict(type=tn, name=e["name"], cls="NO-CANDIDATE", need_depth=row["need_depth"],
                                    nearest=(r or {}).get("q"), nearest_um=None if d is None else round(d, 3), reach_um=reach_um))
                continue
            cls = "DEPTH-CHANGE"
        e["raw"] = new
        if anc is not None:
            rows_a[new] = dict(depth=int(r["depth"]), xy=[round(float(v), 3) for v in r["xy"]])
        cons = row["consumers"]
        reps.append(dict(type=tn, name=e["name"], cls=cls, old_raw=old,
                         old_anchor_depth=None if old_anchor is None else int(old_anchor["depth"]),
                         bound_raw=(resolved_raws or {}).get(e["name"], old), new_raw=new, new_depth=int(r["depth"]),
                         copy_depth=int(r["depth"]) + 1, new_xy=[round(float(v), 3) for v in r["xy"]], dist_um=round(d, 3),
                         consumers={c: dict(old_reset=v.get("old"), reset_depth=v.get("old_depth") or v.get("copy_depth"))
                                    for c, v in cons.items()},
                         start_release_ok=all((v.get("old_depth") or v.get("copy_depth")) is not None and
                                              int(r["depth"]) + 1 >= int(v.get("old_depth") or v.get("copy_depth"))
                                              for v in cons.values())))
    if anc is not None and reps:
        used = refs(ck)
        rows_a = {k: v for k, v in rows_a.items() if k in used or k not in {x["old_raw"] for x in reps}}
        ck[ANCHOR_KEY] = dict(anc, relays=dict(sorted(rows_a.items())))
    return ck, reps, unfixed


def apply_ops(raw, ops):
    """apply type_ops() ops to plan dict raw, checking every old value; -> (applied, noop, conflicts)"""
    n = noop = 0
    conf = []
    for o in ops:
        parts = o["path"].strip("/").split("/")
        cur = raw
        for p in parts[:-1]:
            cur = cur[int(p)] if isinstance(cur, list) else cur.get(p) if isinstance(cur, dict) else None
            if cur is None:
                break
        if cur is None:
            conf.append(dict(path=o["path"], why="parent missing"))
            continue
        k = parts[-1]
        if isinstance(cur, list):
            k = int(k)
            have = cur[k] if k < len(cur) else None
            present = k < len(cur)
        else:
            have, present = cur.get(k), k in cur
        if o["op"] == "remove":
            if not present:
                noop += 1
            elif have != o["old"]:
                conf.append(dict(path=o["path"], why="old-value mismatch", old=o["old"], cur=have))
            else:
                del cur[k]
                n += 1
            continue
        if present and have == o["value"]:
            noop += 1
            continue
        if o["op"] == "add" and present:
            conf.append(dict(path=o["path"], why="add over an existing value", cur=have, new=o["value"]))
            continue
        if o["op"] == "replace" and (not present or have != o["old"]):
            conf.append(dict(path=o["path"], why="old-value mismatch", old=o.get("old"), cur=have))
            continue
        cur[k] = o["value"]
        n += 1
    return n, noop, conf


# ---------------------------------------------------------------- generator probe (needs the plan and the bind's tools)

class _Ctx:
    pass


CTX = _Ctx()


def setup(plan_path, asbuilt, tree, tools):
    if tree:
        os.environ.setdefault("OT_REPO_ROOT", str(Path(tree).resolve()))
        os.environ.setdefault("OT_RT_CURRENT", str(Path(tree).resolve()))
        os.chdir(tree)
    sys.path.insert(0, str(Path(tools).resolve()))
    import schema
    import taps
    import clock_landings as CL
    import reset_tree as RT
    import reset_anchor as RA
    CTX.CL, CTX.RT, CTX.RA, CTX.taps = CL, RT, RA, taps
    CTX.plan_path = Path(plan_path).resolve()
    CTX.raw = json.loads(CTX.plan_path.read_text())
    taps.PLAN_DIR = str(CTX.plan_path.parent)
    CTX.P = schema.Plan(CTX.raw, CTX.plan_path)
    ab = json.loads(Path(asbuilt).read_text())
    if not ab.get("clock_landing_table"):
        raise SystemExit("asbuilt has no clock_landing_table: no landing emitter to ask")
    tbl = Path(ab["clock_landing_table"])
    CTX.table = json.loads((tbl if tbl.is_absolute() else Path(tree or ".") / tbl).read_text())

    class Probe(CL.Landings):
        """type_rtl with _local_resets captured (body, logic) instead of applied"""

        def _local_resets(self, tn, key, body, logic):
            self._cap = (key, body, list(logic))
            return logic
    CTX.L = Probe(CTX.raw, CTX.table, plan_path=CTX.plan_path)


def header(L, key):
    mask = L.by_type[key]
    ports = ["    input wire clk", "    input wire arst_n"]
    for b in mask["inputs"]:
        ports.append(f"    input wire [{int(L.type_row[key].get(b, {}).get('width', 1))}:0] {b}")
    for b in mask["outputs"]:
        ports.append(f"    output wire [{int(L.type_row[key].get(b, {}).get('width', 1))}:0] {b}")
    return "module ot_fstart_depth_probe (\n" + ",\n".join(ports) + "\n);\n"


def probe_type(tn):
    """-> dict(type, probe={entry: {...}}, resolved={entry: raw}, tree_relays, error) for one type, asked with the bind's code"""
    CL, RT, RA, L = CTX.CL, CTX.RT, CTX.RA, CTX.L
    t = copy.deepcopy(CTX.raw["partition_types"][tn])
    res = dict(type=tn)
    try:
        tree = RT.for_type(CTX.P, t.get("split_of", tn))
        if (t.get("clock") or {}).get(ANCHOR_KEY):
            rc = RA.resolve(tn, t, tree, CTX.taps._root())
            res["anchor_remaps"] = (rc or {}).get("remaps", [])
        key = t.get("split_of", tn)
        saved = L.types[key]
        L.types[key] = t                      # the resolved copy (the bind resolves the plan before the landings read it)
        try:
            L._cap = None
            text = header(L, key) + "\n".join(RT.rtl_lines(tree)) + "\nendmodule\n"
            try:
                L.type_rtl(tn, text, base=key)
            except CL.LandingError as exc:
                if L._cap is None:
                    raise
                res["post_error"] = str(exc)[:300]   # after _local_resets: not this class
            if L._cap is None:
                raise CL.LandingError("type_rtl did not reach landing_local_resets")
            _k, body, logic = L._cap
            pr, resolved = {}, {}
            llr = t["clock"].get("landing_local_resets") or []
            plan_llr = {e.get("name"): e.get("raw") for e in CTX.raw["partition_types"][tn]["clock"].get("landing_local_resets") or []}
            for e in llr:
                resolved[e.get("name")] = e.get("raw")
                cons = {}
                for c in e.get("consumers") or []:
                    one = dict(e, consumers=[c])
                    t["clock"]["landing_local_resets"] = [one]
                    L.__dict__.pop("local_reset_rederived", None)
                    L.reset_placements.setdefault(tn, {}).pop("local_resets", None)
                    v = dict(ok=True, raw=e.get("raw"), old=None, old_depth=None, copy_depth=None, rederived_from=None, error=None)
                    try:
                        L.__class__.__bases__[0]._local_resets(L, tn, key, body, list(logic))
                        rec = (L.reset_placements.get(tn, {}).get("local_resets") or [{}])[-1]
                        v.update(raw=rec.get("raw"), copy_depth=rec.get("depth"), rederived_from=rec.get("raw_rederived_from"),
                                 old=(rec.get("replaced") or {}).get(c))
                    except CL.LandingError as exc:
                        m = MISMATCH.search(str(exc))
                        v.update(ok=False, error=str(exc)[:300])
                        if m:
                            v.update(old=m.group(3), old_depth=int(m.group(4)), copy_depth=int(m.group(5)), raw=m.group(6))
                    cons[c] = v
                pr[e.get("name")] = dict(raw=e.get("raw"), plan_raw=plan_llr.get(e.get("name")), xy_um=e.get("xy_um"), consumers=cons)
            t["clock"]["landing_local_resets"] = llr
            res.update(probe=pr, resolved=resolved, tree=dict(relays=tree["relays"]), ported=sorted(RA.ported(tree)))
        finally:
            L.types[key] = saved
            L.reset_placements.pop(tn, None)
    except Exception as exc:                  # noqa: BLE001 -- reported per type, the scan goes on
        res["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    return res


def scan(types, jobs, release=True):
    """-> (per-type results, die max_release or None).  The die wavefront release (minutes on S81) runs in its own worker
    beside the type probes."""
    import multiprocessing as mp
    with mp.get_context("fork").Pool(max(1, jobs) + (1 if release else 0)) as pool:
        rel = pool.apply_async(max_release) if release else None
        res = pool.map(probe_type, types, chunksize=1)
        return res, (rel.get() if rel is not None else None)


def select(raw, globs):
    out = []
    for tn, t in sorted(raw["partition_types"].items()):
        if not (t.get("clock") or {}).get("landing_local_resets"):
            continue
        if globs and not any(fnmatch.fnmatch(tn, g) for g in globs):
            continue
        out.append(tn)
    return out


def summarize(results):
    rows, errs = [], []
    for r in results:
        if r.get("error"):
            errs.append(dict(type=r["type"], error=r["error"]))
            continue
        for name, row in classify(r["probe"]).items():
            rows.append(dict(type=r["type"], name=name, cls=row["cls"], raw=row["raw"], plan_raw=row.get("plan_raw"),
                             **{k: row[k] for k in ("need_depth", "need_depths", "error") if k in row},
                             consumers={c: {k: v[k] for k in ("old", "old_depth", "copy_depth", "raw", "rederived_from")}
                                        for c, v in row["consumers"].items()}))
    return rows, errs


def max_release(P=None):
    try:
        return CTX.RT.wf_plan(P or CTX.P)["max_release"]
    except Exception as exc:                  # noqa: BLE001
        return f"n/a ({type(exc).__name__})"


def print_rows(rows, errs):
    for r in rows:
        if r["cls"] == "OK":
            continue
        cs = "; ".join(f"{c} {v['old']} d{v['old_depth']}" if v["old_depth"] is not None else f"{c} ok" for c, v in r["consumers"].items())
        print(f"{r['cls']:10s} {r['type']} {r['name']} raw {r['plan_raw']}->{r['raw']} need_depth {r.get('need_depth', r.get('need_depths', '-'))} | {cs}"
              + (f" | {r['error']}" if r.get("error") else ""))
    for e in errs:
        print(f"UNCHECKED  {e['type']} {e['error']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("scan", "fix"):
        s = sub.add_parser(name)
        s.add_argument("plan")
        if name == "fix":
            s.add_argument("out_plan")
            s.add_argument("--ops", required=True)
            s.add_argument("--reach-um", type=float, default=300.0)
            s.add_argument("--pin-same-depth", action="store_true")
        s.add_argument("--asbuilt", required=True)
        s.add_argument("--tree", default=None)
        s.add_argument("--tools", default=str(Path(__file__).resolve().parent))
        s.add_argument("--types", default="")
        s.add_argument("-j", type=int, default=1)
        s.add_argument("--json", default=None)
    s = sub.add_parser("apply")
    s.add_argument("plan")
    s.add_argument("ops")
    s.add_argument("out_plan")
    a = ap.parse_args(argv)

    if a.cmd == "apply":
        raw = json.loads(Path(a.plan).read_text())
        doc = json.loads(Path(a.ops).read_text())
        n, noop, conf = apply_ops(raw, doc["ops"])
        for c in conf:
            print("CONFLICT", json.dumps(c)[:400])
        if conf:
            return 1
        Path(a.out_plan).write_text(json.dumps(raw, indent=1) + "\n")
        print(f"FSTART_DEPTH_APPLY applied={n} noop={noop} conflicts=0 -> {a.out_plan}")
        return 0

    for p in (a.plan, a.asbuilt):
        if not Path(p).is_file():
            print(f"not readable: {p}", file=sys.stderr)
            return 2
    plan_abs, ab_abs = str(Path(a.plan).resolve()), str(Path(a.asbuilt).resolve())
    out_abs = str(Path(a.out_plan).resolve()) if a.cmd == "fix" else None
    ops_abs = str(Path(a.ops).resolve()) if a.cmd == "fix" else None
    json_abs = str(Path(a.json).resolve()) if a.json else None
    setup(plan_abs, ab_abs, a.tree, a.tools)
    globs = [g for g in a.types.split(",") if g]
    types = select(CTX.raw, globs)
    results, rel_before = scan(types, a.j)
    rows, errs = summarize(results)
    cnt = {}
    for r in rows:
        cnt[r["cls"]] = cnt.get(r["cls"], 0) + 1
    print_rows(rows, errs)
    print(f"FSTART_DEPTH_SCAN types {len(CTX.raw['partition_types'])} with_llr {len(types)} entries {len(rows)} "
          + " ".join(f"{k}={v}" for k, v in sorted(cnt.items())) + f" UNCHECKED={len(errs)} max_release {rel_before}")
    rep = dict(schema=SCHEMA, plan=plan_abs, asbuilt=ab_abs, tools=str(Path(a.tools).resolve()), tree=a.tree,
               types_total=len(CTX.raw["partition_types"]), types_scanned=len(types), counts=cnt, unchecked=errs,
               rows=[r for r in rows if r["cls"] != "OK"], max_release_before=rel_before)
    bad = cnt.get("MISMATCH", 0) + cnt.get("SPLIT", 0) + cnt.get("OTHER", 0) + len(errs)
    if a.cmd == "scan":
        if json_abs:
            Path(json_abs).write_text(json.dumps(rep, indent=1) + "\n")
        return 1 if bad else 0

    # fix
    raw_out = copy.deepcopy(CTX.raw)
    ops, reps, unfixed = [], [], []
    for r in results:
        if r.get("error"):
            continue
        rows_t = classify(r["probe"])
        if all(x["cls"] in ("OK", "OTHER") for x in rows_t.values()):
            continue
        tn = r["type"]
        t = CTX.raw["partition_types"][tn]
        ck, rp, uf = repick_type(tn, t, rows_t, r["tree"], set(r["ported"]), a.reach_um, a.pin_same_depth, r.get("resolved"))
        reps += rp
        unfixed += uf
        o = type_ops(tn, t.get("clock") or {}, ck)
        ops += o
        raw_out["partition_types"][tn]["clock"] = ck
    for x in reps:
        print(f"REPICK {x['cls']:12s} {x['type']} {x['name']} {x['old_raw']}(anchor d{x['old_anchor_depth']}) -> {x['new_raw']} "
              f"d{x['new_depth']} copy d{x['copy_depth']} @ {x['new_xy']} {x['dist_um']} um | START release >= reset: "
              f"{x['start_release_ok']}")
    for x in unfixed:
        print("UNFIXED", json.dumps(x))
    Path(out_abs).write_text(json.dumps(raw_out, indent=1) + "\n")
    Path(ops_abs).write_text(json.dumps(dict(
        schema=SCHEMA, row="FSTART-DEPTH-CLASS", tool="tools/die_plan/fstart_depth_fix.py", base=plan_abs,
        why="landing_local_resets raw depth + 1 != consumer reset depth (bind EMIT 'release edge would move'): re-pick the raw "
            "onto the nearest non-ported relay of the consumer depth - 1, anchor row recorded on the bound tree; 0 cycles",
        repicks_depth_change=[x for x in reps if x["cls"] == "DEPTH-CHANGE"],
        repicks_same_depth=[x for x in reps if x["cls"] == "SAME-DEPTH"],
        unfixed=unfixed, ops=ops), indent=1) + "\n")
    # re-scan the output with the same code
    setup(out_abs, ab_abs, None, a.tools)
    touched = sorted({x["type"] for x in reps})
    res2, rel_after = scan(touched, a.j)
    rows2, errs2 = summarize(res2)
    left = [r for r in rows2 if r["cls"] in ("MISMATCH", "SPLIT", "OTHER")]
    print_rows(left, errs2)
    nd = sum(1 for x in reps if x["cls"] == "DEPTH-CHANGE")
    print(f"FSTART_DEPTH_FIX types_touched {len(touched)} depth_change {nd} same_depth {len(reps) - nd} unfixed {len(unfixed)} "
          f"ops {len(ops)} rescan_left {len(left)} rescan_unchecked {len(errs2)} max_release {rel_before} -> {rel_after}")
    rep.update(repicks=reps, unfixed=unfixed, ops=len(ops), out_plan=out_abs, ops_file=ops_abs, rescan_types=touched,
               rescan_left=left, rescan_unchecked=errs2, max_release_after=rel_after)
    if json_abs:
        Path(json_abs).write_text(json.dumps(rep, indent=1) + "\n")
    return 1 if (unfixed or left or errs2 or rel_before != rel_after) else 0


if __name__ == "__main__":
    sys.exit(main())
