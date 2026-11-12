"""DIE-S81-87 (DO_NOT_COUNT): COORD 10:3x CLAND-CLASS-1 adoption: iqf__t1 reset_relay_full + verilog_defines. IN OUT REPORT."""
import json, sys
inp, out, rep = sys.argv[1:4]
P = json.load(open(inp)); T = P["partition_types"]["iqf__t1"]
T["reset_relay_full"] = True
d = list(T.get("verilog_defines", []))
for x in ("OT_S81_CLAND_WCHK", "OT_S81_CLAND_LOCAL_ON"):
    if x not in d: d.append(x)
T["verilog_defines"] = d
json.dump(P, open(out, "w"), indent=1); open(rep, "w").write(json.dumps({"iqf__t1": {"reset_relay_full": True, "verilog_defines": d}}))
