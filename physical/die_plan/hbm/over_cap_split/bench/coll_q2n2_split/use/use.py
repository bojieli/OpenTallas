# use.py rest.json NAME out.json : per input port of the extracted remainder, the bit indices read by any cell or
# driving an output port (PATH-HBM/NE2 10-25; rest_wrap --use format: only ports with unread bits are listed)
import json, sys
d = json.load(open(sys.argv[1]))["modules"][sys.argv[2]]
used = set()
for c in d["cells"].values():
    for p, bits in c["connections"].items():
        if c.get("port_directions", {}).get(p, "input") != "output":
            used.update(b for b in bits if isinstance(b, int))
for n, p in d["ports"].items():
    if p["direction"] == "output":
        used.update(b for b in p["bits"] if isinstance(b, int))
out, tot = {}, 0
for n, p in d["ports"].items():
    if p["direction"] != "input":
        continue
    u = [i for i, b in enumerate(p["bits"]) if b in used]
    if len(u) < len(p["bits"]):
        out[n] = u; tot += len(p["bits"]) - len(u)
json.dump(out, open(sys.argv[3], "w"))
print("unread input bits", tot, {k: (len(d["ports"][k]["bits"]), len(v)) for k, v in out.items()})
