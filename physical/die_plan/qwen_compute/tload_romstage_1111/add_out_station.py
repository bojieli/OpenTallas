"""add_out_station SRC IN_PLAN TYPE BUS PINS PROBE OUT_PLAN REPORT: STRUCT-CTL per_bit out station(s) on BUS of TYPE.

leaf = centroid of the planned launch sites (PROBE rows from p2o_probe.py: the flops that drive the face register of
BUS); station count = istation_knee.stations_needed (the kit knee rule, plan margin 400 um, kit stop 403 um); stations
on the line leaf -> pin centroid at (j+1)/(n+1), as qc_struct_ctl.py writes them.  Plan JSON style is preserved."""
import json, math, sys, collections
from pathlib import Path
SRC, INP, TN, BUS, PINS, PROBE, OUT, REP = sys.argv[1:9]
sys.path.insert(0, SRC + "/tools/die_plan")
import istation_knee as KN
raw_bytes = Path(INP).read_bytes(); raw = json.loads(raw_bytes)
t = raw["partition_types"][TN]
assert not any(e.get("conn") == "bus:" + BUS for e in t.get("internal_stations", [])), "bus already has stations"
rec = next(b for b in t["buses"] if b["name"] == BUS)
pins = json.load(open(PINS)); pins = pins["pins"] if isinstance(pins, dict) else pins
pts = [(float(p["x"]), float(p["y"])) for p in pins if p["bus"] == BUS]
pc = (sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts))
corners = [(min(x for x, _ in pts), min(y for _, y in pts)), (max(x for x, _ in pts), max(y for _, y in pts))]
rows = json.load(open(PROBE))
sites = {r["launch"]: tuple(r["site"]) for r in rows}
leaf = (round(sum(x for x, _ in sites.values()) / len(sites), 3), round(sum(y for _, y in sites.values()) / len(sites), 3))
off = KN.leaf_offset(t, rec)
n = KN.stations_needed(rec["face"], "out", leaf, corners, 1, KN.PLAN_MARGIN_UM, off)
worst = KN.worst_hop(rec["face"], "out", leaf, corners, n, off)
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
line = lambda a, b, f: [round(a[0] + (b[0] - a[0]) * f, 3), round(a[1] + (b[1] - a[1]) * f, 3)]
launch_far = max(L1(s, leaf) for s in sites.values())
e = dict(conn=f"bus:{BUS}", from_um=list(leaf), to_um=[round(pc[0], 3), round(pc[1], 3)],
         regs_um=[line(leaf, pc, (j + 1) / (n + 1)) for j in range(n)], bits=int(rec.get("width", len(pts) - 1)) + 1,
         launch="u_pd11_x_fw_i", capture=f"face {BUS}", bit_route="per_bit", leaf_um=list(leaf),
         note=f"TLOAD-ROMSTAGE B DIE-QC-97 11-11: +{n} pin cycles, u_pd11_x_fw_i chain ends (planned sites) -> {BUS} "
              f"pins {L1(leaf, pc):.0f} um (sle_ctl a-run: 1024 captures up to 790 um, no station)")
t2 = dict(t); t2["internal_stations"] = list(t.get("internal_stations", [])) + [e]
raw["partition_types"][TN] = t2
for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
          lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
          lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
    if f(json.loads(raw_bytes)).encode() == raw_bytes:
        Path(OUT).write_text(f(raw)); break
else:
    raise SystemExit("plan JSON style not recognised")
rep = dict(type=TN, bus=BUS, stations=n, leaf_um=leaf, pin_centroid=pc, leaf_to_pins_um=round(L1(leaf, pc), 1),
           kit_knee_worst_um=round(worst[0] if isinstance(worst, tuple) else worst, 1), launch_to_leaf_max_um=round(launch_far, 1),
           launch_flops=len(sites))
Path(REP).write_text(json.dumps(rep, indent=1) + "\n"); print(json.dumps(rep))
