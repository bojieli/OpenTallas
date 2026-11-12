"""m89 bay taps (X-TIER-OTC, COORD blocker 1 "tap capacity per bay"): one light clock tap per register bay.

Die-agnostic post-pass on a form-(d) plan: every ft slot with bay_um and stations > 0 in a clock.tap_mode
"grid+explicit" type gets one clock.added_taps entry at the legal point nearest its bay centre (outline/halo/
spacing as taps.grid_explicit_sites checks).  The bay's station flops then take their own tap (nearest + cap)
instead of piling onto the nearest grid/added tap.  Existing tap names are kept (new taps are appended), so
landing / reset contract references do not move.  A new tap that ends up empty is dropped.

  python3 bay_taps.py PLAN_IN PLAN_OUT [--types t1,t2]
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S                     # noqa: E402
import taps                            # noqa: E402
from placement_obstacles import placement_boxes   # noqa: E402

STEP = 2.7
PLAN_PATH = None


def _plan(raw):
    P = S.Plan(raw)
    if PLAN_PATH:
        P.path = PLAN_PATH
    return P


def legal(x, y, w, h, clear, taken, boxes, eps=1e-8):
    return (clear - eps <= x <= w - clear + eps and clear - eps <= y <= h - clear + eps
            and not any(abs(x - a) < clear - eps and abs(y - b) < clear - eps for a, b in taken)
            and not any(a + eps < x < c - eps and b + eps < y < d - eps for a, b, c, d in boxes))


def site(bay, w, h, clear, taken, boxes):
    x0, y0, x1, y1 = bay
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    pts = []
    nx, ny = int((x1 - x0) / STEP) + 1, int((y1 - y0) / STEP) + 1
    for i in range(nx):
        for j in range(ny):
            pts.append((x0 + i * STEP, y0 + j * STEP))
    pts.sort(key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))
    for x, y in pts:
        if legal(x, y, w, h, clear, taken, boxes):
            return round(x, 3), round(y, 3)
    return None


def add_bay_taps(raw, types=None):
    rep = {}
    for tn, t in raw["partition_types"].items():
        if types and tn not in types:
            continue
        ck = t.get("clock") or {}
        if ck.get("tap_mode") != "grid+explicit":
            continue
        bays = [s for s in t.get("ft_slots", []) if s.get("bay_um") and int(s.get("stations", 0)) > 0]
        if not bays:
            continue
        P = _plan(raw)
        grid = S._grid_taps(P, tn)
        table = ck.setdefault("added_taps", [])
        taken = [(x, y) for _, x, y in grid] + [tuple(map(float, p["xy"])) for p in table]
        w, h = t["outline_um"]
        boxes = list(placement_boxes(t, halo=S.TAP_CLEAR_UM).values())
        new, miss = [], []
        for s in bays:
            xy = site(s["bay_um"], w, h, S.TAP_CLEAR_UM, taken, boxes)
            if xy is None:
                miss.append(s["name"])
                continue
            taken.append(xy)
            new.append((s["name"], xy))
        n0 = len(grid) + len(table)
        for i, (_, xy) in enumerate(new):
            table.append({"name": f"clk_t{n0 + i}", "xy": [xy[0], xy[1]]})
        # drop empty new taps (bay sinks not counted as tap sinks, e.g. a pure landing bay); re-number the tail
        for _ in range(len(new) + 1):
            P = _plan(raw)
            try:
                taps.grid_explicit_taps(P, tn)
                break
            except ValueError as e:
                m = str(e)
                bad = [p for p in table[n0 - len(grid):] if f"tap {p['name']} " in m and "empty=True" in m]
                if not bad:
                    break
                table.remove(bad[0])
                for k, p in enumerate(table):
                    p["name"] = f"clk_t{len(grid) + k}"
        P = _plan(raw)
        try:
            loads = taps.grid_explicit_taps(P, tn)
            verdict = f"OK max_added_load={max((q[3] for q in loads[len(grid):]), default=0):g}"
        except ValueError as e:
            verdict = f"FAIL {e}"
        rep[tn] = dict(added=len(table) - (n0 - len(grid)), unsited=miss, verdict=verdict)
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--types", default="")
    a = ap.parse_args(argv)
    global PLAN_PATH
    PLAN_PATH = str(Path(a.plan).resolve())
    raw = json.load(open(a.plan))
    rep = add_bay_taps(raw, set(filter(None, a.types.split(","))) or None)
    json.dump(raw, open(a.out, "w"))
    for tn, r in sorted(rep.items()):
        print("BAY_TAPS", tn, json.dumps(r))
    return 1 if any(r["verdict"].startswith("FAIL") for r in rep.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
