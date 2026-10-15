#!/usr/bin/env python3
"""S81 hierarchy contract v18 -> v19 (ONE revision for 2026-10-14 PM, die lead r6; one-shot, idempotent).

Folds the r6 decisions (el1011-s81die.log 2026-10-14 16:3x-17:xx) into results/arch/hier_contract_1011/s81.json:
  PQ return topology G, the published pin files / subslots of Engram hl, Markov K256, gather v4 and the NORM variant,
  the cfifo edge (station falling-edge launch), hcol/hsel bind, VM FE structure (a), the crootr_f slot change (measured R),
  the IR gate recipe (--pdn-field-cov 0.09) and the c9p chain recipe.  Geometry of every other slot is unchanged from v18.

Usage: contract_v19.py [--census C9P_CENSUS.json] [--check]
  --census: {master: instances} of the v19c die (c9p GEN plan); without it the v18 master list stands (census owed).
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "results/arch/hier_contract_1011/s81.json"
LOG = "el1011-s81die.log 2026-10-14 (s81-die lead r6)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--census")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    c = json.loads(CON.read_text())
    if c["version"] >= 19 and not a.census:
        print("already v%d" % c["version"]); return 0
    if c["version"] == 18:
        c["version"] = 19
        c["updated"] = "2026-10-14 PM PT (s81 die lead r6, Claude)"
        c["changelog"] = c.get("changelog", []) + [
            "v19 (2026-10-14 PM): PQ return topology G (frame pq_root row off the layer die; 12 count-only RWB slots in a "
            "43.2-um gather|capture seam); Engram hl / Markov K256 / gather v4 / NORM-variant pin files + subslots; cfifo "
            "falling-edge station launch; crootr_f target insertion = measured R; IR gate recipe --pdn-field-cov 0.09; recipe "
            "s81_layer1_v19c (c9p)."]
        R = {"sp_hc_s/crootr_c0/f": (711.2, "crrfw"), "sp_hc_s/crootr_c2/f": (862.2, "crrfe")}
        for s in c["slots"]:
            if s.get("name") in R:
                r_, kit = R[s["name"]]
                s["target_insertion_ps"] = r_
                s["clock_tap"] = ("earlier trunk tap (R > 300 ps), hops SKEW 150 ps (die clock delivery rule, owner 10-13 09:25); "
                                  f"measured TT boundary mean of kit {kit}, leaf spread <= 33.2 ps, 11,430 sinks")
                s["version"] = 19
            if s.get("cell") in ("dsfd_pq_root", "dsfd_rstg_pq66", "dsfd_rstg_pq68"):
                s["v19_state"] = "REMOVED from the layer die by PQ topology G (--pq-g); slot kept for the record only"
        c["v19_decisions"] = {
            "pq_topology": {"decision": "G: the gather root leaves are THE roots; frame pq_root / rstg_pq66 / rstg_pq68 off the "
                                        "layer die; column return = raw tree words (cfifo ri 68)",
                            "closed_views_not_bound": ["ot_s81_pq_rwb11_native (s81pq_rwb11_native-g1-71a9de5c6)",
                                                       "ot_s81_pq_rwb10_native (s81pq_rwb10_native-g1-71a9de5c6)"],
                            "count_slots": "physical/s81_die_pins/v19/pq_count_slots.json (12 x 142.56 x 38.88 in the gather|capture "
                                           "seam widened 21.6 -> 43.2 um; x-tiling 15/2/15)",
                            "owed": ["PQ owner: count-only RTL ot_s81_pq_rwbc<N> + bench + mutant",
                                     "PQ owner + S-FUNC: gather root capacity (S = 8 open rows) vs the PQ phase programs",
                                     "die: exact count-leaf pins by --rtl-bind once the RTL exists; seam 43.2 in GEN"],
                            "generator": "--pq-g (claude/el1011-s81dieit 1d1428aa4)"},
            "pin_files": {
                "engram_hl": "physical/s81_die_pins/v19_engram_hl/ (rr256 seam, NEW rr256w, rr64 with leaf-local reset, ctl split "
                             "ot_engc_ctl_x + ot_engc_ctl_s + one closed dsfd_rly_1_EW on the ACK; worst hop 474.5 um)",
                "markov_k256": "physical/s81_die_pins/v19_markov/ (13 closed leaves adopted; cluster 453.6 x 436.32 ring layout, "
                               "worst hop 429.6 um; HEAD die slot S of the mtp sequencer)",
                "gather_v4": "physical/s81_die_pins/v19/ (slot v18 data pins + ck_q[47:0]; leaves li at the closed 276 relay "
                             "o pattern from leaf y + 40.32, co at the mean t_capture pattern; closed relays / strip / ctl adopted)",
                "norm_tree_variant": "physical/s81_die_pins/v19_ntree/ (default-off; serial NORM stays bound)"},
            "cfifo_edge": {"decision": "(i) station launches xd on the FALLING xf edge (fn0 non-inverted clock copy), the closed "
                                       "colck cfifo keeps its rising capture: half-cycle source-synchronous hop",
                           "generator": "--cfifo-fall-launch", "owed": "grpA: colck view recipe-2 pin-register re-route for 252 xb "
                                                                       "launch pins (263.3 > 220)"},
            "hcol_hsel": "CLOSED -wall-3e33b86ec-g4 views bind; 14 o pins 220.1-239.6 ps launch accepted while their hop L <= 333 "
                         "um (o + 0.76 L + s <= 683.3); re-route only if the classified table names a hop",
            "vm_fe": "(a) capture-slice locality (no 4 x 4 crossbar); gate: slice write-port balance measured in tb_dsfd_sp_vm at "
                     "production shape before any parent spec; fallback (b) corner turn",
            "ir_gate": "combined per-instance loss (tools/s81/ir_combined.py) <= 35 mV: field 27.13 / spine 18.28 mV at "
                       "--pdn-field-cov 0.09 + measured BF power (irv19_c090, EPYC4)",
            "hc_widths": "hc_s <-> hc_t at the RTL widths 3,056 / 2,164 per column (15,660 b): cut 0.24 of M5+M7 over the 1,816.5-um "
                         "slab width; reach needs --hop-spread",
            "recipe": "results/physical/die_iter_1012/s81/s81_layer1_v19c.opts (c9p)",
            "source": LOG}
    if a.census:
        cen = json.loads(Path(a.census).read_text())
        c["master_list_v19"] = {"source": a.census, "masters": len(cen), "instances": sum(cen.values()),
                                "rows": [{"master": m, "instances": n} for m, n in sorted(cen.items(), key=lambda kv: -kv[1])]}
    if a.check:
        print(c["version"], sorted(c.get("v19_decisions", {}))); return 0
    CON.write_text(json.dumps(c, indent=1) + "\n")
    print("wrote v%d" % c["version"], CON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
