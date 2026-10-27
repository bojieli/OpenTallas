#!/usr/bin/env python3
"""KV related-pair die STA with REAL hard-core views where they exist (CLOCK-KV-R15; METHODOLOGY 12.4a).

    kv_realview_sta.py TAPDIR --plan PLAN.json --manifest kv_realview_manifest.json --out OUT
                       [--repo ROOT] [--accept signed|closed|any] [--corner TT --corner FF]

Wraps die_sta_related.py (same tap arrivals, CPPR credit, pin-register characterisation, uncertainties, classes):
  1. runs the unchanged declared-budget tool (die_sta_related.main) -> OUT/declared/die_sta_related.json;
  2. adds the hard-core interface timing from each accepted view's liberty ETM (manifest: type -> status + lib_tt/lib_ff):
     per core type and corner, from the .lib (related_pin = a core clock pin):
       ins_late / ins_early  = max_clock_tree_path / min_clock_tree_path (max of rise/fall; min of rise/fall)
       hold_in   = max hold_rising constraint over input pins     setup_in = max setup_rising constraint
       q_min     = min rising_edge cell delay at index 0 over outputs  q_max = max rising_edge cell delay at the
                   index nearest the seam load (--seam-wire-um x --wire-ff-per-um, as die_sta_related)
     ETM arcs are referenced to the core clock PIN and contain the core tree.  12.3 v5.0 early tap: the parent taps the
     core earlier by its insertion, modelled EXACT per corner: core clock pin = tap + L - ins_late (L = declared common
     latency, 250, cancels as in die_sta_related).  So, against a partition pin register P (DFFHQNx1, declared):
       P -> core in   setup = T - us - (La + qP_max) + Ce - (setup_in + ins_late) + cr
                      hold  = (Ea + qP_min) - Cl - (hold_in - ins_late) - uh + cr
       core out -> P  setup = T - us - (La - ins_late + q_max) + Ce - sP + cr
                      hold  = (Ea - ins_late + q_min) - Cl - hP - uh + cr
     (La/Ea/Cl/Ce = launch/capture tap late/early arrivals.)  The ETM's own late/early clock spread is inside its arcs.
  3. Which taps host cores: each hard-core instance (plan partition_types.*.hard_cores, die frame via schema to_die) is
     put under the partition tap nearest its outline centre.  INTRA pairs (complete, every ordered tap pair of a
     partition, as die_sta_related) are re-timed for every (P|core) x (P|core) endpoint combination the two taps host
     (core<->core uses the core arcs on both ends).  SEAM pairs end on partition pin registers (partition faces): no
     partition kit exists, so seams stay declared-budget; the count of real-view blocks on seams is reported (0 unless
     a partition view is added to the manifest -- not implemented: refuses).
Every number carries the count of real-view vs declared-budget block types/instances.  Opt-in tool; die_sta_related
defaults are unchanged.
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_sta_related as DSR  # noqa: E402

RANK = {"signed": 3, "stale-signed": 2, "closed": 2, "stale-closed": 1, "routed": 1, "none": 0}
ACCEPT = {"signed": {"signed", "stale-signed"}, "closed": {"signed", "stale-signed", "closed", "stale-closed"},
          "any": {"signed", "stale-signed", "closed", "stale-closed", "routed"}}


def _groups(txt, key):
    """yield (header_arg, body) for every `key(arg) { ... }` group (brace matched)."""
    for m in re.finditer(key + r'\s*\(\s*"?([^")]*)"?\s*\)\s*\{', txt):
        i, depth = m.end(), 1
        while depth and i < len(txt):
            c = txt[i]
            depth += (c == "{") - (c == "}")
            i += 1
        yield m.group(1), txt[m.end():i - 1]


def _vals(body, table):
    out = []
    for m in re.finditer(table + r'\s*\([^)]*\)\s*\{(.*?)\}', body, re.S):
        v = re.search(r'values\s*\((.*?)\)\s*;', m.group(1), re.S)
        idx = re.search(r'index_1\s*\(\s*"([^"]*)"', m.group(1))
        nums = [float(x) for x in re.findall(r'-?\d+\.?\d*(?:[eE]-?\d+)?', v.group(1))] if v else []
        out.append((nums, [float(x) for x in idx.group(1).split(",")] if idx else None))
    return out


def lib_arcs(path, load_ff):
    txt = Path(path).read_text()
    r = dict(ins_late=None, ins_early=None, hold_in=None, setup_in=None, q_min=None, q_max=None, n_in=0, n_out=0)
    for _pin, body in _groups(txt, "pin"):
        for _t, tb in _groups(body, "timing"):
            tt = re.search(r'timing_type\s*:\s*(\w+)', tb)
            if not tt:
                continue
            tt = tt.group(1)
            if tt in ("max_clock_tree_path", "min_clock_tree_path"):
                v = [x for n, _ in _vals(tb, "cell_rise") + _vals(tb, "cell_fall") for x in n]
                if tt.startswith("max"):
                    r["ins_late"] = max(v + ([r["ins_late"]] if r["ins_late"] is not None else []))
                else:
                    r["ins_early"] = min(v + ([r["ins_early"]] if r["ins_early"] is not None else []))
            elif tt in ("hold_rising", "setup_rising"):
                v = [x for n, _ in _vals(tb, "rise_constraint") + _vals(tb, "fall_constraint") for x in n]
                k = "hold_in" if tt == "hold_rising" else "setup_in"
                r[k] = max(v + ([r[k]] if r[k] is not None else []))
                r["n_in"] += tt == "hold_rising"
            elif tt == "rising_edge":
                r["n_out"] += 1
                for n, idx in _vals(tb, "cell_rise") + _vals(tb, "cell_fall"):
                    if not n:
                        continue
                    qmin = n[0]
                    j = min(range(len(idx)), key=lambda i: abs(idx[i] - load_ff)) if idx else 0
                    qmax = n[min(j, len(n) - 1)] if idx else max(n)
                    r["q_min"] = qmin if r["q_min"] is None else min(r["q_min"], qmin)
                    r["q_max"] = qmax if r["q_max"] is None else max(r["q_max"], qmax)
    return r


def core_sites(plan_path):
    import schema as S
    P = S.Plan(S.load(plan_path))
    out = []
    for p, inst in P.parts.items():
        t = P.types[inst["type"]]
        for c in t.get("hard_cores", []) or []:
            (ox, oy), (w, h) = c["origin_um"], c["outline_um"]
            if c.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
                w, h = h, w
            out.append(dict(part=p, inst=c["inst"], module=c["module"],
                            xy=[float(v) for v in P.to_die(p, (ox + w / 2, oy + h / 2))]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tapdir")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default=str(HERE.parents[1]))
    ap.add_argument("--accept", choices=sorted(ACCEPT), default="signed")
    ap.add_argument("--corner", action="append")
    ap.add_argument("--clock-tool", default=str(HERE))
    ap.add_argument("--seam-wire-um", type=float, default=40.0)
    ap.add_argument("--wire-ff-per-um", type=float, default=0.15)
    a = ap.parse_args(argv)
    corners = a.corner or ["TT", "FF"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dec = out / "declared"
    DSR.main([a.tapdir, "--plan", a.plan, "--out", str(dec), "--clock-tool", a.clock_tool]
             + sum((["--corner", c] for c in corners), []))
    D = json.loads((dec / "die_sta_related.json").read_text())
    man = json.loads(Path(a.manifest).read_text())
    if any(v.get("kind") == "partition" for v in man["types"].values()):
        raise SystemExit("partition views: not implemented (no partition kit exists for KV)")
    sites = core_sites(a.plan)
    inst_by_mod = defaultdict(int)
    for s in sites:
        inst_by_mod[s["module"]] += 1
    load = a.seam_wire_um * a.wire_ff_per_um
    real = {}
    for m, v in man["types"].items():
        if v.get("status") not in ACCEPT[a.accept] or not v.get("lib_tt"):
            continue
        arcs = {}
        for c in corners:
            lp = Path(v["lib_" + c.lower()])
            lp = lp if lp.is_absolute() else Path(a.repo) / lp
            arcs[c] = lib_arcs(lp, load)
        real[m] = dict(status=v["status"], arcs=arcs, instances=inst_by_mod.get(m, 0))
    d = Path(a.tapdir)
    mesh = json.loads((d / "mesh.json").read_text())
    txy = {t["port"]: t["xy"] for t in mesh["taps"]}
    by_part = defaultdict(list)
    for t in mesh["taps"]:
        by_part[t["part"]].append(t["port"])
    host = defaultdict(set)          # tap -> real core modules under it
    for s in sites:
        if s["module"] in real and by_part.get(s["part"]):
            tp = min(by_part[s["part"]], key=lambda p: (txy[p][0] - s["xy"][0]) ** 2 + (txy[p][1] - s["xy"][1]) ** 2)
            host[tp].add(s["module"])
    n_types = len({s["module"] for s in sites})
    counts = dict(core_types_total=n_types, core_instances_total=len(sites),
                  core_types_real=len([m for m in real if real[m]["instances"]]),
                  core_instances_real=sum(r["instances"] for r in real.values()),
                  partition_types_total=len(json.loads(Path(a.plan).read_text())["partition_types"]),
                  partition_types_real=0, taps_hosting_real_cores=len(host))
    res = dict(declared=str(dec / "die_sta_related.json"), accept=a.accept, counts=counts,
               real_views={m: dict(status=r["status"], instances=r["instances"],
                                   arcs={c: {k: (round(x, 2) if isinstance(x, float) else x) for k, x in v.items()}
                                         for c, v in r["arcs"].items()}) for m, r in real.items()},
               model="ETM arcs at the core clock pin, exact early-tap compensation by ins_late per corner (12.3 v5.0)",
               corners={})
    for c in corners:
        meta, taps = DSR.load_taps(d, c)
        rng = meta["cppr_node_range_ps"]
        reg = D["corners"][c]["register"]
        pairs, _ = DSR.build_pairs(json.loads(Path(a.plan).read_text()), taps)
        T, us, uh = D["period_ps"], DSR.UNC_SETUP_PS, DSR.UNC_HOLD_PS
        ws = wh = None
        n = 0
        per_mod = defaultdict(lambda: [None, None])
        for x, y, part in pairs["intra"]:
            if x not in host and y not in host:
                continue
            A, B = taps[x], taps[y]
            la, ea, lc, ec = A["late_ps"], A["early_ps"], B["late_ps"], B["early_ps"]
            cr = DSR.credit(rng, A["cppr_node"] if A["cppr_node"] == B["cppr_node"] else "h", la, ea, lc, ec)
            L = [None] + sorted(host.get(x, ()))
            C = [None] + sorted(host.get(y, ()))
            for lm in L:
                for cm in C:
                    if lm is None and cm is None:
                        continue      # P -> P is the declared-budget pair already timed by die_sta_related
                    if lm is None:
                        q_max, q_min = reg["clkq_max_wire_ps"], reg["clkq_min_nowire_ps"]
                    else:
                        r = real[lm]["arcs"][c]
                        q_max, q_min = r["q_max"] - r["ins_late"], r["q_min"] - r["ins_late"]
                    if cm is None:
                        su, ho = reg["setup_ps"], reg["hold_ps"]
                    else:
                        r = real[cm]["arcs"][c]
                        su, ho = r["setup_in"] + r["ins_late"], r["hold_in"] - r["ins_late"]
                    s = T - us - (la + q_max) + ec - su + cr
                    h = (ea + q_min) - lc - ho - uh + cr
                    n += 1
                    tag = (lm or "P") + "->" + (cm or "P")
                    if ws is None or s < ws[0]:
                        ws = (round(s, 2), x, y, tag)
                    if wh is None or h < wh[0]:
                        wh = (round(h, 2), x, y, tag)
                    pm = per_mod[tag]
                    pm[0] = s if pm[0] is None else min(pm[0], s)
                    pm[1] = h if pm[1] is None else min(pm[1], h)
        dc = D["corners"][c]["classes"]
        res["corners"][c] = dict(
            real_core_endpoint_pairs=n,
            intra_real=dict(worst_setup_ps=ws and ws[0], worst_setup=ws, worst_hold_ps=wh and wh[0], worst_hold=wh),
            intra_real_by_endpoint={k: dict(setup_ps=round(v[0], 2), hold_ps=round(v[1], 2)) for k, v in sorted(per_mod.items())},
            intra_declared=dict(setup_ps=dc["intra"]["worst_setup_slack_ps"], hold_ps=dc["intra"]["worst_hold_slack_ps"],
                                kit_contract_hold_ps=(dc["intra"].get("kit_contract_hold") or {}).get("worst_hold_bound_ps")),
            seam_declared=dict(setup_ps=dc["seam"]["worst_setup_slack_ps"], hold_ps=dc["seam"]["worst_hold_slack_ps"],
                               kit_contract_hold_ps=(dc["seam"].get("kit_contract_hold") or {}).get("worst_hold_bound_ps")))
        cc = res["corners"][c]
        print(f"{c} intra P->P declared setup {cc['intra_declared']['setup_ps']} hold {cc['intra_declared']['hold_ps']} "
              f"kit {cc['intra_declared']['kit_contract_hold_ps']} | seam declared setup {cc['seam_declared']['setup_ps']} "
              f"hold {cc['seam_declared']['hold_ps']} kit {cc['seam_declared']['kit_contract_hold_ps']}")
        print(f"{c} intra REAL-core endpoints ({n} pair-combos, {counts['core_types_real']}/{n_types} core types, "
              f"{counts['core_instances_real']}/{len(sites)} instances real): setup {ws} hold {wh}")
    res["status"] = "UNCHECKED (NUMBER-CHECK pending)"
    (out / "kv_realview_sta.json").write_text(json.dumps(res, indent=1) + "\n")
    print("COUNTS", json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
