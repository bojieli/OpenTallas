#!/usr/bin/env python3
"""Restore required normal compute in all five designated KV slice leaves.
The selected KV_ENABLE1 source retains the normal 16x5 leaf compute contract and
adds the native bank/pool only at leaf0. The old generator labelled all five as
KV-only and skipped their complete hard-core realization. This delta preserves
partition types/outer ports/FT windows and copies exact existing normal masters
from the closest same-face normal leaf. Native KV bank/pool views remain OPEN,
not represented by invented macros. Use on the final FT candidate, then repack
these five types and publish all resulting station-cycle deltas before adoption.
"""
import argparse, copy, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
import compact_plan
NR = "ot_sram_1r1w_512x128_m4_r0c0"
OLD = "ot_sram_1r1w_512x128_m4_r2c2"
NORMAL_CELLS = (36056 + 16*50540 + 460279 + 375145 + 117971 + 120703 + 46676 + 82916 + 99597)
KV_OLD_EST = 62014 + 94804 + 58177 + 84923 + 43505
# Actual CNIK1/CP1/HARD_RQ0 elaboration:56KVE,8KVP,16KVQ,4KVT; QNR/CN/pool
# are additional. This lower estimate already disproves the old single-leaf
# raw-glue budget. No native physical build is eligible before repartitioning.
KV_EXTRA_EST = 56*62014 + 8*94804 + 16*58177 + 4*43505

def apply(raw):
    T = raw["partition_types"]
    rows = []
    for i in range(1,6):
        tn = f"ot_s81sl_kv_leaf__t{i}"
        t = T[tn]
        if t.get("hard_cores"):
            raise ValueError(f"{tn}: existing hard cores; refusing to overwrite")
        candidates=[]
        for name,d in T.items():
            if not name.startswith("ot_s81sl_leaf__") or len(d.get("hard_cores",[])) != 27:
                continue
            if [b["face"] for b in d["buses"]] != [b["face"] for b in t["buses"]]:
                continue
            score=sum(abs(sum(a["window_um"])/2-sum(b["window_um"])/2) for a,b in zip(d["buses"],t["buses"]))
            candidates.append((score,name))
        score, donor = min(candidates)
        d = T[donor]
        if t["outline_um"] != d["outline_um"]:
            raise ValueError(f"{tn}: donor outline mismatch")
        t["hard_cores"] = copy.deepcopy(d["hard_cores"])
        t["internal_stations"] = copy.deepcopy(d.get("internal_stations",[]))
        vp = []
        for h in t["hard_cores"]:
            if h["module"] == OLD:
                h.update(module=NR, outline_um=[169.368,29.16],
                         lef=f"physical/asap7_memory_macros_v2/{NR}/{NR}.lef",
                         pins_file=f"inputs/core_pins/{NR}.json")
            if h["inst"] in ("u_lf.u_vp.u_b0","u_lf.u_vp.u_b1"):
                vp.append(h["inst"])
        if sorted(vp) != ["u_lf.u_vp.u_b0","u_lf.u_vp.u_b1"]:
            raise ValueError(f"{tn}: not the exact selected VP bank pair")
        t["contents"][0]["module"] = "ot_s81sl_leaf"
        t["contents"][0]["note"] += "; KV slice retains all normal compute (entry_norm 16x5 contract)"
        if i == 2: # s_3N_L0, the only KV_ENABLE leaf
            t["contents"].append(dict(inst="u_lf.g_kv.u_kv",module="ot_s81sl_kv_leaf",status="rework",
                note="ACTUAL KV_ENABLE1 CNIK1 CP1 HARD_RQ0 bank/pool child; native measured views/sizing OPEN. Not a replacement for normal compute."))
        t["note"] += f"; KV normal-compute realization from {donor}; exact masters, no RTL/cycle change; native KV-only extras OPEN"
        area = sum(h["outline_um"][0]*h["outline_um"][1] for h in t["hard_cores"])
        rows.append(dict(type=tn, donor=donor, own_window_center_distance_um=score,
                         hard_cores=len(t["hard_cores"]),vp_banks=len(vp),hard_core_area_um2=area,
                         internal_station_groups=len(t["internal_stations"])))
    report=dict(schema="opentallas.s81.kv_compute_realization.v1",scope="candidate, not adopted",
                basis="selected hybrid KV source + entry_norm 16x5 reader contract",rows=rows,
                normal_compute_cells_per_leaf_est=NORMAL_CELLS,normal_compute_leaves=5,
                native_KV_extra_cells_estimate=KV_EXTRA_EST,native_KV_extra_count=1,
                old_KV_only_estimate=5*KV_OLD_EST,
                corrected_lower_estimate=5*NORMAL_CELLS+KV_EXTRA_EST,
                native_KV_macro_instances=176,native_KV_macro_area_um2=506067.803136,
                native_KV_placement="BLOCKED: actual operator count exceeds old L0 slot budget; distribute/cut before build",
                arithmetic_operator_cycle_change=0,
                transport_cycle_change="PROPOSED internal stations/FT depths require actual RTL-CS + compiler adoption; not zero-cost",
                proposed_internal_station_groups=sum(r["internal_station_groups"] for r in rows),
                external_ports_changed=0,die_outline_changed=False,
                open=["native bank/pool measured footprint/views and production-count repartition", "FT repack + latency delta", "actual-source internal relay realization and current clock/PDN/signoff"])
    return report

def main():
    ap=argparse.ArgumentParser();ap.add_argument("plan");ap.add_argument("out");ap.add_argument("--report",required=True);a=ap.parse_args()
    raw=json.loads(Path(a.plan).read_text());report=apply(raw)
    Path(a.out).write_text(compact_plan.dumps(raw));Path(a.report).write_text(json.dumps(report,indent=1)+"\n")
    print(json.dumps(report,indent=1))
if __name__=="__main__":main()
