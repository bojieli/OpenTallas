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
LATCHECK-REALIZED-1122 (COORD 19:2x, HEAD hd_lep0N LEP-H2R-STN-1): --fixed-in-core takes a lane's fixed_cycles on trust, so
two internal_stations rows on a type WITHOUT realize_internal_stations (nothing emits them) raised lanes L2/L4 by +1 with no
register behind them, and LATCHECK passed.  With --base-plan BASE.json --base-rtl DIR (the plan of record and its RTL) every
cycle change is checked against the RTL it claims (both FAIL, exit 4):
  UNREALIZED_STATION_ROW  a type without realize_internal_stations gains internal_stations regs (new conn or more regs_um)
                          while its wrapper + every module it reaches in the RTL dirs is byte-identical to the base: the bind
                          emits no register for the row (refused: realize it, or change the core RTL that holds the stage)
  UNREALIZED_PLAN_CYCLES  a lane's table cycles changed vs the base while its RTL-observed stages (delivered minus plan-derived
                          kit_ist) did not and both end
                          types' RTL is byte-identical to the base: plan bookkeeping only
Default base (LATCHECK-BASE-1122, COORD 20:5x): without --base-plan the base is the LIVE plan of the plan's die:
$OT_LATCHECK_BASE_PLAN, else kit_wave.json dies.<die>.plan ($OT_COORD or ~/coord/autopilot/kit_wave.json), with RTL
<base dir>/published; --no-base opts out.  A base that is the plan itself, or one that cannot be read, prints
LATCHECK_BASE NONE (<why>) and the run is unchanged.
Modules resolve from the RTL dirs in order (first hit wins: e.g. the wave-prepared published/ cohort, then the gen.py rtl
output); a type with no wrapper is UNOBSERVED (listed, not a failure), as in lane_asbuilt_latency.

    gen_lane_latcheck.py PLAN.json --rtl DIR [--rtl DIR2 ...] [--landings gen_clock_landings.json]
                         [--tsv OUT.tsv] [--json OUT.json]
