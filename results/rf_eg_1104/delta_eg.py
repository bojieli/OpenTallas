#!/usr/bin/env python3
"""S81 plan event RF-EG (DIE-S81-53 11-04): dissolve hard core ot_s81sl_eg into its signed RF1 blocks in all 16 *_C types.
ot_s81sl_eg on main is a wires-only wrapper of u_nh/u_nk (ot_s81sl_egn) + u_gg (ot_s81sl_egg), both blocks signed off
(flow-20261103-x-s81, egn TT +26.51 FF +0.11, egg TT +27.96 FF +0.10).  A parent kit would be an empty kit; the plan names the
blocks directly (physical identity u_bound.u_u_..._u_eg_u_nh via bound_macro_paths).  Slot 259.2x259.2 -> footprint
267.84x311.04, growing away from xfin: R0 (xfin below) north, MX (xfin above) south, 8.64-um channels so egg clk/rst_n
(S-face mid, 131 um) are reachable between the two egn blocks.  t3/t8 have no room north (34.56): the box moves beside xfin.
Text-level edit: JSON output equals the dict delta; compact sections are kept.
    python3 delta_eg.py <plan in> <plan out>
"""
import copy, json, re, sys
src, out = sys.argv[1], sys.argv[2]
txt = open(src).read()
plan = json.loads(txt)
VIEW = "physical/die_plan/s81/cores/views/eg_signed_1104"
G = 8.64
EGN = (129.6, 146.88); EGG = (259.2, 155.52)
BOX = (EGN[0] * 2 + G, EGN[1] + G + EGG[1])
MOVE = {"dsdv_slice_c1x_C__t3": (570.24, 881.28), "dsdv_slice_c1x_C__t8": (1097.28, 881.28)}
PIN = {"ot_s81sl_egn": dict(clk=62.988, rst=64.812), "ot_s81sl_egg": dict(clk=127.788, rst=131.436)}
INS = {m: json.load(open(f"{VIEW}/{m}/insertion.json")) for m in PIN}
FR = dict(u_nh=(0.0, 0.0, "ot_s81sl_egn"), u_nk=(EGN[0] + G, 0.0, "ot_s81sl_egn"), u_gg=(4.32, EGN[1] + G, "ot_s81sl_egg"))
SIZE = dict(ot_s81sl_egn=EGN, ot_s81sl_egg=EGG)
R = lambda v: round(v, 3)
edits = {}
for name, t in plan["partition_types"].items():
    hc = t.get("hard_cores") or []
    old = [c for c in hc if c["module"] == "ot_s81sl_eg"]
    if not old:
        continue
    old = old[0]; idx = hc.index(old)
    ox, oy = old["origin_um"]; orient = old["orient"]
    if name in MOVE:
        bx, by = MOVE[name]
    else:
        bx = ox; by = oy if orient == "R0" else oy + 259.2 - BOX[1]
    rows, taps, resets = [], [], []
    ot = next(x for x in t["clock"]["taps"] if x["name"] == "u_c.u_eg.clk")
    cts = t["clock"]["landing_contract"]["collector_tree"]
    ors = next(x for x in cts["core_resets"] if x["inst"] == "u_c.u_eg")
    for inst, (fx, fy, m) in FR.items():
        w, h = SIZE[m]
        x = R(bx + fx)
        y = R(by + fy) if orient == "R0" else R(by + BOX[1] - fy - h)
        rows.append({"inst": f"u_c.u_eg.{inst}", "module": m, "lef": f"{VIEW}/{m}/{m}.lef", "origin_um": [x, y], "outline_um": [w, h],
                     "orient": orient, "track_offset_um": old["track_offset_um"], "pins_file": f"inputs/core_pins/{m}.json", "obs_max": "M5",
                     "lib": f"{VIEW}/{m}/{m}_tt.lib"})
        cy = y + 0.24 if orient == "R0" else y + h - 0.24
        ry = y + 0.042 if orient == "R0" else y + h - 0.042
        off = -4.32 if orient == "R0" else 4.32
        taps.append(dict(ot, name=f"u_c.u_eg.{inst}.clk", xy=[R(x + PIN[m]["clk"]), R(cy)], insertion_ps=INS[m]["tt"]["boundary"]["mean"],
                         insertion_ff_ps=INS[m]["ff"]["boundary"]["mean"], budget_owner=f"parent_budget pin_register_mean {VIEW}/{m}/insertion.json"))
        resets.append(dict(ors, inst=f"u_c.u_eg.{inst}", pin_um=[R(x + PIN[m]["rst"]), R(ry)], xy=[R(x + PIN[m]["rst"]), R(ry + off)]))
    bb = (bx, by, bx + BOX[0], by + BOX[1])
    for c in hc:
        if c is old: continue
        x, y = c["origin_um"]; w, h = c["outline_um"]
        assert x >= bb[2] + 8.64 or x + w <= bb[0] - 8.64 or y >= bb[3] + 8.64 or y + h <= bb[1] - 8.64, (name, c["module"], bb)
    W, H = t["outline_um"]
    assert bb[0] >= 17.28 and bb[1] >= 17.28 and bb[2] <= W - 17.28 and bb[3] <= H - 17.28, (name, bb)
    inside = [a["name"] for a in t["clock"].get("added_taps", []) if bb[0] - 2.16 <= a["xy"][0] <= bb[2] + 2.16 and bb[1] - 2.16 <= a["xy"][1] <= bb[3] + 2.16]
    moves = {}
    for a in t["clock"].get("added_taps", []):
        if a["name"] in inside:      # grid tap the box now covers: out of the box in the growth direction, same x
            nxy = [a["xy"][0], R(bb[3] + 8.64) if orient == "R0" else R(bb[1] - 8.64)]
            moves[a["name"]] = (list(a["xy"]), nxy); a["xy"] = nxy
    edits[name] = dict(rows=rows, taps=taps, resets=resets, inside=inside, moves=moves)
    hc[idx:idx + 1] = rows
    tt = t["clock"]["taps"]; i = tt.index(ot); tt[i:i + 1] = taps
    cr = cts["core_resets"]; i = cr.index(ors); cr[i:i + 1] = resets
    if "n_reset_consumers" in cts: cts["n_reset_consumers"] += 2
    if "n_clock_taps" in cts: cts["n_clock_taps"] += 2
