#!/usr/bin/env python3
"""DIE-KV-39-SD-V2 KV-022 variant V2 (COORD ruling DIE-KV-38-PARK (3)): fix-only plan delta for kv3_sys_SD /
kv3_sys_SD_v1 clock entries, local to the two types (no other type/die change, no new check kind).

Cause (CHECKED, DIE-KV-38 varA/varC + this lane's 3_place sink dump): the types' tap_edge_y_um grid puts 5 taps at
S-rim x 190/570/950/1330/1710 (C/A moved them to 190/1331/1520/1711/1860), but 98% of the 6.6k 'clk' sinks sit in the
SE corner (S strip x 1400-1900, E strip y 50-700) under/around the x6 PHY macro (17.28,54 1848.96x972), and ~110 S-rim
reset relays rrl_/srl_ span x 0-1400: independent per-tap trees then differ by 213 vs 626 ps on that chain.
Also the plan has no PHY footprint (contents.serdes without lef/origin/outline), so 11/12 reset.local_taps_um sit on
the macro (Codex 18:47 review).

Delta (per type):
 1. (prerequisite, existing main delta) apply_serdes_phys.py + serdes_phys_delta.json: contents serdes gets the x6 PHY
    physical footprint so tap_clear / reset_tree / placed_macro_boxes see the macro (asserted here).
 2. clock: tap_mode explicit, 6 taps from the actual placed 'clk' sink inventory (sink_bins_file = this lane's
    3_place dump of the kit, clk net only): 'clk' at the mid-S-rim reset/START entry (rst_in/run_in/collector root
    x 1108) + 5 load taps in the SE corner; tap_max_sinks 2400, tap_radius_um 400; tap_edge_y_um dropped.  Per-tap trees balance to the
    12.3 common latency by the existing tap_balance (OT_TAP_TARGET_PS 250 TT -> 202.5 FF), no new mechanism.
 3. reset.local_taps_um: the 12 local reset consumer sites re-sited off the macro onto the actual async-reset
    consumer groups (S x 1150-1850, E y 150-820) (count unchanged, so the reset_local_<k> port set is unchanged).
usage: mk_sd39.py TOOLS PLAN_IN(.json[.gz]) PLAN_OUT BINS_SD BINS_SD_V1 BINS_REL_SD BINS_REL_SD_V1"""
import json, sys, gzip
TYPES = ("kv3_sys_SD", "kv3_sys_SD_v1")
TAPS = [("clk", 1110.0, 21.6), ("clk_t1", 1490.0, 21.6), ("clk_t2", 1690.0, 21.6), ("clk_t3", 1855.0, 21.6),
        ("clk_t4", 1892.16, 160.0), ("clk_t5", 1892.16, 640.0)]
# SD_v1 (sys_SE, MY) carries 2.1k sinks at S x 1800-1900: t2/t3 shift east to balance the t3 load
TAPS_V1 = [TAPS[0], TAPS[1], ("clk_t2", 1730.0, 21.6), ("clk_t3", 1872.0, 21.6), TAPS[4], TAPS[5]]
LOCAL = [[1150.0, 30.24], [1300.0, 30.24], [1450.0, 30.24], [1550.0, 30.24], [1650.0, 30.24], [1750.0, 30.24],
         [1850.0, 30.24], [1892.16, 120.0], [1892.16, 250.0], [1892.16, 400.0], [1892.16, 560.0], [1892.16, 820.0]]


def main(a):
    tools, pin, pout = a[1], a[2], a[3]
    bins = {"kv3_sys_SD": a[6], "kv3_sys_SD_v1": a[7]}
    op = gzip.open if pin.endswith(".gz") else open
    raw = json.load(op(pin, "rt"))
    rec = {}
    for tn in TYPES:
        t = raw["partition_types"][tn]
        (c,) = t["contents"]
        # the x6 PHY footprint comes from main's serdes delta (results/die_kv_32_1029/serdes/apply_serdes_phys.py),
        # applied BEFORE this delta; fail closed without it (reset/tap legality then ignores the macro)
        assert c.get("lef") and c.get("origin_um") and c.get("outline_um"), (tn, "apply_serdes_phys first")
        ck = t["clock"]
        ck.pop("tap_edge_y_um", None)
        ck.update(tap_mode="explicit", taps=[{"name": n, "xy": [x, y]} for n, x, y in (TAPS_V1 if tn.endswith("_v1") else TAPS)],
                  tap_max_sinks=2400, tap_radius_um=400.0, sink_bins_file=bins[tn])
        old = t["reset"].get("local_taps_um")
        t["reset"]["local_taps_um"] = [list(p) for p in LOCAL]
        rec[tn] = dict(old_local_taps=old, new_local_taps=LOCAL, taps=TAPS_V1 if tn.endswith("_v1") else TAPS)
    raw["note"] = raw.get("note", "") + " | DIE-KV-39 V2 sd39: kv3_sys_SD/_v1 explicit 6 clock taps + PHY footprint + local reset sites"
    json.dump(raw, open(pout, "w"), indent=1)
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main(sys.argv)
