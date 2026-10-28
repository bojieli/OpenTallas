"""Per-adder interleaved W-face pin plan for ot_qwen_tile_node (DIE-QC-18-PINILV, COORD 13:45 10-28).
Only W-face a/b/y/va names move; t_out/t_vout/vy/E face/clk unchanged; slots on the M4 track grid (offset 0.012, pitch 0.048), 0.192 pin pitch."""
import json, sys
src, dst = sys.argv[1], sys.argv[2]
P = json.load(open(src))
old = {q["name"]: q for q in P["pins"]}
PITCH, X = 0.192, 0.042
def slot(y0, k): return round(y0 + k * PITCH, 3)
new = {}
def group(p): return [f"a[{32*p+i}]" for i in range(32)] + [f"b[{32*p+i}]" for i in range(32)] + [f"y[{32*p+i}]" for i in range(32)]
k = 0
for p in range(10):
    for n in group(p): new[n] = slot(10.908, k); k += 1
new["va"] = slot(10.908, k)
k = 0
for p in range(10, 16):
    for n in group(p): new[n] = slot(312.492, k); k += 1
pins = []
for q in P["pins"]:
    q = dict(q)
    if q["name"] in new:
        assert q["layer"] == "M4" and abs(q["x"] - X) < 1e-9, q
        q["y"] = new[q["name"]]
    pins.append(q)
assert len(new) == 1537 and len(pins) == len(P["pins"])
for q in pins: assert abs(((q["y"] - 0.012) / 0.048) - round((q["y"] - 0.012) / 0.048)) < 1e-6, q
out = dict(P); out["pins"] = pins
out["source"] = (P["source"] + " | DIE-QC-18-PINILV 10-28 (COORD 13:45 approved): W-face a/b/y re-planned PER ADDER "
                 "(group p = a[32p+:32] | b[32p+:32] | y[32p+:32], 96 pins, 0.192 um pitch on the M4 track grid): adders 0-9 from "
                 "y 10.908, va after adder 9, adders 10-15 from 312.492; t_out/t_vout feedthrough band, vy, E face and clk unchanged; "
                 "RTL unchanged (opt-in recipe ot_qwen_tile_node_ilv, suffix a0k6)")
open(dst, "w").write(json.dumps(out) + "\n")
ys = sorted(new.values()); print("va", new["va"], "lower max", max(v for v in ys if v < 211), "upper", min(v for v in ys if v > 300), max(ys))
