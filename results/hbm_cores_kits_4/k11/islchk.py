import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import kit_contract as KC
for kd in sys.argv[2:]:
    kd = Path(kd)
    cip = json.loads((kd / "core_infra_plan.json").read_text())
    rects = []
    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("rect_um", "island_um", "rect") and isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v):
                    rects.append((path + "/" + k, v))
                else:
                    walk(v, path + "/" + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + f"[{i}]")
    walk(cip)
    cfg = KC._mk(kd)
    halo = max([KC._num(t) or 0.0 for t in cfg.get("MACRO_PLACE_HALO", "0").split()] or [0.0])
    boxes, prob = KC.macro_boxes(kd) if cfg.get("MACRO_PLACEMENT_TCL") else (None, "none")
    hits = []
    for b in boxes or []:
        g = (b[1] - halo, b[2] - halo, b[3] + halo, b[4] + halo)
        for p, r in rects:
            if g[0] < r[2] and r[0] < g[2] and g[1] < r[3] and r[1] < g[3]:
                hits.append((b[0], p, r))
    print(kd.name, "islands", len(rects), "macros", len(boxes or []), "OVERLAPS", len(hits), hits[:3])
