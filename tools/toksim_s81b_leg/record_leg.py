#!/usr/bin/env python3
"""TOKSIM-S81B/LEG (10-19): element record elements/LEG.json from the tb_leg_s81 reduction (parse_leg.py) + slot records
for every priced on-die leg term of the committed composition (results/arch/token_path_1018/ds_rom.json, xdie terms,
grade 'priced', part 'on-die leg farthest slice <-> end slice, both ends (p4l plan, 67 cyc an end)').
usage: record_leg.py <leg.json> <token_path_1018 ds_rom.json> <out LEG.json> <branch@commit> <written>"""
import json, sys
from collections import Counter

lj, dj, oj, br, written = sys.argv[1:6]
R = json.load(open(lj)); D = json.load(open(dj))
assert R["PASS"], "bench/law not PASS"
far = {}
for w in R["windows"]:
    if w["links"] == 7 and w["name"] == "stage_hop":
        far[(w["tier"], w["flow"])] = w["cycles"]
# circuits (tb_xdie_s81_2 pair A): d.ES <-> (d+1).WS (S tier), d.EN <-> (d+2).WN (N tier); each crossing = the sender's
# farthest slice -> its end slice (OUT) + the receiver's end slice -> its farthest slice (IN)
circ = {
    "S: E-end out + W-end in (d.ES -> (d+1).WS)": far[("S", 1)] + far[("S", 2)],
    "S: W-end out + E-end in ((d+1).WS -> d.ES)": far[("S", 0)] + far[("S", 3)],
    "N: E-end out + W-end in (d.EN -> (d+2).WN)": far[("N", 1)] + far[("N", 2)],
    "N: W-end out + E-end in ((d+2).WN -> d.EN)": far[("N", 0)] + far[("N", 3)],
}
worst = max(circ.values()); best = min(circ.values())
per_end = {f"{t} {['out_W','out_E','in_E','in_W'][f]}": c for (t, f), c in sorted(far.items())}
sweep = {}
for w in R["windows"]:
    if w["name"].startswith("sweep_"):
        sweep[f"{w['tier']} flow{w['flow']} {w['src_col']}->{w['dst_col']}"] = w["cycles"]
