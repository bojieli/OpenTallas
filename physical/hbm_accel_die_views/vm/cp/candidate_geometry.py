#!/usr/bin/env python3
"""Planning geometry from the actual packed pin ranges, never a closure claim."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CP = Path(__file__).resolve().parent
loader = importlib.util.spec_from_file_location("vm_cp", CP / "make_vm_cp.py")
plan = importlib.util.module_from_spec(loader)
loader.loader.exec_module(plan)
specs, instances, drivers, receivers = {}, {}, {}, {}
# On-grid moves repair the actual packed-range reach. Open relay tiles only.
# face/fork tiles: locked per-bit plans of face_pin_plan.py (fw2 | fw3 seam moved: u_fw3 origin follows fw2's height).
floader = importlib.util.spec_from_file_location("face_pin_plan", CP / "face_pin_plan.py")
fplan = importlib.util.module_from_spec(floader)
floader.loader.exec_module(fplan)
relay_y = dict(fplan.INST_Y)
for instance, master, x, y, orient, connections in plan.INST:
    if master not in specs:
        legacy = ROOT / "physical/ref_tile" / master / "spec.json"
        candidate = next((c for c in (CP / "codex_specs" / f"{master}_cx2.json", CP / "codex_specs" / f"{master}_cx.json")
                          if c.exists()), legacy)
        specs[master] = json.loads(candidate.read_text())
    spec = specs[master]
    width, height = spec["outline"]["w"], spec["outline"]["h"]
    x = plan.VMW - width if x is None else x
    y = relay_y.get(instance, y)
    instances[instance] = dict(x=x, y=y, w=width, h=height, orient=orient,
                               master=master, geometry_source=spec["name"])
    for port, net in connections.items():
        direction, bits = plan.ports_of(master)[port][:2]
        face = next(face for face, ports in spec["pins"].items() if port in ports)
        endpoints = []
        for offset in spec["pin_ranges"][port]:
            px = x + (0 if face == "W" else width if face == "E" else offset)
            py = y + (0 if face == "S" else height if face == "N" else offset)
            if orient == "MX":
                py = y + height - (py - y)
            endpoints.append((px, py))
        entry = dict(instance=instance, port=port, bits=bits, endpoints=endpoints)
        (drivers if direction == "out" else receivers).setdefault(net, []).append(entry)
hops = []
for net, sources in drivers.items():
    for source in sources:
        for dest in receivers.get(net, []):
            distances = [abs(a[0] - b[0]) + abs(a[1] - b[1])
                         for a, b in zip(source["endpoints"], dest["endpoints"])]
            hops.append(dict(net=net, frm=source["instance"] + "." + source["port"],
                             to=dest["instance"] + "." + dest["port"],
                             max_same_order_end_um=max(distances), mid_um=sum(distances) / 2))
overlap = []
boxes = list(instances.items())
for i, (name, a) in enumerate(boxes):
    for other, b in boxes[i + 1:]:
        if (min(a["x"] + a["w"], b["x"] + b["w"]) > max(a["x"], b["x"])
                and min(a["y"] + a["h"], b["y"] + b["h"]) > max(a["y"], b["y"])):
            overlap.append([name, other])
_inst, per_bit, _over = fplan.hops()
result = dict(planning_only=True, per_bit_hops=per_bit,
              per_bit_hops_above500=[hop for hop in per_bit if hop["max_bit_um"] > 500], region=[plan.VMW, plan.VMH], instances=instances,
              instance_count=len(instances), overlap=overlap, hops=hops,
              hops_endpoint_above500=[hop for hop in hops if hop["max_same_order_end_um"] > 500],
              limitations="Packed-range endpoints assume the same bit order at both ends. Actual bit-level "
              "net connectivity, detailed-route reach and source-matched closed views remain required.")
print(json.dumps(result, indent=2))
