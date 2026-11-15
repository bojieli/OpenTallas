"""HEAD-99 hd_host_e FORM A (FABLE-PD-HKQ H2): u_head banks 5-8 (the pins farthest from u_epc south face) move to a stack at x 345.6, y 103.68.. (17.28 pitch, contiguous),
~230 um nearer the u_epc south-face in_data pins (Manhattan from bank 6 (318,311) to pin (619,60): 552 -> ~320).  Translations only.
usage: hostE_formA.py PLAN_IN PLAN_OUT"""
import json, sys
a, b = sys.argv[1:3]
d = json.load(open(a)); t = d["partition_types"]["hd_host_e"]; hc = t["hard_cores"]
def rect(h):
    w, hh = h["outline_um"]; x, y = h["origin_um"]; return (x, y, x + w, y + hh)
def ov(r, s, m=0.05): return r[0] < s[2]-m and s[0] < r[2]-m and r[1] < s[3]-m and s[1] < r[3]-m
y = 103.68
for k in (5, 6, 7, 8):
    for h in hc:
        if h["inst"].endswith(f"u_ski.u_head.g_bank[{k}].u_m"):
            print(h["inst"][-30:], h["origin_um"], "->", [345.6, round(y, 4)]); h["origin_um"] = [345.6, round(y, 4)]; y += 17.28
o = t["outline_um"]
for i, h in enumerate(hc):
    r = rect(h); assert r[0] >= 0 and r[1] >= 0 and r[2] <= o[0] and r[3] <= o[1], h["inst"]
    for g in hc[i+1:]: assert not ov(r, rect(g)), (h["inst"], g["inst"])
t["note"] += " | HEAD-99 hd_host_e FORM A (FABLE-PD-HKQ H2): u_head banks 5-8 moved to x 345.6 y 103.68-172.8, ~230 um nearer the u_epc south in_data pins."
json.dump(d, open(b, "w"), indent=1, ensure_ascii=False); print("ok")
