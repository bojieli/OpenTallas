#!/usr/bin/env python3
"""added_tap_legalize.py PLAN OUT --types-file F [--parked PLAN_TP.json] [--report R.json]      (cwd = repo root)

--parked: first restore every added tap that core_place carried with a core back to its park_taps.py xy.

FRAME-SPINE-1113 (FRAME-FORMS-1-VOL): park_taps.py moved the non-core added taps off the seeded cores with its own
halo (12.96 um around cores, 43.2 um between parked taps).  The kit rule (taps.grid_explicit_sites) is stricter: an added
tap must lie TAP_CLEAR_UM inside the outline, outside every placement_obstacles box (halo TAP_CLEAR_UM; cores, stations,
...) and not within TAP_CLEAR_UM (both axes) of the R4 grid taps or of an earlier added tap.  For every added tap that
fails exactly that test, this moves it to the nearest (Manhattan) legal 4.32-lattice point; names, order and count are
kept, nothing is added.  Radius / load are left to added_tap_recentre.py, which runs next.  Report: per type the moves."""
import json
import sys
from pathlib import Path

sys.path[:0] = ["tools/die_plan"]
import schema  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402

G = 4.32


def main():
    a = sys.argv[1:]
    src, out = a[0], a[1]
    types = Path(a[a.index("--types-file") + 1]).read_text().split()
    raw = schema.load(src)
    P = schema.Plan(raw, src)
    eps, clear = 1e-8, schema.TAP_CLEAR_UM
    rep, nmov = {}, 0
    restored = {}
    if "--parked" in a:
        # core_place carries every point that lay inside a base core, added taps included (clk_t20 of col_h9_r1 rode
        # 1070 um west with its core); the added taps belong where park_taps.py put them: restore those xy first
        TP = json.loads(Path(a[a.index("--parked") + 1]).read_text())["partition_types"]
        for tn in types:
            pk = {p["name"]: p["xy"] for p in (TP[tn]["clock"].get("added_taps") or [])}
            for p in raw["partition_types"][tn]["clock"].get("added_taps") or []:
                if p["name"] in pk and [round(float(v), 4) for v in p["xy"]] != [round(float(v), 4) for v in pk[p["name"]]]:
                    restored.setdefault(tn, []).append(dict(tap=p["name"], carried=p["xy"], parked=pk[p["name"]]))
                    p["xy"] = list(pk[p["name"]])
        del TP
    for tn in types:
        typ = raw["partition_types"][tn]
        ck = typ.get("clock", {})
        if ck.get("tap_mode") != "grid+explicit":
            continue
        w, h = typ["outline_um"]
        boxes = list(placement_boxes(typ, halo=clear).values())
        grid = schema._grid_taps(P, tn)
        taken = [(x, y) for _, x, y in grid]

        def legal(x, y):
            return (clear - eps <= x <= w - clear + eps and clear - eps <= y <= h - clear + eps
                    and not any(abs(x - p) < clear - eps and abs(y - q) < clear - eps for p, q in taken)
                    and not any(b0 + eps < x < b2 - eps and b1 + eps < y < b3 - eps for b0, b1, b2, b3 in boxes))
        moves = []
        for p in ck.get("added_taps") or []:
            x, y = map(float, p["xy"])
            if not legal(x, y):
                best = None
                for r in range(1, 200):
                    for dx in range(-r, r + 1):
                        for dy in ((-r, r) if abs(dx) != r else range(-r, r + 1)):
                            q = (round(round((x + dx * G) / G) * G, 3), round(round((y + dy * G) / G) * G, 3))
                            if legal(*q):
                                d = abs(q[0] - x) + abs(q[1] - y)
                                if best is None or d < best[0]:
                                    best = (d, q)
                    if best:
                        break
                if best is None:
                    moves.append(dict(tap=p["name"], old=[x, y], new=None))
                    taken.append((x, y))
                    continue
                moves.append(dict(tap=p["name"], old=[x, y], new=list(best[1]), move_um=round(best[0], 3)))
                p["xy"] = list(best[1])
                x, y = best[1]
                nmov += 1
            taken.append((x, y))
        if moves:
            rep[tn] = moves
    Path(out).write_text(json.dumps(raw, indent=1))
    unf = sum(1 for m in rep.values() for x in m if x["new"] is None)
    print("types", len(types), "carried taps restored to parked xy", sum(map(len, restored.values())),
          "in", len(restored), "types; types with legality moves", len(rep), "taps moved", nmov, "unplaceable", unf)
    if "--report" in a:
        Path(a[a.index("--report") + 1]).write_text(json.dumps(dict(restored=restored, moves=rep), indent=1))
    return 1 if unf else 0


if __name__ == "__main__":
    sys.exit(main())