LATCHECK-BUILT-ONLY reports plan bus stations that are counted by LATCHECK but absent from generated RTL.
It leaves the gate unchanged. An observed RTL stage still counts even if the plan flag is unset.
Exit 0 PASS, 4 FAIL, 5 no failure but some lane UNOBSERVED (lane_asbuilt_latency's codes)."""
import argparse
import json
import os
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


MOD_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:#\s*\(|[A-Za-z_\\]\w*\s*\()", re.M)


def type_rtl_digest(plan, tn, rtl_dirs, cache=None):
    """sha256 of the type's wrapper and every module it reaches (by <module>.sv in the RTL dirs, first hit wins); None = no wrapper"""
    import hashlib
    mod = plan["partition_types"].get(tn, {}).get("module")
    if not mod:
        return None

    def find(m):
        for d in rtl_dirs:
            f = Path(d) / f"{m}.sv"
            if f.is_file():
                return f
        return None
    if find(mod) is None:
        return None
    seen, todo, h = set(), [mod], hashlib.sha256()
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        f = find(m)
        if f is None:
            continue
        t = f.read_bytes()
        h.update(m.encode() + b"\0" + t)
        todo.extend(x for x in MOD_RE.findall(t.decode(errors="replace")) if x not in seen)
    return h.hexdigest()


def _regs_by_conn(t):
    out = {}
    for e in t.get("internal_stations", []) or []:
        out[e.get("conn")] = out.get(e.get("conn"), 0) + len(e.get("regs_um") or [])
    return out


def realized_check(plan, recs, rtl_dirs, base_plan, base_recs, base_rtl):
    """LATCHECK-REALIZED-1122: cycle changes vs the plan of record must be backed by RTL that changed -> error lines"""
    errs = []
    types, btypes = plan["partition_types"], base_plan.get("partition_types", {})
    dig = {}

    def same(tn):
        if tn not in dig:
            a = type_rtl_digest(plan, tn, rtl_dirs)
            b = type_rtl_digest(base_plan, tn, base_rtl) if tn in btypes else None
            dig[tn] = a is not None and a == b
        return dig[tn]
    for tn, t in sorted(types.items()):
        if t.get("realize_internal_stations") or tn not in btypes:
            continue
        new, old = _regs_by_conn(t), _regs_by_conn(btypes[tn])
        grown = {c: (old.get(c, 0), n) for c, n in new.items() if n > old.get(c, 0)}
        if grown and same(tn):
            for c, (o, n) in sorted(grown.items()):
                errs.append(f"UNREALIZED_STATION_ROW {tn} {c}: internal_stations regs {o} -> {n} on a type without "
                            f"realize_internal_stations and its RTL is byte-identical to the base: no register is emitted "
                            f"(realize the row, or change the core RTL that holds the stage)")
    base = {r["lane"]: r for r in base_recs}

    def observed(r):
        # delivered minus the plan-derived kit stations (kit_ist = the internal_stations rows the KIT is expected to insert):
        # on a plan-generated die nothing inserts them on a type without realize_internal_stations, so they are bookkeeping
        return (r.get("delivered") or 0) - sum(int((r.get(k) or {}).get("kit_ist", 0) or 0) for k in ("source", "receiver"))
    for r in recs:
        b = base.get(r["lane"])
        if b is None or r.get("table") is None or b.get("table") is None or r["table"] == b["table"]:
            continue
        if observed(r) == observed(b) and same(r["src_type"]) and same(r["dst_type"]):
            r["verdict"] = "FAIL"
            r["class"] = list(r.get("class", [])) + ["UNREALIZED_PLAN_CYCLES"]
            errs.append(f"UNREALIZED_PLAN_CYCLES {r['lane']}: table {b['table']} -> {r['table']} but RTL-observed stages "
                        f"{observed(r)} unchanged and {r['src_type']} / {r['dst_type']} RTL byte-identical to the base")
    return errs


def live_base(plan_path, plan, env=None):
    """(base plan path, base rtl dirs, why) of the LIVE plan of this plan's die, or (None, None, why)"""
    env = os.environ if env is None else env
    c = env.get("OT_LATCHECK_BASE_PLAN")
    how = "$OT_LATCHECK_BASE_PLAN"
    if not c:
        die = (plan.get("die") or {}).get("name") if isinstance(plan.get("die"), dict) else plan.get("die")
        kw = Path(env.get("OT_COORD") or Path.home() / "coord") / "autopilot/kit_wave.json"
        try:
            c = ((json.loads(kw.read_text()).get("dies") or {}).get(die) or {}).get("plan")
        except (OSError, ValueError):
            c = None
        how = f"kit_wave.json dies.{die}.plan"
        if not c:
            return None, None, f"no live plan ({how} unreadable or unset)"
    b = Path(c)
    try:
        if not b.is_file():
            return None, None, f"{how} {c} not on this host"
        if b.resolve() == Path(plan_path).resolve() or b.read_bytes() == Path(plan_path).read_bytes():
            return None, None, f"{how} {c} is the plan itself"
    except OSError as e:
        return None, None, f"{how} {c}: {e}"
    pub = b.parent / "published"
    if not pub.is_dir():
        return None, None, f"{how} {c}: no published/ RTL beside it"
    return str(b), [str(pub)], how


def annotate_unbuilt_stations(plan, rows, module_of, type_of, landing_of, records):
    """Mark predicted bus station cycles with no register in a plan-generated wrapper."""
    observed_types = {}
    for name, typ in plan["partition_types"].items():
        stations = typ.get("internal_stations") or []
        retained = [row for row in stations if not (row.get("conn") or "").startswith("bus:")]
        observed_types[name] = dict(typ, internal_stations=retained) if retained != stations else typ
    if observed_types == plan["partition_types"]:
        return
    observed, _ = LAL.check(plan, rows, module_of, type_of, observed_types, landing_of)
    by_lane = {record["lane"]: record.get("delivered") for record in observed}
    for record in records:
        priced = record.get("delivered")
        built = by_lane.get(record["lane"])
        if priced is not None and built is not None and priced > built:
            record["unbuilt_stations"] = priced - built


def run(plan, rtl_dirs, landings=None, fixed_in_core=False, base_plan=None, base_rtl=None, base_landings=None):
    parts = parts_of(plan)
    rows, bad = lane_rows(plan)
    land = {}
    if landings:
        land = {k: int(v) for k, v in (landings.get("lane_added_cycles") or {}).items()}
    module_of, src = load_modules(plan, rtl_dirs)
    def type_of(part):
        return parts.get(part, {}).get("type")

    recs, errs = LAL.check(plan, rows, module_of, type_of, plan["partition_types"], land.get)
    annotate_unbuilt_stations(plan, rows, module_of, type_of, land.get, recs)
    recs, errs = reclassify(plan, recs, errs, fixed_in_core)
    errs = [f"LANE_ROWS {b}" for b in bad] + errs
    if base_plan is not None:
        brecs, _, _ = run(base_plan, base_rtl, base_landings, fixed_in_core)
        errs += realized_check(plan, recs, rtl_dirs, base_plan, brecs, base_rtl)
    return recs, errs, src


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--rtl", action="append", required=True, help="wrapper dir (repeatable, first hit wins)")
    ap.add_argument("--landings", help="gen.py rtl --clock-landing output gen_clock_landings.json")
    ap.add_argument("--fixed-in-core", action="store_true",
                    help="lane fixed_cycles are core-internal registers (s81_head convention)")
    ap.add_argument("--base-plan", help="LATCHECK-REALIZED-1122: plan of record the cycle changes are checked against")
    ap.add_argument("--base-rtl", action="append", help="RTL dir(s) of --base-plan (repeatable)")
    ap.add_argument("--base-landings", help="gen_clock_landings.json of --base-plan")
    ap.add_argument("--no-base", action="store_true", help="no base plan (not even the live-plan default)")
    ap.add_argument("--tsv")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    landings = json.loads(Path(a.landings).read_text()) if a.landings else None
    why = "--base-plan"
    if not a.base_plan and not a.no_base:
        a.base_plan, a.base_rtl, why = live_base(a.plan, plan)
    elif a.no_base:
        why = "--no-base"
    base = json.loads(Path(a.base_plan).read_text()) if a.base_plan else None
    if base is not None and not a.base_rtl:
        ap.error("--base-plan needs --base-rtl")
    print(f"LATCHECK_BASE {a.base_plan} ({why})" if base is not None else
          f"LATCHECK_BASE NONE ({why}; in-core cycle changes unchecked)")
    recs, errs, src = run(plan, a.rtl, landings, a.fixed_in_core, base, a.base_rtl,
                          json.loads(Path(a.base_landings).read_text()) if a.base_landings else None)
    sm_fixed = sum(1 for r in recs if r.get("fixed_in_core"))
    sm = LAL.summary(recs)
    unbuilt = [r for r in recs if r.get("unbuilt_stations")]
    sm.update(plan=str(a.plan), rtl=a.rtl, landings=a.landings, modules=src, mode="gen", fixed_in_core=sm_fixed,
              built_only=dict(lanes=len(unbuilt), cycles=sum(r["unbuilt_stations"] for r in unbuilt)))
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
    for r in unbuilt[:40]:
        print(f"LATCHECK_BUILT_ONLY {r['lane']} priced {r['delivered']} "
              f"built {r['delivered'] - r['unbuilt_stations']} "
              f"({r['src_type']}.{r['bus_out']} -> {r['dst_type']}.{r['bus_in']})")
    print("LANE_ASBUILT", json.dumps({k: v for k, v in sm.items() if k != "modules"}))
    return 4 if errs else 5 if sm["unobserved"] else 0


if __name__ == "__main__":
    sys.exit(main())
