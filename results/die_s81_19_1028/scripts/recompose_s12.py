#!/usr/bin/env python3
"""DIE-S81-19 plan_s12: re-compose the plan_s11 landing network with the ACTUAL S81 observer.

plan_s11(e) carries the DIE-S81-2 r98 landing compose whose collector root is s_4S_L3 with the QC default observer
(qfd_sys_face_lctx3_wrapped) -> strict bind validate_observer must fail. This script
  1. un-composes plan_s11e EXACTLY: every landing cohort clone (landing_base_type) folds back to its base type (clones are
     asserted identical once the compose-only fields are removed), clock.landing_contract / fclk_* edge clocks /
     clock.landing_network removed, reset.in_sites renamed to the base type;
  2. re-runs the EXISTING main clock_landing_plan.compose (monitor=reset, default bands) with the SAME landing table
     (die-s81-2/reg/landed_crossings.json, 98 regions, +3/crossing) and observer_part=seqhost,
     observer = dsdv_hostb_dstat u_u_dst fault vid_ri / ready alive_i (PD7d S81-UNBLOCK-3 spec, define S81_HOSTB_LAND_OBS);
  3. writes plan + sidecar. Latency is regenerated afterwards with gen.py latency --inplace.
usage: recompose_s12.py PLAN_IN TABLE OUT_PLAN OUT_SIDECAR [--check-roundtrip OUT]"""
import copy, json, sys, time, hashlib
sys.path.insert(0, 'tools/die_plan')
import clock_landing_plan as CLP

OBS = dict(module="dsdv_hostb_dstat", instance_suffix="u_u_dst", fault_port="vid_ri", ready_port="alive_i")
OBS_PART = "seqhost"


def strip_type(t):
    t = copy.deepcopy(t)
    for k in ("module", "note", "landing_base_type"):
        t.pop(k, None)
    c = t.get("clock", {})
    c.pop("landing_contract", None)
    if "edge_clocks" in c:
        c["edge_clocks"] = [e for e in c["edge_clocks"] if not e["port"].startswith(("fclk_", "cland_"))]
        if not c["edge_clocks"]:
            c.pop("edge_clocks")
    return t


def uncompose(raw):
    raw = copy.deepcopy(raw)
    T = raw["partition_types"]
    clones = {n: t["landing_base_type"] for n, t in T.items() if "landing_base_type" in t}
    groups = {}
    for n, b in clones.items():
        groups.setdefault(b, []).append(n)
    newT = {}
    for n, t in T.items():
        if n in clones:
            continue
        s = copy.deepcopy(t)
        c = s.get("clock", {})
        c.pop("landing_contract", None)
        if "edge_clocks" in c:
            c["edge_clocks"] = [e for e in c["edge_clocks"] if not e["port"].startswith(("fclk_", "cland_"))]
            if not c["edge_clocks"]:
                c.pop("edge_clocks")
        newT[n] = s
    for b, ns in sorted(groups.items()):
        assert b not in T, b
        s0 = strip_type(T[ns[0]])
        for n in ns[1:]:
            if strip_type(T[n]) != s0:
                raise SystemExit(f"cohort clones of {b} differ beyond compose fields: {ns[0]} vs {n}")
        base = copy.deepcopy(T[ns[0]])
        base.pop("landing_base_type")
        base["module"] = b
        note = base.get("note", "")
        i = note.find(";clock landing cohort from")
        if i >= 0:
            base["note"] = note[:i]
        c = base.get("clock", {})
        c.pop("landing_contract", None)
        if "edge_clocks" in c:
            c["edge_clocks"] = [e for e in c["edge_clocks"] if not e["port"].startswith(("fclk_", "cland_"))]
            if not c["edge_clocks"]:
                c.pop("edge_clocks")
        newT[b] = base
    # residual special buses must be zero (compose's _finish moves them into landing_contract)
    for n, t in newT.items():
        if any(x["name"].startswith(("fclk_", "cland_")) for x in t.get("buses", [])):
            raise SystemExit(f"{n}: residual fclk_/cland_ bus")
    raw["partition_types"] = newT
    for p in raw["partitions"]:
        p["type"] = clones.get(p["type"], p["type"])
    ins = raw.get("reset", {}).get("in_sites", {})
    for n in list(ins):
        if n in clones:
            v = ins.pop(n)
            b = clones[n]
            if b in ins and ins[b] != v:
                raise SystemExit(f"reset in_site of {b} differs across cohorts")
            ins[b] = v
    raw["clock"].pop("landing_network", None)
    return raw, clones


def main():
    a = sys.argv[1:]
    plan_in, table, outp, outs = a[:4]
    raw = json.load(open(plan_in))
    tab = json.load(open(table))
    base, clones = uncompose(raw)
    print(json.dumps(dict(stage="uncompose", types_in=len(raw["partition_types"]), clones=len(clones),
                          types_base=len(base["partition_types"]))), flush=True)
    t0 = time.time()
    if "--check-roundtrip" in a:
        # Proof of the un-compose: re-composing with the ORIGINAL r98 observer must reproduce plan_s11e's types.
        root = raw["clock"]["landing_network"]["root_observer"]["part"]
        rt, _ = CLP.compose(base, tab, plan_path=plan_in, observer_part=root)
        ok_types = sorted(rt["partition_types"]) == sorted(raw["partition_types"])
        same = sum(1 for n in raw["partition_types"] if rt["partition_types"].get(n) == raw["partition_types"][n])
        net = rt["clock"]["landing_network"] == raw["clock"]["landing_network"]
        parts = [p["type"] for p in rt["partitions"]] == [p["type"] for p in raw["partitions"]]
        print(json.dumps(dict(stage="roundtrip", observer_part=root, type_names_equal=ok_types, types_identical=same,
                              types_total=len(raw["partition_types"]), landing_network_equal=net, part_types_equal=parts,
                              secs=round(time.time() - t0, 1))), flush=True)
        json.dump(rt, open(a[a.index("--check-roundtrip") + 1], "w"), indent=1)
        return
    new, side = CLP.compose(base, tab, plan_path=plan_in, observer_part=OBS_PART, observer=dict(OBS))
    new["note"] = (new.get("note", "") + "; DIE-S81-19 10-28 plan_s12: plan_s11e landings re-composed (same r98 98-region table) "
                   "with the ACTUAL S81 observer seqhost dsdv_hostb_dstat u_u_dst (fault vid_ri / ready alive_i, define S81_HOSTB_LAND_OBS)")
    json.dump(new, open(outp, "w"), indent=1)
    json.dump(side, open(outs, "w"), indent=1)
    c = side["collector"]
    print(json.dumps(dict(stage="compose", observer=c["observer"], types_after=len(new["partition_types"]),
                          ports=len(new["ports"]), infra_edges=len(new["clock"]["landing_network"]["edges"]),
                          placement_failures=len(c["placement_failures"]), max_monitor_hop_um=c["max_die_hop_um"],
                          boot_ready_cycles=c["boot_budget"]["ready_at_glue_max_cycles"], secs=round(time.time() - t0, 1))))


if __name__ == "__main__":
    main()
