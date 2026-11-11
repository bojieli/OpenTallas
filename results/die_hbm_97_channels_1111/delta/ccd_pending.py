"""hbm-channels-1111: record the event's lane cycle changes as pending in the plan dir compiler_core_delta.json"""
import json, sys, hashlib
D = sys.argv[1]; p = D + "/compiler_core_delta.json"; c = json.load(open(p))
c["pending_not_folded"]["hbm-channels-cycles-1111"] = (
    "die lane cycle event (not EQ-by-construction; DIE-HBM-98 11-11). latency.lanes: "
    "L5090 48->50 and L5091 47->48 (link class: native internal-station data lanes, NE_su01 q_su01__physical_v1 .L5090_o/.L5091_o "
    "-> NE_hub q_hub_ne .L5090_i/.L5091_i, 21 b / 41 b; lane fixed_cycles 3->5 / 3->4 = SU-CHAN internal source stations); "
    "L8301m, L8302, L8302m, L8314, L8314m +1 each (link class: hub->SM data lanes through the q_su11/q_su11__physical_v1 ft "
    "slots, q_hub_ne/q_hub_nw .L30_o/.L31_o/.L98_o -> q_sm1 .L30_i/.L31_i/.L98_i, 1615 b / 1615 b / 22 b; one more ft "
    "station per slot by the generator rule). latency_groups: no entry names these lanes (unchanged). "
    "Compiler estimate (price_chan_cyc.json, S2): SM+1 -0.032%, SU+2 upper bound -0.313%, both -0.344%. "
    "HBM-TAPS price on hbm_price_d44t (RESULT hbm-channels-cycles): L5090/L5091 carry NE_su01 bank_read_data to NE_hub; "
    "the slowest SU->hub leg is L1271 at 66 (NE L5094 at 64), so under the max-leg rule the expected delta is +0 "
    "(1648.00 tok/s unchanged), bound 1642.88 tok/s (-0.311%, matches the SU+2 estimate); hub->SM +1 lanes expected +0. "
    "The affected types count only after the "
    "scheduler/token check on the new cycles passes. Stage-equivalence proof for the extra stations: MISSING.")
json.dump(c, open(p, "w"), indent=1)
print(hashlib.sha256(open(p, "rb").read()).hexdigest())