terms_by_size = {w["name"]: w["cycles"] for w in R["windows"] if w["tier"] == "S" and w["flow"] == 0 and not w["name"].startswith("sweep")}
ops = []
slots = {}
for wl in ("ar", "mtp"):
    S = []
    for e in D["workloads"][wl]["terms"]:
        if e.get("kind") == "xdie" and e["grade"] == "priced" and "on-die leg" in e.get("part", ""):
            ncross = round(e["E"] / 134.0) if e["E"] else 0
            S.append(dict(slot=e["slot"], n=e["n"], old_E=e["E"], old_exposed=e["cycles"], crossings_x_n=ncross,
                          new_E=ncross * worst, new_exposed=(e["cycles"] / 134.0) * worst if e["cycles"] else 0.0,
                          critical=e["cycles"] > 0))
    slots[wl] = S
    old = sum(s["old_exposed"] for s in S); new = sum(s["new_exposed"] for s in S)
    ops.append({
        "op": f"xdie.on_die_leg.{wl}", "dag_cls": "hop", "n_crit": sum(1 for s in S if s["critical"]),
        "old_cycles_per_instance": 134.0,
        "cycles": float(worst),
        "by_old": {"134.0": float(worst), "268.0": float(2 * worst), "8308.0": round(8308.0 / 134.0 * worst, 1), "0.0": 0.0},
        "grade": "measured-release-RTL",
        "definition": ("per cross-die crossing, both ends: OUT = edge the farthest source slice's ring stop samples its "
                       "control-plane line inject (ci_b) -> edge the end slice ring stop samples the beat on its inward ri "
                       "(= tb_xdie_s81_2 issue edge); IN = edge the receiving end slice ring stop loads its inward ro "
                       "(= tb_xdie_s81_2 landing edge) -> edge the farthest owning slice ring stop loads dl_e/dl_w (consumer "
                       "register). Value = worst circuit (S tier W-bound both ends); every beat of every window has the same "
                       "latency (1 beat/cycle sustained, no wait), so the leg adds latency only, independent of payload."),
        "shape": ("7 ring links each end (farthest slice, as the price): per link 4 x 276-b lanes, ICG hop 0 + 7 x "
                  "dsfd_dvrlyh_276 half-cycle relays + dsfd_dvland_276 (k 4/5 from die.v) + the entered ot_s81sl_rstop; "
                  "production payload per term (1..321 beats of 128 B, xdie beats_per_peer) + column sweep 1..7 links, "
                  "both tiers, all 4 flows; 6,320 beats"),
        "bit_exact": True,
        "golden": "full 1,104-b beat compare at the end-stop pin / owning-stop dl register (payload SHA-256 stream, hops as compiled), in order per flow",
        "rtl": {"module": "ot_s81sl_rstop + dsfd_dvrlyh_276_{WE,EW} (ot_dvrly_st HC 1 / ot_s81_rly RSREG 1) + dsfd_dvland_276 (ot_s81_land D 4); chain from die.v",
                "source": "origin/claude/s81-bind-mu4-1019@19bf4121e (die.v = ot-epyc7 s81-bind-mu4c/bind_main/bind/die.v)",
                "blob": "rstop d089448887d5, ot_s81_rly dd70cc2dc04a, dsfd_rly_masters_dv276 72c17619b1b5, dsfd_rly_masters_dvh 0567b4082944, ot_s81_land 29d5d8f807c1, dsfd_dvland 3f4a565f9307",
                "in_release_source": True},
        "bench": f"rtl/test/toksim_s81b_leg/tb_leg_s81.sv + leg_chain_gen.sv (tools/toksim_s81b_leg/gen_chain.py from die.v) @{br}",
        "evidence": "results/rtl/toksim_s81b_leg_1019/l1/run.log.gz ('PASS leg_s81: 6320 beats'), leg.json (law_violations 0)",
        "job": "ot-run ot-epyc8 oth-ubuntu-410900-1792462807 (out_l1), Verilator 5.050",
        "edges_owed": ("NOT folded (not in the release mu4c): LEAD2-S81 INBOX [SLICE 16:39] ot_s81sl_xg successor rstop RELAY=1 (claude/s81-xgr-1019@5e5845264) = +1 edge on ro_e/ro_w/dl_* per stop -> +7 an end, +14 a crossing (worst 154) if bound; [SMWIRE] rstop V-train re-kit touches the V rung only (+0 here). The 8 lk lane legs (3 dvrlyh + dvland k3) are inside tb_xdie_s81_2 (measured there, job u2 owned by the parent), not here"),
        "circuits": circ, "per_end_farthest": per_end, "best_circuit": best,
        "old_total_exposed": round(old, 1), "new_total_exposed": round(new, 1), "delta_cycles": round(new - old, 1),
        "slots": S,
        "note": (f"replaces ONDIE 134 = 2 x 67 (record.py: 29 stations 14.5 + 7 landed links 38.5 + 7 stops x 2 = 67 an end). "
                 f"Measured: {per_end} an end at 7 links; per crossing {best}..{worst}. The die's ring links each have 7 relay "
                 f"stations (49 per 7 links, not 29), law per link + entered stop = k + 5 edges. Off-critical slots (exposed 0) "
                 f"stay 0. The unplaced_hops slot (62 hops x 134 = 8,308) scales x {worst}/134. Cross-tier (V rung) owners are "
                 f"not on the priced path and not measured here."),
    })
rec = {"cls": "LEG", "written": written, "agent_branch": br, "ops": ops,
       "sweep_cycles": sweep, "terms_far_S_outW": terms_by_size}
json.dump(rec, open(oj, "w"), indent=1)
for o in ops:
    print(o["op"], "worst", o["cycles"], "best", best, "old", o["old_total_exposed"], "new", o["new_total_exposed"], "delta", o["delta_cycles"])
