"""KV-PLAN-DELTA-3 hm_r26q5 part (b) D-KV-AHUB-ZH-TAP (COORD 12:01 ASK-2 ruling: NUMBER-CHECK, then a plan-computed
early tap per 12.8 MSCTS v5.0, not a hand clock tweak).
NUMBER-CHECK (zh/sta.tcl + zh/sta2.tcl, OpenSTA NLDM ASAP7 RVT TT/FF + macro .lib, Elmore pi SPEF from the kit
setRC_rcx.tcl clock RC): delivering the zh clk pins from the q4 centre entry (302.4,241.92) costs 138.7-147.8 ps TT /
120.2-127.8 FF (best of 1-4 x BUFx12f/16f/24 on clock-class RC; M7 RC bound 98.9-105.2 TT / 86.2-91.5 FF), so zh arrive
TT 345..394 (+95..+144 vs 250), FF +86..+128 vs 202.5.  q4 (0.20 ps/um, UNCHECKED) said +51..55 -> CONFIRMED late and
the model was ~2.5x optimistic.  Structural fix (v5.0 early-tap form, early_core_taps.py placement rule: a dedicated
drop beside the actual transformed macro clock pin): the zh pairs face each other across the 21.6-um channel
x 177.12..198.72 at y 71.94 (S pair zh0/zh1) and y 411.9 (N pair zh2/zh3) -> one in-core pushdown island (12.2a1) per pair
on the 4.32 lattice in that channel, a new core clock pin on it (ck[1] S, ck[2] N, M5 like ck[0]), and a kv3_hub_C
partition-tree leaf tap per pin.  Pin -> zh pin delay (die buffer BUFx12f in the island, both stubs): TT 4.5/6.4 ps,
FF 4.5/6.3 ps (sta2) -> tap insertion = zh signed mean + worst stub = TT 252.7 / FF 209.0: within the 250 +-20 band,
early offset vs the common 250 = 2.7 ps (no spine shift needed).  recip (-10.7 q4 model) stays on ck[0].
Also fixes a q4 defect: kv3_hub_C tap ahub.ck[0] xy kept the OLD entry y (1045.44+220.32) after q4 moved the pin to 241.92.
RTL obligation (KV-KITS-7 / KV-CORES): qkd_ahub ck [0:0] -> [2:0]; g_zh[0..1].u_zh.clk <- ck[1], g_zh[2..3] <- ck[2].
    q5_ahub.py PD_IN(q4 pd) PLAN_IN PLAN_OUT"""
import json, sys, copy
pd, pin_, pout = sys.argv[1:4]
L, ISL, KO = 4.32, 8.64, 1.08
P = json.load(open(pin_)); q4 = copy.deepcopy(P)
S = json.load(open(f"{pd}/cores/qkd_ahub_slice_r26q4.json")); sl = S["slice"]
boxes = [tuple(b) for b in sl["hard_children_boxes_um"]]
def rect(c): return [round(c[0] - ISL / 2, 4), round(c[1] - ISL / 2, 4), round(c[0] + ISL / 2, 4), round(c[1] + ISL / 2, 4)]
def clear(r): return all(r[2] <= x0 - KO or r[0] >= x1 + KO or r[3] <= y0 - KO or r[1] >= y1 + KO for x0, y0, x1, y1 in boxes)
sinks = {s["inst"]: s for s in sl["macro_sinks"]["sinks"]}
PAIRS = {"ck[1]": ("g_zh[0].u_zh", "g_zh[1].u_zh"), "ck[2]": ("g_zh[2].u_zh", "g_zh[3].u_zh")}
STUB = {"ck[1]": dict(tt=6.42, ff=6.29), "ck[2]": dict(tt=6.42, ff=6.29)}   # sta2: BUFx12f pair, worst stub (14.5 um), Y->clk
M5_OFF, M5_PITCH = 0.024, 0.048
entries = []
others = [tuple(i["centre_um"]) for i in sl["core_tree"]["islands"]] + [tuple(sl["entry"]["xy_um"])]
for pin, (a, b) in PAIRS.items():
    pa, pb = sinks[a]["pin_um"], sinks[b]["pin_um"]
    assert abs(pa[1] - pb[1]) < 1e-6, (pa, pb)
    cx = round(round(((pa[0] + pb[0]) / 2) / L) * L, 4); cy = round(round(pa[1] / L) * L, 4)
    r = rect((cx, cy)); assert clear(r), (pin, r)
    assert all(max(abs(cx - o[0]), abs(cy - o[1])) >= ISL - 1e-9 for o in others), (pin, cx, cy)
    others.append((cx, cy))
    px = round(M5_OFF + round((cx - M5_OFF) / M5_PITCH - 0.5) * M5_PITCH, 4)   # M5 track just left of centre (ck[0] form)
    assert r[0] < px < r[2]
    ins = {k: round(max(sinks[m]["insertion_ps"][k] for m in (a, b)) + STUB[pin][k], 1) for k in ("tt", "ff")}
    entries.append(dict(pin=pin, island_um=r, xy_um=[cx, cy], pin_xy_um=[px, cy], layer="M5", via_stack=sl["entry"]["via_stack"],
                        sinks=[a, b], stub_um={m: round(abs(sinks[m]["pin_um"][0] - px) + abs(sinks[m]["pin_um"][1] - cy), 3) for m in (a, b)},
                        insertion_ps=ins, form="v5.0 dedicated macro drop (early_core_taps rule) on a 12.2a1 in-core island"))
