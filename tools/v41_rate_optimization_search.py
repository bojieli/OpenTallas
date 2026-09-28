#!/usr/bin/env python3
"""Conditional V4.1 rate search from exact collective and index reader gates.

Every projected speedup is tied to a named missing RTL/physical gate.  The
current delivered scan and full-shape die have not achieved the modeled rate.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import arch_lanes_v41 as AL  # noqa: E402
import arch_budget_v41 as AB  # noqa: E402
import collective_exposure as CX  # noqa: E402
import decode_critical_path as DC  # noqa: E402
from v41_tp_exact_reprice import v41_moe_rowsplit  # noqa: E402
from v41_tp_rowsplit_measured_reprice import measured_gather_mutation  # noqa: E402

OUT = ROOT / "results/arch/v41_rate_optimization_search.json"


def critical_path(solution):
    built = solution["_built"]
    graph = built.g
    groups = {}
    for name in graph.path(built.sink):
        key = re.sub(r"^L\d+\.", "L*.", name)
        key = re.sub(r"^E\d+\.", "E*.", key)
        groups[key] = groups.get(key, 0.0) + sum(graph.contrib[name].values()) * 1e6
    return sorted((dict(node=k, cumulative_us=round(v, 3)) for k, v in groups.items()),
                  key=lambda x: -x["cumulative_us"])[:8]


def build():
    depth = json.loads((ROOT / "results/rtl/v41_collective_depth_campaign.json").read_text())
    mtp = json.loads((ROOT / "results/rtl/v41_tp_rowsplit_mtp_collectives.json").read_text())
    reader = json.loads((ROOT / "results/rtl/hdc_v41x_idx_shard_reader_pc.json").read_text())
    priced = json.loads((ROOT / "results/arch/v41_tp_rowsplit_measured_reprice.json").read_text())
    budget = json.loads((ROOT / "results/arch/arch_budget_v41.json").read_text())
    lanes = json.loads((ROOT / "results/arch/v41_lanes.json").read_text())
    for record in (depth, mtp, priced):
        for path, digest in record["source_sha256"].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    assert reader["schema"] == "opentallas.hdc-v41x-idx-shard-reader-pc.v1"
    assert reader["status"] == "pass_exact_below_bandwidth_target"
    assert depth["contract"]["selected_full_shape_CL_DEPTH"] == 128
    assert mtp["contract"]["m"] == 6 and mtp["contract"]["PAIRWISE"] == 1
    assert priced["measured_tail_cycles"] == {
        n: depth["summary"][n]["selected_tail_cycles"] for n in ("act", "y")}
    point = AL.design_point()
    hz = point["hz"][0]
    die_hbm_bytes_cycle = AB.ROM_DIE_HBM_BPS / hz
    effective_sectors_cycle = die_hbm_bytes_cycle / 32
    tagged_sectors_cycle = reader["timed_1040_key_scan"]["sectors_per_cycle"]
    base = {n: depth["summary"][n]["selected_tail_cycles"] for n in ("act", "y")}
    fused = {n: mtp["summary"][n]["fused_exposed_tail_cycles"] for n in ("act", "y")}
    serial = {n: mtp["summary"][n]["serial_six_exposed_tail_cycles"] for n in ("act", "y")}
    # The exact GW1 engine tails sit 156 cycles above their one-write-port
    # output floors for both gathers.  Holding this overhead constant when
    # widening output is an optimistic floor, not an implemented datapath.
    overhead = {n: base[n] - depth["summary"][n]["output_port_minimum_cycles"] for n in base}
    assert overhead == {"act": 156, "y": 156}

    def widened(gw, words):
        return {n: math.ceil(4 * words[n] / gw) + overhead[n] for n in ("act", "y")}

    ar_words = {n: depth["summary"][n]["input_words_per_die"] for n in ("act", "y")}
    mtp_words = {n: mtp["summary"][n]["fused_local_flits_per_die"] for n in ("act", "y")}
    cases = [
        dict(name="tagged_reader_negative_gate", index_sectors_cycle=tagged_sectors_cycle, gw=1,
             weight_factor=1.0, evidence="standalone exact tagged per-PC reader; not an integrated full-token rate",
             gate="integrate exact sharded reader with user offsets and token path; close timing and power"),
        dict(name="reader_32_sensitivity", index_sectors_cycle=32.0, gw=1, weight_factor=1.0,
             evidence="hypothetical four-stack aggregate", gate="four-stack exact timed scan at >=32 sectors/cycle"),
        dict(name="reader_60_sensitivity", index_sectors_cycle=60.0, gw=1, weight_factor=1.0,
             evidence="hypothetical four-stack aggregate", gate="four-stack exact timed scan at >=60 sectors/cycle"),
        dict(name="reader_at_effective_hbm_cap", index_sectors_cycle=effective_sectors_cycle, gw=1,
             weight_factor=1.0, evidence="existing design-point assumption, not delivered RTL",
             gate="four-stack exact full-token scan at effective 3.6 TB/s and P&R closure"),
        dict(name="reader_cap_plus_two_vm_writes", index_sectors_cycle=effective_sectors_cycle, gw=2,
             weight_factor=1.0, evidence="optimistic output-port floor plus measured GW1 fixed overhead",
             gate="two-bank VM/CDMA and GW2 engine exact stage/full-token benches and route"),
        dict(name="reader_cap_plus_four_vm_writes", index_sectors_cycle=effective_sectors_cycle, gw=4,
             weight_factor=1.0, evidence="optimistic output-port floor plus measured GW1 fixed overhead",
             gate="four-bank VM/CDMA and GW4 engine exact stage/full-token benches and route"),
        dict(name="four_vm_writes_plus_weight_125", index_sectors_cycle=effective_sectors_cycle, gw=4,
             weight_factor=1.25, evidence="analytical width sensitivity only; no additional weight RTL or physical closure",
             gate="25% wider weight/BF16 lanes with ROM delivery, exact token, hottest-die power and route"),
    ]
    lev = lanes["collective_exposure"]["levers"]
    common = point["muts"] + [point["ml"], CX.mutation(lev["terms"]),
                               CX.consumer_mutation(tuple(lev["consumers"]))]
    envelope = budget["compute_envelope_mm2"]
    cool = budget["power"]["cooling_limit_w_per_die_by_class"]["liquid"]
    old = DC.v41_moe
    DC.v41_moe = v41_moe_rowsplit
    try:
        rows = []
        for case in cases:
            gw = case["gw"]
            ar_tails = base if gw == 1 else widened(gw, ar_words)
            mtp_fused = fused if gw == 1 else widened(gw, mtp_words)
            mtp_serial = serial if gw == 1 else {n: 6 * ar_tails[n] for n in ("act", "y")}
            spec = replace(point["sp"], idx_bytes=case["index_sectors_cycle"] * 32)
            factor = case["weight_factor"]
            if factor != 1:
                spec = replace(spec, weight_macs=spec.weight_macs * factor,
                               bf16_macs=spec.bf16_macs * factor,
                               rom_bytes=spec.rom_bytes * factor)
            areas = {str(m): AL.U.area_of(spec, AL.A.unit_areas()[0], pooled=True, lm=m)["total"]
                     for m in (1, 2)}
            contexts = {}
            for ctx in (1_048_576, 200_000):
                with AL.LX.clock(point["hz"][0]), AL.U.params(**point["hz"][1]):
                    ar = AL.U.solve(spec, ctx, levers=AL.U.CHAIN_L3,
                                    muts=common + [measured_gather_mutation(ar_tails)])
                # Evaluate the six-position verification + draft period, using
                # each candidate's distinct collective descriptor schedule.
                f = AL.LX.evaluate(spec, ctx, common + [measured_gather_mutation(mtp_fused)],
                                   hz=point["hz"], draft_extra_s=point["draft_extra_s"])
                s = AL.LX.evaluate(spec, ctx, common + [measured_gather_mutation(mtp_serial)],
                                   hz=point["hz"], draft_extra_s=point["draft_extra_s"])
                contexts[str(ctx)] = dict(ar_tokens_s_per_user=ar["tokens_s_per_user"],
                                          ar_period_us=ar["period_s"] * 1e6,
                                          ar_binding=ar["binding"],
                                          ar_breakdown_us=ar["breakdown_us"],
                                          ar_critical_path_groups=critical_path(ar),
                                          mtp_fused_stage_sensitivity=f["mtp"],
                                          mtp_serial_stage_sensitivity=s["mtp"])
            rows.append(dict(**case, ar_tail_cycles=ar_tails,
                             mtp_fused_tail_cycles=mtp_fused,
                             mtp_serial_tail_cycles=mtp_serial,
                             analytical_compute_area_mm2=areas,
                             analytical_m2_fits_compute_envelope=areas["2"] <= envelope,
                             physical_status="not routed; banked VM area and added dynamic power unpriced",
                             contexts=contexts))
    finally:
        DC.v41_moe = old
    baseline = next(x for x in rows if x["name"] == "reader_at_effective_hbm_cap")
    for ctx in ("1048576", "200000"):
        actual = priced["points"][ctx]["ar"]["row_split_measured_gathers"]
        assert abs(baseline["contexts"][ctx]["ar_tokens_s_per_user"] - actual) < 1e-8
    sources = ("tools/v41_rate_optimization_search.py", "tools/v41_tp_rowsplit_measured_reprice.py",
               "tools/v41_tp_exact_reprice.py", "tools/arch_lanes_v41.py",
               "tools/arch_latency_ladder_v41.py", "tools/arch_utilization_v41.py",
               "tools/arch_budget_v41.py", "tools/decode_critical_path.py",
               "tools/collective_exposure.py", "results/arch/v41_lanes.json",
               "results/arch/arch_budget_v41.json",
               "results/arch/v41_tp_rowsplit_measured_reprice.json",
               "results/rtl/v41_collective_depth_campaign.json",
               "results/rtl/v41_tp_rowsplit_mtp_collectives.json",
               "results/rtl/hdc_v41x_idx_shard_reader_pc.json")
    pins = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in sources}
    return dict(schema="v41_rate_optimization_search_v1", source_sha256=pins,
                scope="conditional batch-one design sensitivity; no full-shape bit-exact rate or P&R claim",
                baseline_assumptions=dict(clock_hz=hz, hbm_effective_Bps=AB.ROM_DIE_HBM_BPS,
                                          hbm_effective_sectors_per_cycle=effective_sectors_cycle,
                                          reader_nominal_target_sectors_per_cycle=reader["target_sectors_per_cycle"],
                                          tagged_reader_sectors_per_cycle=tagged_sectors_cycle,
                                          liquid_cooling_limit_w_per_die=cool,
                                          analytical_compute_envelope_mm2=envelope,
                                          added_vm_bank_area_power="unpriced"),
                scenarios=rows,
                limits=["the tagged reader is a standalone exact prototype and does not drive the full die",
                        "four-stack exact scan delivery, user isolation and HBM timing remain open",
                        "the GW2/GW4 tails hold the measured 156-cycle GW1 fixed overhead and divide only output cycles; they are optimistic floors, not measurements",
                        "the four-bank VM/CDMA and widened weight pools have no routed area, power or exact-token verdict",
                        "MTP fused versus six-serial descriptor schedule is not yet emitted by the full-shape program"])


def main():
    rec = build()
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    for row in rec["scenarios"]:
        c = row["contexts"]["1048576"]
        print(row["name"], round(c["ar_tokens_s_per_user"]),
              round(c["mtp_fused_stage_sensitivity"]), round(c["mtp_serial_stage_sensitivity"]))


if __name__ == "__main__":
    main()
