"""R25 task 3 (COORD ruling R24b): A0 E-face pins vs the 8 E-strip island y-windows (R3b EF0-5/EN1-2, 8.64 islands, NK halo
kept).  Pin tables = plan pin tables inputs/d51/cores/a0_{nk,nl}_pins.json (core R0 frame; MX instances mirror the whole
core, so the core-frame check covers every instance).  Window = island centre y +- 4.32 (footprint) + 0.5 um access margin.
Proposal = one rigid shift of the whole E pin block on the M4 track pitch (0.048) into the free gap between the EF4 and
EF5 windows.  usage: r25_epins.py PINDIR R3B OUT.json"""
import json, re, sys, collections
pd, r3b, out = sys.argv[1:4]
R3 = json.load(open(r3b))
E = {k: v["centre"][1] for k, v in R3["islands"].items() if k[0] == "E"}
HALF, MARG, PITCH = 4.32, 0.5, 0.048
win = {k: (y - HALF - MARG, y + HALF + MARG) for k, y in E.items()}
res = dict(rule=__doc__.split("\n")[0], windows_um={k: [round(a, 3), round(b, 3)] for k, (a, b) in win.items()})
def hits(pins, dy=0.0):
    return {k: sum(1 for p in pins if a <= p["y"] + dy <= b) for k, (a, b) in win.items()}
for t in ("nk", "nl"):
    pins = [p for p in json.load(open(f"{pd}/a0_{t}_pins.json"))["pins"] if p["x"] > 457.92 / 2]
    lo, hi = min(p["y"] for p in pins), max(p["y"] for p in pins)
    buses = collections.Counter(re.sub(r"\[\d+\]", "", p["name"]) for p in pins)
    h0 = hits(pins)
    # free gaps between consecutive windows that hold the block span
    ws = sorted(win.values())
    gaps = [(b0, a1) for (a0, b0), (a1, b1) in zip(ws, ws[1:]) if a1 - b0 >= hi - lo]
    best = None
    for g0, g1 in gaps:
        # smallest |shift| on the track pitch that puts [lo, hi] inside [g0, g1]
        for dy in sorted({round(k * PITCH, 3) for k in range(int((g0 - lo) / PITCH) - 1, int((g1 - hi) / PITCH) + 2)}, key=abs):
            if g0 < lo + dy and hi + dy < g1:
                if best is None or abs(dy) < abs(best[0]):
                    best = (dy, g0, g1)
                break
    dy = best[0]
    res[t] = dict(e_pins=len(pins), layers=dict(collections.Counter(p["layer"] for p in pins)), buses=dict(buses),
                  y_span=[lo, hi], span_um=round(hi - lo, 3), hits_now=h0, pins_in_windows_now=sum(h0.values()),
                  shift_um=dy, new_span=[round(lo + dy, 3), round(hi + dy, 3)], gap=[round(best[1], 3), round(best[2], 3)],
                  hits_after=hits(pins, dy), clearance_um=[round(lo + dy - best[1], 3), round(best[2] - hi - dy, 3)],
                  ck_pin=[p for p in pins if p["name"] == "ck"])
res["verdict"] = ("POSSIBLE: identical 8.64 E islands + 5.4 halo kept; one rigid E-block shift per type, 0 pins in any window"
                  if all(sum(res[t]["hits_after"].values()) == 0 for t in ("nk", "nl")) else "NOT POSSIBLE by a rigid shift")
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({t: {k: res[t][k] for k in ("e_pins", "y_span", "pins_in_windows_now", "hits_now", "shift_um", "new_span", "clearance_um")} for t in ("nk", "nl")}, indent=0))
print(res["verdict"])
