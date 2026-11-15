#!/usr/bin/env python3
"""HEAD-BIND-1 11-14: LATCHECK-1 (lane_asbuilt_latency.check) on a PLAN-GENERATED die (gen.py rtl / gen.py phys).

A die whose kit RTL is the plan's own generated wrappers (s81_head: kit RTL = gen.py phys bootstrap + raw patch, no
as-built GEN die top, no bind.py partitioning) has no bind output dir for lane_asbuilt_latency.py to read.  The
generated wrappers carry the same lane-stage instances the bind emits (gen_rtl.py: u_bout_<o>[_pad<j>],
u_bin_<i>[_pad<j>], u_blk_<o>, kit-inserted u_ist_/u_lpad_), so the SAME check() runs on them, with three readers
replaced:
  rows     one per plan lane: source = the lane's first port src (part, bus), receiver = its last port dst (part, bus)
           (bind.py link rows are the same end pair; the ft hops in between come from plan_hops as in a bind)
  ft       gen_rtl names a ft slot <s>'s stations u_ft_<s>_s<j> (+ cross-tap hop u_fx_<s>_s<j>); plan_hops gives the
           outgoing bus <s>_o, so ModuleIndex.ft counts u_f[tx]_<s>_s<j> (bind: u_f[tx]_<s>_o_<k>; both accepted)
  landing  gen_clock_landings.json lane_added_cycles (gen.py rtl --clock-landing), the generated count-aligned rings
--fixed-in-core (s81_head convention, tools/s81_head/head_transport_depth.py + head_host_split_delta.py): a lane's
  fixed_cycles are registers INSIDE the source / destination core (e.g. CTL_PRE x_o +1, host W core L0_STAGE), not
  wrapper stages; the wrapper transport must equal table - fixed_cycles.  Such a lane passes as FIXED_IN_CORE (the
  cycles are recorded, their proof is the core's own).  Without the flag the lane fails as in a bind.
Failure classes added here (report only; the gate is delivered == table): PLAN_STATIONS_UNPRICED = the excess is
exactly the u_ist_ stations already in the generated wrappers (plan internal_stations, kit_istations FIRM) that the
plan latency table (schema.lane_natural: boundary + ft stations + fixed + landing) does not count.
Modules resolve from the RTL dirs in order (first hit wins: e.g. the wave-prepared published/ cohort, then the gen.py rtl
output); a type with no wrapper is UNOBSERVED (listed, not a failure), as in lane_asbuilt_latency.

    gen_lane_latcheck.py PLAN.json --rtl DIR [--rtl DIR2 ...] [--landings gen_clock_landings.json]
                         [--tsv OUT.tsv] [--json OUT.json]
Exit 0 PASS, 4 FAIL, 5 no failure but some lane UNOBSERVED (lane_asbuilt_latency's codes)."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lane_asbuilt_latency as LAL  # noqa: E402


class GenModuleIndex(LAL.ModuleIndex):
    """ModuleIndex that also counts gen_rtl ft station names (u_ft_<slot>_s<j>, u_fx_<slot>_s<j>)"""

    def ft(self, o):
        n = super().ft(o)
        if n:
            return n
        slot = o[:-2] if o.endswith("_o") else o
        rx = re.compile(rf"u_f[tx]_{re.escape(slot)}_s(\d+)")
        return sum(1 for k in self.inst if rx.fullmatch(k))


def parts_of(plan):
    p = plan["partitions"]
    return {x["name"]: x for x in p} if isinstance(p, list) else p


def lane_rows(plan):
    """bind_latency-shaped rows: one per plan lane with ports (source end, receiver end)"""
    ports = {x["id"]: x for x in plan.get("ports", [])}
    table = plan.get("latency", {}).get("lanes", {})
    rows, bad = [], []
    for ln in plan.get("lanes", []):
        hp = [ports[q] for q in ln.get("ports", []) if q in ports]
        if not hp:
            continue
        if len(hp) != len(ln.get("ports", [])):
            bad.append(f"lane {ln['id']}: {len(ln['ports']) - len(hp)} port id(s) not in plan.ports")
        a, z = hp[0], hp[-1]
        if a["src"]["part"].startswith("@") or z["dst"]["part"].startswith("@"):
            continue                          # die IO lane end: no partition register pair to count
        rows.append(dict(lane=ln["id"], src=a["src"]["part"], dst=z["dst"]["part"], bus_out=a["src"]["bus"],
                         bus_in=z["dst"]["bus"], plan_cycles=table.get(ln["id"], {}).get("cycles")))
    return rows, bad


def load_modules(plan, rtl_dirs):
    """partition -> GenModuleIndex (or None when its type's wrapper is in no RTL dir); -> (module_of, sources)"""
    parts, types = parts_of(plan), plan["partition_types"]
    idx, src = {}, {}

    def find(mod):
        for d in rtl_dirs:
            f = Path(d) / f"{mod}.sv"
            if f.is_file():
                return f
        return None

    def module_of(p):
        t = types.get(parts.get(p, {}).get("type"), {})
        mod = t.get("module")
        if mod not in idx:
            f = find(mod) if mod and not t.get("hard") else None
            idx[mod] = GenModuleIndex(f.read_text(errors="replace")) if f else None
            src[mod] = str(f) if f else None
        return idx[mod]
    return module_of, src


def reclassify(plan, recs, errs, fixed_in_core):
    """FIXED_IN_CORE passes (opt-in) and the PLAN_STATIONS_UNPRICED class; -> (recs, errs)"""
    fixed = {x["id"]: int(x.get("fixed_cycles", 0) or 0) for x in plan.get("lanes", [])}
    drop = set()
    for r in recs:
        if r["verdict"] != "FAIL":
            continue
        fx = fixed.get(r["lane"], 0)
        # HEAD-99 11-15 (FABLE-TRIAGE-HEADKV s17b): kit / bound stations (kit_ist, bound_ist) on the lane already count in `delivered`; the in-core
        # fixed cycles that remain unobserved are fx - min(fx, observed kit stations).  delta must equal minus that.
        obs = sum(int(r.get(side, {}).get(k, 0) or 0) for side in ("source", "receiver") for k in ("kit_ist", "bound_ist"))
        if fixed_in_core and fx and r["delta"] == -(fx - min(fx, obs)) and not r.get("problems"):
            r.update(verdict="PASS", fixed_in_core=fx, kit_stations_observed=obs)
            r.pop("class", None)
            drop.add(r["lane"])
            continue
        ist = int(r.get("source", {}).get("bound_ist", 0)) + int(r.get("receiver", {}).get("bound_ist", 0))
        if ist and r["delta"] == ist:
            r["class"] = [c for c in r.get("class", []) if c != "OTHER"] + ["PLAN_STATIONS_UNPRICED"]
    out = [e for e in errs if not any(e.startswith(f"LANE_ASBUILT {ln}:") for ln in drop)]
    return recs, out


def run(plan, rtl_dirs, landings=None, fixed_in_core=False):
    parts = parts_of(plan)
    rows, bad = lane_rows(plan)
    land = {}
    if landings:
        land = {k: int(v) for k, v in (landings.get("lane_added_cycles") or {}).items()}
    module_of, src = load_modules(plan, rtl_dirs)
    recs, errs = LAL.check(plan, rows, module_of, lambda p: parts.get(p, {}).get("type"), plan["partition_types"],
                           land.get)
    recs, errs = reclassify(plan, recs, errs, fixed_in_core)
    errs = [f"LANE_ROWS {b}" for b in bad] + errs
    return recs, errs, src


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--rtl", action="append", required=True, help="wrapper dir (repeatable, first hit wins)")
    ap.add_argument("--landings", help="gen.py rtl --clock-landing output gen_clock_landings.json")
    ap.add_argument("--fixed-in-core", action="store_true",
                    help="lane fixed_cycles are core-internal registers (s81_head convention)")
    ap.add_argument("--tsv")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    landings = json.loads(Path(a.landings).read_text()) if a.landings else None
    recs, errs, src = run(plan, a.rtl, landings, a.fixed_in_core)
    sm_fixed = sum(1 for r in recs if r.get("fixed_in_core"))
    sm = LAL.summary(recs)
    sm.update(plan=str(a.plan), rtl=a.rtl, landings=a.landings, modules=src, mode="gen", fixed_in_core=sm_fixed)
    if a.json:
        Path(a.json).write_text(json.dumps(dict(summary=sm, lanes=recs, errors=errs), indent=1) + "\n")
    if a.tsv:
        with open(a.tsv, "w") as f:
            f.write("lane\tsrc\tsrc_type\tbus_out\tdst\tdst_type\tbus_in\ttable\tdelivered\tdelta\tft\tlanding\tverdict\tclass\n")
            for r in recs:
                f.write("\t".join(str(x) for x in (r["lane"], r["src"], r["src_type"], r["bus_out"], r["dst"], r["dst_type"],
                                                   r["bus_in"], r["table"], r.get("delivered", ""), r.get("delta", ""),
                                                   r.get("ft", ""), r.get("landing", ""), r["verdict"],
                                                   "+".join(r.get("class", [])))) + "\n")
    for e in errs:
        print(e)
    print("LANE_ASBUILT", json.dumps({k: v for k, v in sm.items() if k != "modules"}))
    return 4 if errs else 5 if sm["unobserved"] else 0


if __name__ == "__main__":
    sys.exit(main())
