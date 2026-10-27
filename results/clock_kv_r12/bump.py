"""CLOCK-KV-R12: +1 station on the 4 pv slots whose route length / stations is already >= 400 um (no slack for any
core-avoiding slide after the headmirror moves): kv3_pv_v12 ft33/ft39/ft40, kv3_pv_v7 ft48 (5 -> 6)."""
import json, sys
P = json.load(open(sys.argv[1])); led = []
for tn, sn in (("kv3_pv_v12", "ft33"), ("kv3_pv_v12", "ft39"), ("kv3_pv_v12", "ft40"), ("kv3_pv_v7", "ft48")):
    s = next(x for x in P["partition_types"][tn]["ft_slots"] if x["name"] == sn)
    s.pop("regs_um", None); s["stations"] = int(s["stations"]) + 1; led.append([tn, sn, s["width"], s["stations"]])
json.dump(P, open(sys.argv[2], "w")); print(led)
