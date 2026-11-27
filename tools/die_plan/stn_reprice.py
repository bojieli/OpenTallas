#!/usr/bin/env python3
"""stn_reprice.py (STN-REPRICE 11-24, COORD / FABLE-RC-KV): a row that ADDS stations must re-price what it adds, in the same op set.

KV A5s: ASTKSRC (+3 lanes) and RREACH e28ef6cafd32 (+82 lanes) added registers to lane end buses and left fixed_cycles (and the
latency row) at the old depth; ISTPRICE repaired the price at a later compose step, which moved law-table members (pv_col 210,
pv_v 214) and caused the A2f/A3 refusals.  ISTCYC / R8STALE / ISTPRICE (plan_gate_pre) catch it only AFTER the row.  This tool closes it.

  stn_reprice.py wrap [--strict] [--regen-table T]... [--asbuilt AB] [--tree TREE] -- ROW.py PLAN_IN PLAN_OUT [row args]
      (a) runs the row unchanged (the row file and its sha do not move), then re-prices every lane of PLAN_OUT whose source OUT +
          destination IN station depth moved vs PLAN_IN and whose PLAN_IN fixed_cycles followed fixed = source + destination
          (the plan_gate_pre ISTCYC lane set; fixed_cycles and the latency fixed / cycles / natural move by the same delta);
          the file keeps the row's own formatting.
      (b) law-table guard: the lanes whose depth moved are looked up as members of the as-built's R8 tables (land_r8 /
          land_r8_extra: pv_col, pv_v, vport, R8 main).  A hit is a WARN line per table (report-only by default, r703); with --strict
          the plan is refused (PLAN_OUT moved to PLAN_OUT.refused, exit 3) unless a regenerated table is supplied with
          --regen-table (same file name as the plan's table, bytes differ from it).
  stn_reprice.py check PLAN --baseline-plan B [--asbuilt AB] [--tree T]     (b) + (c) on a finished plan, no row run
  (c) STNPRICE: lanes whose source OUT + destination IN station depth != fixed_cycles (plan alone; report-only LIST line in PRE).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_gate_pre as G  # noqa: E402


def stnprice_lanes(raw):
    """[(lane, src, dst, depth, fixed)] lanes with a station row on an end bus whose fixed_cycles != source + destination depth"""
    ports = {p.get("id"): p for p in raw.get("ports") or []}
    parts = {p.get("name"): p for p in raw.get("partitions") or []}
    out, n = [], 0
    for L in raw.get("lanes") or []:
        ps = [ports.get(x) for x in L.get("ports") or []]
        if not ps or not ps[0] or not ps[-1]:
            continue
        try:
            src = (parts[ps[0]["src"]["part"]]["type"], ps[0]["src"]["bus"])
            dst = (parts[ps[-1]["dst"]["part"]]["type"], ps[-1]["dst"]["bus"])
        except (KeyError, TypeError):
            continue
        n += 1
        d = G._bus_depth(raw, *src) + G._bus_depth(raw, *dst)
        fx = int(L.get("fixed_cycles", 0) or 0)
        if d and fx != d:
            out.append((L.get("id"), src, dst, d, fx))
    return out, n


def unpriced_depth_growth(raw, baseline):
    """Find extra lane-end stations that outgrow the change in the priced fixed cycles."""
    old_types = {p.get("name"): p.get("type") for p in baseline.get("partitions") or []}
    current_types = {p.get("name"): p.get("type") for p in raw.get("partitions") or []}
    ports = {p.get("id"): p for p in raw.get("ports") or []}
    old_ports = {p.get("id"): p for p in baseline.get("ports") or []}
    lanes = {lane.get("id"): lane for lane in raw.get("lanes") or []}
    old_lanes = {lane.get("id"): lane for lane in baseline.get("lanes") or []}
    for lid, (old_depth, depth) in sorted(G.depth_changed_lanes(raw, baseline).items()):
        path = lanes[lid].get("ports")
        old = old_lanes.get(lid)
        if depth <= old_depth or not old or not path or path != old.get("ports"):
            continue
        endpoints = ((path[0], "src"), (path[-1], "dst"))
        if any(ports[pid].get(end) != (old_ports.get(pid) or {}).get(end) for pid, end in endpoints):
            continue
        parts = [ports[pid][end].get("part") for pid, end in endpoints]
        if any(current_types.get(part) != old_types.get(part) for part in parts):
            continue
        old_fixed, fixed = (int(lane.get("fixed_cycles", 0) or 0) for lane in (old, lanes[lid]))
        if fixed - old_fixed < depth - old_depth:
            yield lid, old_depth, depth, old_fixed, fixed


def check_stnprice(plan, max_list=5, baseline=None):
    """Report station prices and flag baseline growth regardless of preexisting fixed-cycle overhead."""
    raw = G._load(plan) or {}
    bad, n = stnprice_lanes(raw)
    if not n:
        return []
    ex = "; ".join(f"{a} {s[0]}.{s[1]}->{d[0]}.{d[1]} depth {dp} fixed {fx}" for a, s, d, dp, fx in bad[:max_list])
    lines = [f"LIST STNPRICE {len(bad)} of {n} lanes have station depth != priced fixed_cycles (report-only; ISTCYC/ISTPRICE judge the touched / bound ones)"
             + (f": {ex}" if bad else "")]
    missing = list(unpriced_depth_growth(raw, G._load(baseline))) if baseline else []
    lines += [f"WARN ADV-IST-PRICE STATION-DELTA lane {lid}: lane-end stations {before} -> {after}, "
              f"fixed_cycles {old} -> {new}; {after - before - (new - old)} added cycle(s) lack a fixed price"
              for lid, before, after, old, new in missing[:max_list]]
    if len(missing) > max_list:
        lines.append(f"WARN ADV-IST-PRICE STATION-DELTA ... {len(missing) - max_list} more lane(s)")
    return lines


def reprice_raw(raw, braw):
    """(a) in memory: the plan_gate_pre.reprice edit.  -> {lane: (old, new)}"""
    lat = (raw.get("latency") or {}).get("lanes") or {}
    byid = {L.get("id"): L for L in raw.get("lanes") or []}
    done = {}
    for lid, _s, _d, _db, dn, _bfx, nfx in G.istcyc_lanes(raw, braw):
        if nfx == dn:
            continue
        byid[lid]["fixed_cycles"] = dn
        r = lat.get(lid)
        if r is not None:
            for f in ("fixed", "cycles", "natural"):
                if f in r:
                    r[f] = int(r[f]) + (dn - nfx)
        done[lid] = (nfx, dn)
    return done


def _upstream(raw, seeds, members, hops):
    """member lanes with a moved / re-priced lane within `hops` lanes upstream (a lane is fed by the lanes entering its source partition)"""
    ports = {p.get("id"): p for p in raw.get("ports") or []}
    src, by_dst = {}, {}
    for L in raw.get("lanes") or []:
        ps = [ports.get(x) for x in L.get("ports") or []]
        if ps and ps[0] and ps[-1]:
            src[L["id"]] = ps[0]["src"]["part"]
            by_dst.setdefault(ps[-1]["dst"]["part"], set()).add(L["id"])
    out = set()
    for l in members:
        cur = fr = {l}
        for _ in range(hops):
            fr = {u for x in fr for u in by_dst.get(src.get(x), ())} - cur
            cur = cur | fr
        if cur & seeds:
            out.add(l)
    return out


def law_hits(plan, baseline, asbuilt=None, tree=None, regen=(), upstream=0):
    """(b) {table path: [lanes whose station depth moved vs baseline and that are members of the table]}, minus supplied regenerations"""
    raw, braw = G._load(plan), G._load(baseline)
    if not raw or not braw:
        return {}
    moved = G.depth_changed_lanes(raw, braw)
    if not moved:
        return {}
    seeds = set(moved)
    bl = {L.get("id"): L for L in braw.get("lanes") or []}
    seeds |= {L["id"] for L in raw.get("lanes") or [] if L.get("id") in bl and L.get("fixed_cycles") != bl[L["id"]].get("fixed_cycles")}
    ab, mdir = None, Path(plan).parent
    if asbuilt:
        ab, mdir = G._load(asbuilt), Path(asbuilt).parent
    if not isinstance(ab, dict):
        ab = raw.get("asbuilt") if isinstance(raw.get("asbuilt"), dict) else None
    if not ab:
        return {}
    base, _ = G.manifest_paths(ab, mdir, tree or mdir)
    tabs = ([ab["land_r8"]] if ab.get("land_r8") else []) + list(ab.get("land_r8_extra") or [])
    regen = [Path(r) for r in regen]
    hits = {}
    for rel in tabs:
        tp = Path(os.path.normpath(Path(rel) if Path(rel).is_absolute() else Path(base) / rel))
        try:
            members = (json.loads(tp.read_text()) or {}).get("members") or []
        except (OSError, ValueError):
            continue
        ml = {str(m.get("lane")) for m in members}
        hit = sorted((ml & seeds) | (_upstream(raw, seeds, ml, upstream) if upstream else set()))
        if not hit:
            continue
        if any(r.name == tp.name and r.is_file() and r.read_bytes() != tp.read_bytes() for r in regen):
            continue                                            # a regenerated table of that name was supplied
        hits[str(tp)] = hit
    return hits


def _law_lines(hits, strict):
    return [f"{'FAIL' if strict else 'WARN'} STNREPRICE-LAW table {t}: {len(l)} lane(s) whose station depth moved are members "
            f"({', '.join(l[:6])}{' ...' if len(l) > 6 else ''}); supply the regenerated table (--regen-table) or restore those lanes' stations"
            for t, l in sorted(hits.items())]


def wrap(argv, a):
    row = argv
    if len(row) < 3:
        print("stn_reprice wrap: need ROW.py PLAN_IN PLAN_OUT", file=sys.stderr)
        return 2
    plan_in, plan_out = Path(row[1]), Path(row[2])
    rc = subprocess.run([sys.executable, "-I", *row]).returncode
    if not plan_out.is_file():
        return rc or 2
    text = plan_out.read_text()
    raw, braw = json.loads(text), json.loads(plan_in.read_text())
    done = reprice_raw(raw, braw)
    if done:
        try:
            import param_class_split as PCS
            plan_out.write_text(PCS._dump_like(raw, text))
        except Exception:  # noqa: BLE001
            plan_out.write_text(json.dumps(raw, indent=1, ensure_ascii=False) + "\n")
    print(f"STNREPRICE row rc {rc}: {len(done)} lane(s) re-priced" + "".join(f"\n  {k}: fixed_cycles {o} -> {n}" for k, (o, n) in sorted(done.items())[:20]))
    hits = law_hits(plan_out, plan_in, a.asbuilt, a.tree, a.regen_table, a.upstream)
    for ln in _law_lines(hits, a.strict):
        print(ln)
    if hits and a.strict:
        os.replace(plan_out, str(plan_out) + ".refused")
        print(f"STNREPRICE strict: {plan_out} refused, moved to {plan_out}.refused")
        return 3
    return rc


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("wrap")
    c = sub.add_parser("check")
    for p in (w, c):
        p.add_argument("--asbuilt")
        p.add_argument("--tree")
        p.add_argument("--regen-table", action="append", default=[])
        p.add_argument("--strict", action="store_true")
        p.add_argument("--upstream", type=int, default=0, help="also flag members with a moved lane N lanes upstream (1 = the bind put() reach seen on KV A5s; 2+ floods)")
    c.add_argument("plan")
    c.add_argument("--baseline-plan")
    if argv and argv[0] == "wrap" and "--" in argv:
        i = argv.index("--")
        a = ap.parse_args(argv[:i])
        return wrap(argv[i + 1:], a)
    a = ap.parse_args(argv)
    if a.cmd == "wrap":
        ap.error("wrap needs `-- ROW.py PLAN_IN PLAN_OUT`")
    out = check_stnprice(a.plan, baseline=a.baseline_plan)
    hits = law_hits(a.plan, a.baseline_plan, a.asbuilt, a.tree, a.regen_table, a.upstream) if a.baseline_plan else {}
    out += _law_lines(hits, a.strict)
    print("\n".join(out))
    return 3 if (hits and a.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
