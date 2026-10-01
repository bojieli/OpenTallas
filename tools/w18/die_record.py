#!/usr/bin/env python3
"""W18: the V4.1 ROM layer-die assembly record -- one source-pinned index of the adopted die: floorplan from
real element abstracts, collective engine placement and link lane map, clock plan, hierarchical PDN and IR,
die route and crossing cycles, current management, and the hardened control blocks at 1.2 GHz.

It holds no new measurement: every figure is copied from (and pinned to) the record that measured it.

    python3 tools/w18/die_record.py --output results/physical_abi3/asap7/chip/v41_w18/die_assembly.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "results/physical_abi3/asap7/chip/v41_w18"
K = ROOT / "results/physical_abi3/asap7/chip/v41x_karb_local"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text())


def ref(p):
    return dict(record=str(Path(p).relative_to(ROOT)), sha256=sha(p))


def _adopted():
    """W18b (2026-10-01): the shrunk product die with the compact (plus) C_rotate hub, the layer plan and the
    die-level requirements from the element tiles.  INTERIM until the W10b abstracts land (the rebase chain
    re-derives these records)."""
    hs_p = D / "hub_square/hub_square.json"
    hp_p = D / "route/hubplan/hub_layer_plan.json"
    ls_p = D / "route/die_route_layer_split.json"
    if not hs_p.exists():
        return None
    hs = load(hs_p)
    return dict(
        status="INTERIM on W10b tile outlines (q pair 510.84 x 126.9, BF16 column pair 1002.89 x 142.56 um)",
        die_and_hub=dict(ref(hs_p), adopted=hs["adopted"], plus=hs["plus"], square=hs["square"],
                         strip_reference=hs["strip_reference"], rotate_on_m89=hs["rotate_on_m89"]),
        layer_plan=dict(ref(hp_p), trunks_on_m8m9=ref(ls_p),
                        rule="SU parts M1-M6, VM/bank square and other hub parts M1-M5, HBM service bands full metal, "
                             "x/result trunks M8/M9 (layer-split route, rest charged per 4x4 GCell)"),
        clock_requirement=("W10b element tiles time their I/O against neighbours on the same balanced tree (insertion "
                           "~0.43-0.51 ns at SS, in the ETMs): the die clock tree must deliver clk at abutting tile pins "
                           "balanced within ~+/-0.1 ns (input budget 0.25-0.667 ns, output -0.30 to -0.233 ns after the "
                           "ideal edge) -- a die-CTS check, open"),
        karb=dict(round_trip_cycles_by_region=[20, 16, 14, 10, 10, 14, 16, 20],
                  basis="results/rtl/chip_v41x_karb_pipe_equiv_w18_iqrep.json (MERGE2 + HEADREG + replicated pointers)",
                  closure="pslice closes; proot and pregion do not yet (see blocks_1p2ghz)"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    fp_p = D / "die_floorplan_ch8.64.json"
    fp = load(fp_p)
    lm_p = D / "collective_lane_map.json"
    lm = load(lm_p)
    ck_p = D / "clock_plan.json"
    ck = load(ck_p)
    ir_p = D / "ir/ir_stack.json"
    ir = load(ir_p)
    rt_p = D / "route/die_route_k32_ph5.json"
    rt = load(rt_p)
    cg_p = D / "route/congestion_variants.json"
    cg = load(cg_p)
    pc_p = D / "peak_current.json"
    dr_p = D / "droop_schemes_1p2ghz.json"
    dr = load(dr_p)
    fc_p = D / "field_ctrl_bench.json"
    pg_p = D / "pg_ctrl_bench.json"
    blocks = {}
    for t in ("ot_chip_v41_pg_ctrl", "ot_chip_v41_droop_ctrl", "ot_chip_v41_preramp", "ot_chip_v41_xcap",
              "ot_chip_v41_ratio_fifo_2clk"):
        p = D / "harden_1p2" / t / "corner_sta.json"
        if p.exists():
            c = load(p)
            blocks[t] = dict(ref(p), ss_setup_reg_to_reg_ps=c["setup_ss"].get("worst_reg_to_reg_slack_ps"),
                             ff_hold_reg_to_reg_ps=c["hold_ff"].get("worst_reg_to_reg_slack_ps"))
    for t in sorted(K.glob("*w18e8p5_1p2*/corner_sta.json")):
        c = load(t)
        blocks["karb/" + t.parent.name] = dict(ref(t), ss_setup_reg_to_reg_ps=c["setup_ss"].get("worst_reg_to_reg_slack_ps"),
                                               ff_hold_reg_to_reg_ps=c["hold_ff"].get("worst_reg_to_reg_slack_ps"))
    rec = dict(
        schema="opentallas.v41.w18_die_assembly.v1",
        die=dict(size_um=[fp["die"]["w_um"], fp["die"]["h_um"]], floorplan=ref(fp_p), pairs=fp["capacity"],
                 element=dict(fp["pair"], note="W10 p5 routed pair (not closed); pitch with an 8.64 um pin channel"),
                 placeholders=fp["placeholders"]),
        hbm_phy=dict(view="ot_hbm3e_phy_v41x_aw30_e8p5", orfs_check=ref(D / "orfs_check_e8p5_win_s0.json")),
        collective=dict(ref(lm_p), placement="engine at the centre of each link edge (adopted free fix)",
                        engines={k: v["engine_um"] for k, v in lm["links"].items()},
                        critical_peer_lanes={k: [r["lane"] for r in v["lanes"] if r["role"] == "critical_peer"]
                                             for k, v in lm["links"].items()},
                        vm_to_engine_cycles={k: v["vm_to_engine_cycles"] for k, v in lm["links"].items()},
                        lane_map={k: [dict(lane=r["lane"], rank=r["rank_from_vm"], role=r["role"],
                                           engine_to_lane_cycles=r["engine_to_lane_cycles"]) for r in v["lanes"]]
                                  for k, v in lm["links"].items()}),
        clock=dict(ref(ck_p), pll=ck["pll"], slow_domain=ck["domains"]["slow_0p9"]["placement"],
                   cdc_latency={c["point"]: c["latency"]["model_cycles"] for c in ck["cdc"]["points"]}),
        pdn_ir=dict(ref(ir_p), scenarios={k: dict(rail_to_rail_mv=v["rail_to_rail_mv"], pct=v["pct_of_vdd"])
                                          for k, v in ir["scenarios"].items()}, budget=ir["budget"]),
        route=dict(ref(rt_p), congestion=ref(cg_p), overflow_total=rt["global_route"].get("total", {}).get("overflow_total"),
                   reach=rt["wire_model"]["reach_basis"],
                   crossings={k: (v.get("cycles") or v.get("max_cycles")) for k, v in rt["crossings"].items()}),
        current_management=dict(adopted="50% concurrent-pair cap (ot_chip_v41_xcap) + 256-cycle schedule-driven pre-ramp "
                                         "(ot_chip_v41_preramp, holds through short gaps) + droop detector "
                                         "(ot_chip_v41_droop_ctrl)",
                                peak_current=ref(pc_p), droop=ref(dr_p), package_spec=dr.get("package_spec"),
                                benches=[ref(fc_p), ref(pg_p)]),
        blocks_1p2ghz=blocks,
        head_and_table_dies=(dict(ref(D / "head_table_fit.json"),
                                  head=load(D / "head_table_fit.json")["head_die"],
                                  table=load(D / "head_table_fit.json")["table_die"])
                             if (D / "head_table_fit.json").exists() else None),
        adopted_2026_10_01=_adopted(),
        tool_sha256=sha(Path(__file__)))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(collective=rec["collective"]["engines"], crit=rec["collective"]["critical_peer_lanes"],
                          route=rec["route"]["crossings"], ir=rec["pdn_ir"]["scenarios"],
                          blocks={k: (v["ss_setup_reg_to_reg_ps"], v["ff_hold_reg_to_reg_ps"]) for k, v in blocks.items()}),
                     indent=1))


if __name__ == "__main__":
    main()
