"""R21: channel stack census (R20 item 10 form): every pin stack whose pin lies in the centre clock channel rect;
count those whose riser start (M8 trunk junction) lies outside the channel (riser crosses the partition face)."""
import json, sys
from collections import Counter
CH = (1563.84, 13132.8, 31216.32, 13176.0)
for d in sys.argv[1:]:
    try:
        M = json.load(open(f"{d}/dry_exact/mesh.json"))
    except FileNotFoundError:
        pe = json.load(open(f"{d}/dry_exact/plan_errors.json")) if __import__("os").path.exists(f"{d}/dry_exact/plan_errors.json") else []
        print(d, "NO mesh.json; plan errors", Counter(e["kind"] for e in (pe if isinstance(pe, list) else pe.get("errors", []))))
        continue
    n = out = 0
    bad = []
    for w in M["fixed_wires"]:
        for s in w.get("stacks", []):
            x, y = s["xy"]
            if CH[0] <= x <= CH[2] and CH[1] - 1e-6 <= y <= CH[3] + 1e-6:
                n += 1
                ry = s["riser_from"][1]
                if not (CH[1] <= ry <= CH[3]):
                    out += 1
                    bad.append((w["name"], s["cell"], y, ry))
    print(d, "channel stacks", n, "riser outside channel", out, bad[:6], "root", M["meta"].get("root_um"))
