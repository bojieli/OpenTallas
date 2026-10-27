"""CLOCK-KV hm_r26q4 part (e) D-KV-AHUB-ENTRY (KV-KITS-7 ASK 11:32, COORD scope add): qkd_ahub clock entry + core_tree
islands clear of the 5 FIRM hard children.
  entry: 12.8a centre x kept (302.4), y moved into the free H channel y 220.32..263.52 -> centre (302.4, 241.92) on the
         4.32 lattice; ck[0]/rst_n[0] pins y 220.32 -> 241.92 (x/layer unchanged) -> cores/qkd_ahub_pins_r26q4.json
  core_tree: every island whose 8.64 rect touches a macro box (+1.08 keep-off) moves to the nearest free 4.32-lattice
         centre (Manhattan), no two islands on one site; the others unchanged
  macro sinks: the 5 macro clk pins (LEF pin x orient) with their signed TT/FF insertion (insertion.json 'all' mean);
         planned direct stub from the entry at 0.20 ps/um (the slice trunk model, UNCHECKED) -> arrival vs 250/202.5
    q4_ahub.py PD SLICE_IN SLICE_OUT"""
import json, sys
pd, sin, sout = sys.argv[1:4]
L, ISL, KO = 4.32, 8.64, 1.08
S = json.load(open(sin))
sl = S["slice"]
W, H = sl["outline_um"]
hc = json.load(open("/srv/opentallas-scratch2/claude/wt/kv-plan-q3-1027/physical/die_plan/qwen_kvsys/cores/harden/qkd_ahub_hard_children.json"))
SZ = {"ot_nhb_zh": 151.2, "ot_qkh_recip_leaf": 216.0}
PIN = {"ot_nhb_zh": (0.042, 148.38), "ot_qkh_recip_leaf": (0.042, 113.916)}           # LEF clk RECT centres (W face)
INS = {"ot_nhb_zh": dict(tt=246.3, ff=202.7), "ot_qkh_recip_leaf": dict(tt=224.3, ff=181.6)}  # insertion.json all.mean
boxes, sinks = [], []
for b in hc["blocks"]:
    s = SZ[b["master"]]; x, y = b["x"], b["y"]
    boxes.append((x, y, x + s, y + s))
    px, py = PIN[b["master"]]
    o = b["orient"]
    lx = s - px if o in ("MY", "R180") else px
    ly = s - py if o in ("MX", "R180") else py
    sinks.append(dict(inst=b["inst"], master=b["master"], orient=o, pin_um=[round(x + lx, 3), round(y + ly, 3)],
                      insertion_ps=INS[b["master"]]))
def clear(r):
    return all(r[2] <= x0 - KO or r[0] >= x1 + KO or r[3] <= y0 - KO or r[1] >= y1 + KO for x0, y0, x1, y1 in boxes) \
        and r[0] >= 0 and r[1] >= 0 and r[2] <= W and r[3] <= H
def rect(c):
    return [round(c[0] - ISL / 2, 4), round(c[1] - ISL / 2, 4), round(c[0] + ISL / 2, 4), round(c[1] + ISL / 2, 4)]
ent = [302.4, 241.92]
assert clear(rect(ent)) and abs(ent[1] / L - round(ent[1] / L)) < 1e-9
old_entry = dict(sl["entry"])
sl["entry"]["xy_um"] = ent
sl["entry"]["island_um"] = rect(ent)
for p in sl["entry"]["pins"]:
    p["to"][2] = 241.92
sl["entry"]["rule"] += " | hm_r26q4 D-KV-AHUB-ENTRY: y moved into the free H channel 220.32..263.52 (x centre kept); hard children FIRM"
cands = [(i * L, j * L) for i in range(1, int(W / L)) for j in range(1, int(H / L)) if clear(rect((i * L, j * L)))]
used = {tuple(isl["centre_um"]) for isl in sl["core_tree"]["islands"] if clear(isl["rect_um"])}
used.add(tuple(ent))
moves = []
for k, isl in enumerate(sl["core_tree"]["islands"]):
    if clear(isl["rect_um"]):
        continue
    c0 = isl["centre_um"]
    c = min((c for c in cands if all(max(abs(c[0] - u[0]), abs(c[1] - u[1])) >= ISL - 1e-9 for u in used)), key=lambda c: (abs(c[0] - c0[0]) + abs(c[1] - c0[1]), c))
    used.add(c)
    moves.append(dict(island=k, old=c0, new=[round(c[0], 4), round(c[1], 4)], move_um=round(abs(c[0] - c0[0]) + abs(c[1] - c0[1]), 2)))
    isl["centre_um"] = [round(c[0], 4), round(c[1], 4)]; isl["rect_um"] = rect(c)
assert all(clear(i["rect_um"]) for i in sl["core_tree"]["islands"])
cs = [tuple(i["centre_um"]) for i in sl["core_tree"]["islands"]] + [tuple(ent)]
assert all(max(abs(a[0] - b[0]), abs(a[1] - b[1])) >= ISL - 1e-9 for k, a in enumerate(cs) for b in cs[k + 1:]), "overlap"
A = 0.20
for s in sinks:
    d = abs(s["pin_um"][0] - ent[0]) + abs(s["pin_um"][1] - ent[1])
    s["stub_um"] = round(d, 2)
    s["arrival_TT_ps"] = round(A * d + s["insertion_ps"]["tt"], 1)
    s["arrival_FF_ps"] = round(A * d * 0.8118 + s["insertion_ps"]["ff"], 1)
    s["vs_target_TT_ps"] = round(s["arrival_TT_ps"] - 250.0, 1)
    s["vs_target_FF_ps"] = round(s["arrival_FF_ps"] - 202.5, 1)
sl["macro_sinks"] = dict(form="hard-child clk pins = sinks fed by direct stubs from the entry (v5.0 early-tap form); "
                         "arrival = 0.20 ps/um x Manhattan + signed insertion (MODEL UNCHECKED)", sinks=sinks)
sl["hard_children_boxes_um"] = [list(b) for b in boxes]
S["q4_delta"] = dict(entry_old=old_entry["xy_um"], entry_new=ent, island_moves=moves)
json.dump(S, open(sout, "w"), indent=1)
# pin view
d = json.load(open(f"{pd}/cores/qkd_ahub_pins.json"))
n = 0
for p in d["pins"]:
    if p["name"] in ("ck[0]", "rst_n[0]"):
        assert abs(p["y"] - 220.32) < 1e-9, p
        p["y"] = 241.92; n += 1
assert n == 2
d["source"] += " | CLOCK-KV hm_r26q4 10-27 D-KV-AHUB-ENTRY: ck[0]/rst_n[0] y 220.32 -> 241.92 (entry island into the free H channel, clear of g_zh[1])"
open(f"{pd}/cores/qkd_ahub_pins_r26q4.json", "w").write(json.dumps(d, indent=1) + "\n")
print("entry", old_entry["xy_um"], "->", ent, "| islands moved", len(moves), "max move", max(m["move_um"] for m in moves))
for m in moves: print(" ", m)
for s in sinks: print(" sink", s["inst"], s["pin_um"], "stub", s["stub_um"], "TT", s["arrival_TT_ps"], s["vs_target_TT_ps"], "FF", s["arrival_FF_ps"], s["vs_target_FF_ps"])