print(len(edits), {k: v["inside"] for k, v in edits.items() if v["inside"]})
# text edit, in file order of partition types
D = lambda o: json.dumps(o, separators=(",", ":"))
new = txt
def sub_in(body, pat, repl, cnt=1):
    b, n = re.subn(pat, repl, body, count=cnt, flags=re.S)
    assert n == cnt, pat
    return b
pos = [(m.start(), m.group(1)) for m in re.finditer(r'(?m)^  ?  ?"(\w+)": \{\s*$', txt) if m.group(1) in plan["partition_types"]]
assert {n for _, n in pos} >= set(edits), set(edits) - {n for _, n in pos}
pos.sort(); spans = []
for i, (s, n) in enumerate(pos):
    e = pos[i + 1][0] if i + 1 < len(pos) else len(txt)
    spans.append((s, e, n))
res, last = [], 0
for s, e, n in spans:
    if n not in edits: continue
    res.append(txt[last:s]); body = txt[s:e]; ed = edits[n]
    body = sub_in(body, r'\{"inst":"u_c\.u_eg","module":"ot_s81sl_eg".*?\}(?=,?\s*\n)', lambda m: ",\n    ".join(D(r) for r in ed["rows"]))
    body = sub_in(body, r'\{\s*"name": "u_c\.u_eg\.clk".*?\n\s*\}', lambda m: ", ".join(D(r) for r in ed["taps"]))
    body = sub_in(body, r'\{\s*"inst": "u_c\.u_eg",.*?\n\s*\}', lambda m: ", ".join(D(r) for r in ed["resets"]))
    for tn, (oxy, nxy) in ed["moves"].items():
        body = sub_in(body, r'("name": "%s",.*?"xy": \[\s*)%s(,\s*)%s(\s*\])' % (tn, re.escape(str(oxy[0])), re.escape(str(oxy[1]))),
                      lambda m: m.group(1) + str(nxy[0]) + m.group(2) + str(nxy[1]) + m.group(3))
    for key in ("n_reset_consumers", "n_clock_taps"):
        body = re.sub(rf'("{key}": )(\d+)', lambda m: m.group(1) + str(int(m.group(2)) + 2), body, count=1)
    res.append(body); last = e
res.append(txt[last:]); new = "".join(res)
assert json.loads(new) == plan, "text edit differs from dict delta"
open(out, "w").write(new)
print("delta_eg OK")