sl["macro_entries"] = entries
sl["macro_sinks"]["form"] = ("REJECTED for zh (q5 NUMBER-CHECK): centre-entry delivery = 138.7-147.8 TT / 120.2-127.8 FF ps (sta.tcl), "
                             "zh +95..+144 TT late; zh now fed by macro_entries ck[1]/ck[2]; recip stays on ck[0]")
for s in sl["macro_sinks"]["sinks"]:
    if s["master"] == "ot_nhb_zh":
        s["fed_by"] = next(e["pin"] for e in entries if s["inst"] in e["sinks"])
S["q5_delta"] = dict(macro_entries=[e["pin"] for e in entries], number_check="results/kv_plan_q5_1027/zh/README.txt")
open(f"{pd}/cores/qkd_ahub_slice_r26q5.json", "w").write(json.dumps(S, indent=1) + "\n")
d = json.load(open(f"{pd}/cores/qkd_ahub_pins_r26q4.json"))
assert not any(p["name"] in PAIRS for p in d["pins"])
for e in entries:
    d["pins"].append(dict(name=e["pin"], layer="M5", x=e["pin_xy_um"][0], y=e["pin_xy_um"][1]))
d["source"] += " | KV-PLAN-DELTA-3 hm_r26q5 10-27 D-KV-AHUB-ZH-TAP: + ck[1] (zh S pair) / ck[2] (zh N pair) on in-core macro-drop islands"
open(f"{pd}/cores/qkd_ahub_pins_r26q5.json", "w").write(json.dumps(d, indent=1) + "\n")
n = 0
for tn, t in P["partition_types"].items():
    for hc in t.get("hard_cores", []):
        if hc.get("pins_file") == "cores/qkd_ahub_pins_r26q4.json":
            hc["pins_file"] = "cores/qkd_ahub_pins_r26q5.json"; n += 1; host, H = tn, hc
assert n == 1 and host == "kv3_hub_C" and H.get("orient", "R0") == "R0"
ox, oy = H["origin_um"]
taps = P["partition_types"][host]["clock"]["taps"]
t0 = next(t for t in taps if t["name"] == "ahub.ck[0]")
p0 = next(p for p in d["pins"] if p["name"] == "ck[0]")
old = list(t0["xy"]); t0["xy"] = [round(ox + p0["x"], 4), round(oy + p0["y"], 4)]
t0["note"] += " | hm_r26q5: xy follows the q4 entry move (was the q3 y 1265.76)"
for e in entries:
    taps.append(dict(name=f"ahub.{e['pin']}", kind="core", xy=[round(ox + e["pin_xy_um"][0], 4), round(oy + e["pin_xy_um"][1], 4)],
                     insertion_ps=e["insertion_ps"]["tt"], insertion_ff_ps=e["insertion_ps"]["ff"], budget_owner="qkd_ahub",
                     note=f"KV-PLAN-DELTA-3 D-KV-AHUB-ZH-TAP: partition tree leaf = dedicated macro drop for {'+'.join(e['sinks'])} "
                          f"(signed zh mean + STA stub; early vs 250 = {round(e['insertion_ps']['tt'] - 250, 1)} TT)"))
# nothing else changes
for k in P:
    if k != "partition_types": assert P[k] == q4[k], k
for tn in P["partition_types"]:
    if tn != host: assert P["partition_types"][tn] == q4["partition_types"][tn], tn
P["note"] = P.get("note", "") + " | hm_r26q5 (KV-PLAN-DELTA-3 10-27): D-KV-AHUB-ZH-TAP qkd_ahub ck[1]/ck[2] zh macro drops + hub_C ck[0] tap xy fix"
open(pout, "w").write(json.dumps(P, indent=1) + "\n")
print("ck[0] tap", old, "->", t0["xy"])
for e in entries: print(e["pin"], e["xy_um"], e["pin_xy_um"], e["stub_um"], e["insertion_ps"])
