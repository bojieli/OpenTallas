#!/usr/bin/env python3
"""QC-BANKRST-OFF1 row BANKRST-LAND (C1p, base C1o v13 aa3a14fb7484): landed ft bank reset taps re-derived at the REAL site.

bank_reset_delta.bank_xy (before QC-BANKRST-OFF1 fix) put ft station k at regs_um[k]; on a LANDED slot (band <slot>_i)
face_flops.tcl seats station k at plan stage k+1 (bit_sites_um[k] / regs_um[k+1]) and the last station at the out face.
Op (every QC type with landed slots except the two sle_su_l1 types, which SUL1-SLE-LAND covers): each u_ft_<landed>_o_<k>
sink of reset.bank_taps is measured at its real site (fixed bank_reset_delta.ft_station_xy); a bank on a core reset tap
(index >= n_reset_consumers) or over REACH from its tap moves to the nearest consumer tap with room (<= LEAF_MAX).
0 cycles, 0 flops (reset_tree pads every tap to the same depth).  Idempotent.  Every other key stays byte-identical.

usage: python3 -I bankrst_land.py PLAN_IN PLAN_OUT REPORT.json ROW.json --rt RT --tree TREE
  RT   = rt with the FIXED bank_reset_delta.py;  TREE = installed tree for reset_tree (sink_bins), e.g. launch_b716_sul1
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

EXCLUDE = ("sle_su_l1__cl5ea486db", "sle_su_l1__clc6d66f5b",   # SUL1-SLE-LAND (QC-SUL1-PLACE)
           "slw_st_a_v2__clf4365a62")                          # STAV2-F436 re-floors it: F436 re-runs this op on its own output
REACH_UM = 275.0
LEAF_MAX = 32


def plan_taps(t):
    """{tap index: (x, y)}, {mission tap indexes} from the plan's own tree record (collector_tree.taps names ->
    reset.consumer_sites_um / core_resets); core_rst* taps are lane core reset drivers, never bank taps."""
    ct = ((t.get("clock") or {}).get("landing_contract") or {}).get("collector_tree") or {}
    cs = {n: (float(x), float(y)) for n, x, y in (t.get("reset") or {}).get("consumer_sites_um") or []}
    core = {f"core_rst{i}": tuple(map(float, c.get("pin_um") or c["xy"])) for i, c in enumerate(ct.get("core_resets") or [])}
    taps, mission = {}, set()
    for i, n in enumerate(ct.get("taps") or []):
        if n in cs:
            taps[i] = cs[n]; mission.add(i)
        elif n in core:
            taps[i] = core[n]
    return taps, mission


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("report"); ap.add_argument("row")
    ap.add_argument("--rt", required=True); ap.add_argument("--tree", required=True)
    ap.add_argument("--prefix", default="")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(a.tree) / "tools" / "die_plan"))
    import fstart_reset_delta as F
    import importlib.util
    spec = importlib.util.spec_from_file_location("brd_fixed", str(Path(a.rt) / "tools" / "die_plan" / "bank_reset_delta.py"))
    B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
    assert hasattr(B, "ft_station_xy"), "rt bank_reset_delta.py lacks the landed fix"
    rb = Path(a.plan).read_bytes(); raw = json.loads(rb); ob = json.loads(rb)
    dump = F.dumper(rb, raw)
    rep = {"base_sha": hashlib.sha256(rb).hexdigest()[:12], "types": {}}
    sets = {}
    for tn, t in sorted(raw["partition_types"].items()):
        if tn in EXCLUDE or (a.prefix and not tn.startswith(a.prefix)):
            continue
        if not any(B.ft_landed(t, s.get("name")) for s in t.get("ft_slots") or []):
            continue
        rows = (t.get("reset") or {}).get("bank_taps") or []
        if not rows:
            continue
        taps, mission = plan_taps(t)
        if not taps:
            raise SystemExit(f"{tn}: bank_taps but no collector_tree tap sites in the plan")
        load, assign = {}, {}
        for r in rows:
            load[r["tap"]] = load.get(r["tap"], 0) + len(r["sinks"])
            for s in r["sinks"]:
                assign[s] = r["tap"]
        ch = []
        for s in sorted(assign):
            m = re.fullmatch(r"u_ft_(\w+?)_o_(\d+)", s)
            if not m:
                continue
            sl = next((x for x in t["ft_slots"] if x.get("name") == m.group(1)), None)
            if sl is None or not B.ft_landed(t, sl["name"]):
                continue
            xy = B.ft_station_xy(t, sl, int(m.group(2)))
            ti = assign[s]
            if xy is None or ti not in taps:
                ch.append(dict(sink=s, kept=ti, why="unmeasured")); continue
            d = B.man(xy, taps[ti])
            if ti in mission and d <= REACH_UM:
                continue
            cands = sorted((B.man(xy, taps[i]), i) for i in taps if i in mission and load.get(i, 0) < LEAF_MAX)
            if not cands:
                ch.append(dict(sink=s, kept=ti, um=round(d, 1), why="no consumer tap with room")); continue
            nd, ni = cands[0]
            if nd >= d and ti in mission:
                ch.append(dict(sink=s, kept=ti, um=round(d, 1), why="already nearest")); continue
            load[ti] -= 1; load[ni] = load.get(ni, 0) + 1; assign[s] = ni
            ch.append(dict(sink=s, site=[round(xy[0], 3), round(xy[1], 3)], was_tap=ti, was_core=ti not in mission,
                           was_um=round(d, 1), tap=ni, um=round(nd, 1), over_reach=nd > REACH_UM))
        moved = [c for c in ch if "tap" in c]
        if moved:
            by, order = {}, []
            for r in rows:
                for s in r["sinks"]:
                    by.setdefault(assign[s], []).append(s)
            t["reset"]["bank_taps"] = [dict(tap=i, sinks=by[i]) for i in sorted(by)]
            sets[tn] = {"set": {f"partition_types.{tn}.reset.bank_taps": t["reset"]["bank_taps"]}}
        rep["types"][tn] = dict(changes=ch, moved=len(moved), worst_before=max([c.get("was_um", 0) for c in moved], default=0),
                                worst_after=max([c["um"] for c in moved], default=0),
                                still_over=sum(c["over_reach"] for c in moved) + sum(1 for c in ch if c.get("why") and c.get("um", 0) > REACH_UM))
        print(f"{tn}: moved {len(moved)} worst {rep['types'][tn]['worst_before']} -> {rep['types'][tn]['worst_after']} "
              f"still_over {rep['types'][tn]['still_over']}", flush=True)
    other = [k for k in raw["partition_types"] if k not in sets]
    assert all(raw["partition_types"][k] == ob["partition_types"][k] for k in other)
    assert all(raw[k] == ob[k] for k in raw if k != "partition_types")
    Path(a.out).write_text(dump(raw))
    osha = hashlib.sha256(Path(a.out).read_bytes()).hexdigest()[:12]
    rep["out_sha"] = osha; rep["changed_types"] = sorted(sets)
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    row = dict(row="BANKRST-LAND (C1p): landed ft bank reset taps re-derived at the real landed site (stage k+1), QC family, "
                   "excl. sle_su_l1 x2 (SUL1-SLE-LAND) and slw_st_a_v2__clf4365a62 (STAV2-F436)", lane="QC-BANKRST-OFF1", base="c1o_v13", base_sha=rep["base_sha"],
               out_sha=osha, overlay={}, script="bankrst_land.py (idempotent)", types=sets)
    Path(a.row).write_text(json.dumps(row, indent=1) + "\n")
    print(f"BANKRST-LAND base {rep['base_sha']} -> {osha}; changed {len(sets)} types")
    return 0


if __name__ == "__main__":
    sys.exit(main())
