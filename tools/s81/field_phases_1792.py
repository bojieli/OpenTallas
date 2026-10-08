#!/usr/bin/env python3
"""Measured per-token field phases of the actual 1,792-pair S81 mappings (s81-fieldphase, 2026-10-07).

The DS ROM 1,792 rows (unified_composition actual1792_half_dedicated / actual1792_full_shared) were partial-priced
sensitivities: the published composition + extra stage hops + a BF16-phase doubling, with the field phases of the
1,792 mapping never measured.  This tool composes them from per-stage measurements (owner rules simulate-minimum-
component / measure-at-target-context: one token at DS 1M, one layer per layer type):

  regions  per phase x region of the field vehicle runs (tools/dsrom_1m_field.py on the 2d811aafb bindings, qelem 10,
           layers 0 1 2 3 20 21 24, every region of every stage that holds the phase; OT_DSROM_FIELD_BINDING):
           [rows, go->last row write, go->idle, exact, BF pair busy] -> a compact committed file
  compose  node cycles at the actual geometry and the composed AR / MTP rows (see RULES below)

RULES (each line of the record says measured / composed / model-only):
  * phase time: the as-built sequential rule (tools/dsrom_field_reprice_r8.seq_cycles): a phase ends when the farthest
    busy region's last row is back (idle_r + wire_r) + 1; the last phase of a node at max(last_r + wire_r).
  * wire_r: the per-region field round trip of the actual mixed221 die (77ffa0428 options, tools/s81/mixed_geometry.py
    BASE, built by tools/dsrom_field_reprice_r8.py geometry --geom m221bf / m221q; the BF-flavour die for 'bf' stages,
    the q-only die for 'q' stages), max over the scan (layer) and 1-stack (layer1) die kinds, + hub return stations.
    It includes the meso d8 crossings and the S81 v9d stations, so it REPLACES the published node's f183.60 r8 wire
    + s81_die (+27) + meso_d8g1 (+4).
  * per-phase block adders (closure-cost ledger, measured on their blocks): vm_bank_group +8, gather_root_v4 +6,
    capture +3, bf_rowfix +1 = +18 a phase.  The published ledger charges them once a NODE; here once a PHASE
    (the sequential rule serialises phases), and the published node is re-based the same way for the delta.
  * BF half rate (HALF=1 element, results/rtl/s81_bf_native_20261006/half_exact: every element cycle = 2 clk, +1 pin
    +1 output cycle): a region whose BF pair is busy in the phase runs that phase at 2 x (go->idle) + 2 (UPPER BOUND:
    the return tree / root / VM write after the element really stay at full rate).  HALF dedicated: BF pairs hold only
    BF16 words, so exactly the BF16 phases; FULL shared: every phase with a busy BF pair (q words on BF pairs too).
  * a layer spread over several stages: node = MAX over its stages (the S81 composition convention: the substage dies
    work concurrently, each extra stage costs one measured hop); the serial alternative (SUM over stages) is reported
    as a sensitivity.  Model-only.
  * other layers take their type representative's delta (tools/dsrom_1m_measure.TYPES), as every field record does.
  * extra stage hops: (stages - 85) x the measured full-FEC hop (as unified_composition).

    python3 tools/s81/field_phases_1792.py regions --work W --out R.json.gz
    python3 tools/s81/field_phases_1792.py compose [--out results/uarch/dsrom_s81_field_phases_1792_20261007/composition.json]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

OUT = ROOT / "results/uarch/dsrom_s81_field_phases_1792_20261007"
MAP = ROOT / "results/uarch/dsrom_s81_mixed1792_mapping_20261007"
REPRICE = ROOT / "results/rtl/dsrom_field_reprice_r8_20261006/reprice.json"
CMP = ROOT / "results/arch/three_machine_compose/compose.json"
LINKS = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/links_full_fec.json"
PUB_GEOM, PUB_CFG = "f183.60", "asbuilt_qelem10"
WIRE_ITEMS = dict(s81_die=27, meso_d8g1=4)            # published per-node wire adders the new geometry replaces
PHASE_ADDERS = dict(vm_bank_group=8, gather_root_v4=6, capture=3, bf_rowfix=1)   # per field phase (ledger)
HALF_PIN = 2                                          # HALF=1 element: +1 pin register, +1 output register
CLK = 1.2e9
PQ_CAM_8LEAF = 4                                      # results/rtl/s81_pq_root_cam_20261007/record.json measured_delta_cycles
PQ_STAGE_C = 7                                        # stage-C fallback (modelled, default-off), unified_composition
BASE_STAGES = 85                                      # published composition geometry (f183.60, rack.json)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ regions
def cmd_regions(a):
    work = a.work.resolve()
    plan = json.loads((work / "plan.json").read_text())
    out = dict(schema="opentallas.s81.field1792.regions.v1", work=str(work), plan_sha256=sha(work / "plan.json"),
               build=json.loads((work / "build" / "build.json").read_text()).get("params"), phases={})
    bad = 0
    for ph in plan["phases"]:
        bfs = set(ph.get("bf_sites", plan["bf_sites"]))
        rows = {}
        for reg in ph["regions"]:
            r = json.loads((work / "runs" / ph["phase"] / f"r{reg:03d}" / "result.json").read_text())
            used = {p for m in ph["mats"] for _, _, p in m["regions"].get(str(reg), [])}
            rows[reg] = [r["rows"], r["go_to_last_w"], r["go_to_idle"], int(r["pass_"]), int(bool(used & bfs))]
            bad += not r["pass_"]
        out["phases"][ph["phase"]] = dict(layer=ph["layer"], node=ph["node"], stage=ph["stage"], fmts=ph["fmts"],
                                          K=ph["K"], regions=rows)
    out["region_runs"] = sum(len(p["regions"]) for p in out["phases"].values())
    out["failed"] = bad
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(a.out, "wt") as f:
        json.dump(out, f, separators=(",", ":"))
    print(a.out, out["region_runs"], "region runs,", bad, "failed")
    return 0


# ------------------------------------------------------------------------------------------------ compose
def wire_table(geo_dir, geom):
    import dsrom_field_reprice_r8 as RP
    geo = {}
    for d in RP.DIES:
        p = geo_dir / f"{d}_{geom}.json"
        if p.exists():
            geo[d] = json.loads(p.read_text())
    assert geo, (geo_dir, geom)
    return RP.wire_fn(geo, RP.hub_terms(geo)), {d: g["field_round_trip_farthest"]["cycles"] for d, g in geo.items()}


def phase_cycles(phases, wire, half, adder):
    """sequential rule (dsrom_field_reprice_r8.seq_cycles) with optional BF half-rate regions and a per-phase adder.
    phases: [regions {r: [rows, last, idle, exact, bf_busy]}]"""
    tot, ok, nph = 0, True, len(phases)
    for i, R in enumerate(phases):
        ok &= all(v[3] for v in R.values())
        sc = lambda v: (2 * v + HALF_PIN) if v is not None else None
        regs = {r: ([v[0], sc(v[1]), sc(v[2]), v[3], v[4]] if (half and v[4]) else v) for r, v in R.items()}
        if i < nph - 1:
            tot += max(max(v[2] + (wire[int(r)] if v[0] > 0 else 0) for r, v in regs.items()),
                       max(v[2] for v in regs.values())) + 1
        else:
            tot += max(v[1] + wire[int(r)] for r, v in regs.items() if v[1] is not None)
    return tot + adder * nph, ok


def node_cycles(reg, stage_flavour, wires, half, adder):
    """{node name: dict(per-stage cycles, max, sum, phases)} for one regions file"""
    grp = {}
    for name, ph in reg["phases"].items():
        node = ph["node"] if ph["node"].startswith("E1.") else f"L{ph['layer']}.{ph['node']}"
        grp.setdefault(node, {}).setdefault(ph["stage"], []).append((name, ph))
    out = {}
    for node, st in grp.items():
        per, ok, nph = {}, True, {}
        for s, lst in st.items():
            fl = stage_flavour[s]
            c, e = phase_cycles([ph["regions"] for _, ph in lst], wires[fl], half, adder)   # plan (issue) order
            per[s], nph[s] = c, len(lst)
            ok &= e
        out[node] = dict(stages=per, phases=nph, max=max(per.values()), sum=sum(per.values()), exact=ok,
                         bf16_phases=sum(1 for lst in st.values() for _, ph in lst if "bf16" in ph["fmts"]))
    return out


# Every per-token phase of the composition, its status at the 1,792 mapping and its evidence (deliverable: "every phase
# cited to committed evidence; mark which phases are still model-only").
PHASE_LEDGER = [
    dict(phase="ROM field matvec phases (q and BF16, full rate)", status="MEASURED at 1,792",
         evidence="regions/{half_dedicated,full_shared}.json.gz: tools/dsrom_1m_field.py (qelem 10 vehicle) on the hash-bound "
                  "2d811aafb bindings, layers 0 1 2 3 20 21 24, every region of every stage holding the phase, every row "
                  "bit-exact vs tools/hdc_golden_v41 (19,312 + 18,416 region runs, 0 failed)"),
    dict(phase="field wire (per-region round trip, hub return stations)", status="GEOMETRY (planned stations, not routed)",
         evidence="geometry/layer{,1}_m221{bf,q}.json: tools/dsrom_field_reprice_r8.py geometry on the actual mixed221 die "
                  "(77ffa0428 options): far round trip BF die 163 / 165, q-only die 161 / 164 cycles"),
    dict(phase="per-phase block adders vm_bank_group +8, gather_root_v4 +6, capture +3, bf_rowfix +1", status="MEASURED on blocks",
         evidence="results/rtl/dsrom_closure_cost_ledger_20261007/ledger.json items (tools/dsrom_closure_cost_ledger.py); "
                  "charged once a phase here (the published ledger charges once a node)"),
    dict(phase="BF half rate (BF16 phases on BF pairs; FULL shared: every phase with a busy BF pair)",
         status="COMPOSED UPPER BOUND from the measured element rule",
         evidence="results/rtl/s81_bf_native_20261006/half_exact/terminal.json (HALF=1 exact, element cycle = 2 clk, +1 pin "
                  "+1 output); region go->idle x 2 + 2; the HALF element is NOT in the field vehicle (its x-hold protocol "
                  "is not in the vehicle spine)"),
    dict(phase="substage concurrency (a layer over 3 stages: node = max over stages)", status="MODEL-ONLY (inherited S81 "
         "convention)", evidence="tools/dsrom_field_reprice_r8.summarise; serial (sum) alternative reported as half_rate_serial"),
    dict(phase="extra stage hops (stages - 85) x full-FEC hop", status="MEASURED hop x mapping count",
         evidence="results/rtl/dsrom_1m_allmeasured_20261004/links_full_fec.json hop + compose.json ds_rom.link_fec cable; "
                  "results/uarch/dsrom_s81_mixed1792_mapping_20261007/<v>/inventory.json stages"),
    dict(phase="PQ root CAM +1 / +2 / +4 a phase", status="MEASURED block term; PQ spine not adopted -> sensitivity only",
         evidence="results/rtl/s81_pq_root_cam_20261007/record.json measured_delta_cycles; PQ phase pipelining at 1,792 "
                  "NOT measured (the as-built sequential field is the headline basis)"),
    dict(phase="PQ CAM stage C +3 / +7", status="MODEL-ONLY (default-off fallback)", evidence="unified_composition pq_stage_b_timing"),
    dict(phase="selector +20 a segment (+22 with selt_c MRG_PIPE/RQPIPE)", status="MEASURED (+20 ledger; +22 branch bench)",
         evidence="ledger item selector; claude/s81-blocks-20261007 b17a8dda2 (selt_c bench tail mean 129 vs 127)"),
    dict(phase="softmax SAFE2 (+30 normalize, +1 exp) and exp RECUT", status="MEASURED, unchanged by the mapping",
         evidence="ledger items softmax_safe_div, softmax_exp_recut"),
    dict(phase="TP4 collectives (slab v4)", status="MEASURED, unchanged by the mapping", evidence="ledger item collective_lane"),
    dict(phase="WINDOW KV load", status="MEASURED (as composed), unchanged by the mapping",
         evidence="results/rtl/hbm_path_bandwidth_audit_20261004/dsrom_window_load.json (tools/dsrom_1m_allmeasured.py)"),
    dict(phase="index read / select / CKV gather / q.k / SU chain / head", status="MEASURED (as composed), unchanged",
         evidence="tools/dsrom_1m_allmeasured.py inputs (published composition)"),
    dict(phase="head / table / draft dies", status="MODEL-ONLY for 1,792: not re-sized for the mapping",
         evidence="unified_composition dies_note"),
]


def cmd_compose(a):
    import dsrom_1m_measure as M
    import dsrom_closure_cost_ledger as LED
    rp = json.loads(REPRICE.read_text())["geoms"][PUB_GEOM]["configs"][PUB_CFG]
    # the published per-node wire adders as the ledger in this tree charges them (s81_die +27 on main, +28 since 39e424990)
    for it, _, rows in LED.ITEMS:
        if it in WIRE_ITEMS:
            WIRE_ITEMS[it] = max(c for _, c, _ in rows)
    adder = sum(PHASE_ADDERS.values())
    rep = {L: t["rep"] for t in M.TYPES.values() for L in t["layers"]}
    c = json.loads(CMP.read_text())["ds_rom"]
    links = json.loads(LINKS.read_text())
    hop_us = links["hop"]["us"] + c["link_fec"]["full_fec"]["ii_hop_cable_us"]
    wires, far = {}, {}
    for fl, geom in (("bf", "m221bf"), ("q", "m221q")):
        wires[fl], far[fl] = wire_table(a.geo_dir, geom)
        # --extra-wire: cycles a phase the current die adds beyond the generator geometry (39e424990: 2 PQ root-row
        # stations on the m221pq layer1 die, round trip 167 + 2)
        wires[fl] = {r: w + a.extra_wire for r, w in wires[fl].items()}
    ar0, mtp0 = LED.compose([it for it, _, _ in LED.ITEMS])
    rec = dict(schema="opentallas.s81.field_phases_1792.v1", tool="tools/s81/field_phases_1792.py",
               basis=dict(published_AR_tok_s=ar0, published_MTP_tok_s=mtp0, published_geometry="f183.60, 85 stages",
                          published_field=f"{REPRICE.relative_to(ROOT)} geoms.{PUB_GEOM}.configs.{PUB_CFG} + ledger "
                                          "s81_die +27, meso_d8g1 +4 and the +18 per-phase block adders once a node",
                          hop_us=hop_us, ledger_items=[it for it, _, _ in LED.ITEMS], wire_items_replaced=dict(WIRE_ITEMS)),
               geometry=dict(far_round_trip=far, extra_wire_per_phase=a.extra_wire, dir=str(a.geo_dir.relative_to(ROOT)) if a.geo_dir.is_relative_to(ROOT) else str(a.geo_dir)),
               phase_ledger=PHASE_LEDGER, variants={})
    for v in a.variants.split(","):
        reg = json.load(gzip.open(a.regions_dir / f"{v}.json.gz", "rt"))
        bdir = MAP / v if (MAP / v).exists() else OUT / "binding" / v
        inv = json.loads((bdir / "inventory.json").read_text())
        sm_fl = json.loads((bdir / "stage_map.json").read_text())["stage_flavour"]
        stage_flavour = {i: f for i, f in enumerate(sm_fl)}
        full = node_cycles(reg, stage_flavour, wires, False, adder)
        half = node_cycles(reg, stage_flavour, wires, True, adder)
        nodes, adds = {}, {}
        for n in sorted(half):
            p = rp.get(n)
            if p is None:
                continue
            pub = p["total_cycles"] + sum(WIRE_ITEMS.values()) + adder          # as composed (adders once a node)
            # the published node with every per-phase term charged per phase (the sequential rule serialises phases:
            # the ledger's +27 / +4 wire and +18 block adders were charged once a node)
            pub_pp = p["total_cycles"] + (sum(WIRE_ITEMS.values()) + adder) * p["phases"]
            nodes[n] = dict(published=pub, published_phases=p["phases"], published_per_phase=pub_pp,
                            full_rate=full[n]["max"], half_rate=half[n]["max"], half_rate_serial=half[n]["sum"],
                            stages=half[n]["stages"], phases=half[n]["phases"], bf16_phases=half[n]["bf16_phases"],
                            exact=half[n]["exact"])
        for key, field in (("half_rate", "half_rate"), ("full_rate_bf", "full_rate"), ("half_rate_serial", "half_rate_serial"),
                           ("published_per_phase", "published_per_phase")):
            rows = []
            for n, x in nodes.items():
                d = x[field] - x["published"]
                if n.startswith("E1."):
                    rows.append((n, d, 0)); continue
                Lr, suf = n.split(".", 1)
                rows += [(f"L{L}.{suf}", d, 0) for L, r in rep.items() if r == int(Lr[1:])]
            adds[key] = rows
        comp = {}
        for key, rows in adds.items():
            extra_hops = 0 if key == "published_per_phase" else inv["stages"] - BASE_STAGES
            ar, mtp = LED.compose([it for it, _, _ in LED.ITEMS], extra=[(f"field1792_{v}_{key}", "measured 1,792 field", rows)])
            ar_us = 1e6 / ar + extra_hops * hop_us
            mtp_us = c["tau"] * 1e6 / mtp + extra_hops * hop_us
            comp[key] = dict(AR_tok_s=round(1e6 / ar_us, 1), MTP_tok_s=round(c["tau"] * 1e6 / mtp_us, 1),
                             AR_us=round(ar_us, 3), MTP_step_us=round(mtp_us, 3),
                             field_only_AR_tok_s=round(ar, 1), field_only_MTP_tok_s=round(mtp, 1),
                             sum_layer_field_delta_cycles=sum(r[1] for r in rows))
        # sensitivities on the main (half-rate) row, each composed alone on top of it
        sens = {}
        n_ph = {n: x["phases"][max(x["stages"], key=x["stages"].get)] for n, x in nodes.items()}   # on the critical stage
        def expand(rows_by_node):
            out = []
            for n, d in rows_by_node.items():
                if n.startswith("E1."):
                    out.append((n, d, 0)); continue
                Lr, suf = n.split(".", 1)
                out += [(f"L{L}.{suf}", d, 0) for L, r in rep.items() if r == int(Lr[1:])]
            return out
        for sk, srows, what in (
                ("selector_plus22", [("*.attn.idx.topk_local", 2, 0), ("*.attn.cand.topk_local", 2, 0)],
                 "selector tile +22 a segment (claude/s81-blocks-20261007 b17a8dda2 MRG_PIPE+RQPIPE bench) vs the "
                 "ledger's +20"),
                ("pq_root_cam_8leaf", expand({n: PQ_CAM_8LEAF * k for n, k in n_ph.items()}),
                 "PQ root CAM measured +4 a phase (eight-leaf, results/rtl/s81_pq_root_cam_20261007) on every field "
                 "phase, IF the PQ spine is adopted (the PQ phase pipelining itself is not measured at 1,792)"),
                ("pq_stage_c", expand({n: PQ_STAGE_C * k for n, k in n_ph.items()}),
                 "PQ CAM stage-C fallback +7 a phase (modelled, default-off)")):
            ar, mtp = LED.compose([it for it, _, _ in LED.ITEMS],
                                  extra=[(f"field1792_{v}_half_rate", "measured 1,792 field", adds["half_rate"]),
                                         (sk, what, srows)])
            ar_us = 1e6 / ar + (inv["stages"] - BASE_STAGES) * hop_us
            mtp_us = c["tau"] * 1e6 / mtp + (inv["stages"] - BASE_STAGES) * hop_us
            sens[sk] = dict(what=what, AR_tok_s=round(1e6 / ar_us, 1), MTP_tok_s=round(c["tau"] * 1e6 / mtp_us, 1),
                            AR_pct_vs_half_rate=round(100 * ((1e6 / ar_us) / comp["half_rate"]["AR_tok_s"] - 1), 3))
        rec["variants"][v] = dict(sensitivities=sens, stages=inv["stages"], layer_dies=inv["layer_dies"], extra_hops=inv["stages"] - BASE_STAGES,
                                  region_runs=reg["region_runs"], failed=reg["failed"],
                                  all_exact=reg["failed"] == 0 and all(x["exact"] for x in nodes.values()),
                                  nodes=nodes, compositions=comp)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for v, x in rec["variants"].items():
        print(v, x["stages"], x["region_runs"], "failed", x["failed"], {k: (y["AR_tok_s"], y["MTP_tok_s"]) for k, y in x["compositions"].items()})
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("regions")
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("compose")
    p.add_argument("--regions-dir", type=Path, default=OUT / "regions")
    p.add_argument("--geo-dir", type=Path, default=OUT / "geometry")
    p.add_argument("--variants", default="half_dedicated,full_shared")
    p.add_argument("--extra-wire", type=int, default=0)
    p.add_argument("--out", type=Path, default=OUT / "composition.json")
    a = ap.parse_args()
    return dict(regions=cmd_regions, compose=cmd_compose)[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
