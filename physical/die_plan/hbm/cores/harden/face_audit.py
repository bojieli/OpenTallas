"""face-rule audit of every core pin file in the census (<=6 pins/um per face averaged and in any 10-um window)."""
import collections, json, sys
from pathlib import Path
root = Path(sys.argv[1]); cen = json.load(open(sys.argv[2]))["types"]
out = []
for r in cen:
    w, h = r["outline_um"]
    pins = json.load(open(root / r["pins_file"]))
    by = collections.defaultdict(list)
    for p in pins:
        x, y = p["x"], p["y"]
        f = min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]
        by[f].append(y if f in "EW" else x)
    worst_avg = worst_win = 0
    used = {}
    for f, co in by.items():
        co.sort(); span = h if f in "EW" else w
        j = 0; win = 0
        for i in range(len(co)):
            while co[i] - co[j] > 10: j += 1
            win = max(win, i - j + 1)
        worst_avg = max(worst_avg, len(co) / span); worst_win = max(worst_win, win / 10)
        used[f] = round((co[-1] - co[0]) / span, 2)
    perim_need = len(pins) / 5.0
    out.append(dict(type=r["type_id"], pins=len(pins), perim=2 * (w + h), avg_max=round(worst_avg, 2),
                    win_max=round(worst_win, 2), face_used_frac=used,
                    feasible_at_5=len(pins) <= 5.0 * 2 * (w + h), excluded=r["excluded"]))
json.dump(out, open(sys.argv[3], "w"), indent=1)
ok = [o for o in out if o["win_max"] <= 6 and o["avg_max"] <= 6]
inf = [o for o in out if not o["feasible_at_5"]]
print("types", len(out), "face-rule PASS", len(ok), "FAIL", len(out) - len(ok), "| perimeter infeasible at 5/um:", len(inf))
for o in inf: print("  INFEASIBLE", o["type"], o["pins"], "pins, perimeter", round(o["perim"]), "um")
print("PASS list:", [o["type"] for o in ok][:20])
