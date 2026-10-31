#!/usr/bin/env python3
"""HUBMESH-6: a3e6 (A) / a3e6b (B) = a3e1c (18 e185 taps on 4 location sub-trees) + the other 17 plan early core taps.
A: one sub-tree per earliness class (a3e5 classes e100/e69/e57/e38).  B: e38 (both hubs) and NE e69 split W/E by location (>=2 taps per sub-tree)."""
import sys
src, dst, var = sys.argv[1:4]
A = {"e100p3": (100.3, ["clk_c43", "clk_c44", "clk_c45"], ["clk_c42", "clk_c43", "clk_c44"]),
     "e69p3": (69.3, ["clk_c52", "clk_c53", "clk_c56", "clk_c57"], ["clk_c49", "clk_c50", "clk_c53", "clk_c54"]),
     "e57p4": (57.4, ["clk_c19", "clk_c20"], ["clk_c18", "clk_c19"]),
     "e38p9": (38.9, ["clk_c82", "clk_c83", "clk_c84", "clk_c85", "clk_c86", "clk_c87", "clk_c88", "clk_c89"],
               ["clk_c79", "clk_c80", "clk_c81", "clk_c82", "clk_c83", "clk_c84", "clk_c85", "clk_c86"])}
B = {"e100p3": A["e100p3"],
     "e69p3": (69.3, ["clk_c52", "clk_c53", "clk_c56", "clk_c57"], None),
     "e69p3_W": (69.3, None, ["clk_c50", "clk_c54"]),
     "e69p3_E": (69.3, None, ["clk_c49", "clk_c53"]),
     "e57p4": A["e57p4"],
     "e38p9_W": (38.9, ["clk_c82", "clk_c83", "clk_c84", "clk_c85"], ["clk_c83", "clk_c84", "clk_c85", "clk_c86"]),
     "e38p9_E": (38.9, ["clk_c86", "clk_c87", "clk_c88", "clk_c89"], ["clk_c79", "clk_c80", "clk_c81", "clk_c82"])}
G = A if var == "A" else B
s = open(src).read()
j = s.index("      core_tap_prefix")
b = ""
for k, (lead, nw, ne) in G.items():
    b += "          %s:\n            lead_ps: %s\n            taps:\n" % (k, lead)
    for part, ts in (("NW_hub", nw), ("NE_hub", ne)):
        if ts:
            b += "              %s: [%s]\n" % (part, ", ".join(ts))
s = s[:j] + b + s[j:]
name = "hubmesh_a3e6" if var == "A" else "hubmesh_a3e6b"
note = ("# a3e6%s (HBM-HUBMESH-6) = a3e1c + the other 17 plan early core taps (FF 33.7-87.1 ps) on %s; a3e1c routed (GRT-RC) "
        "left only these undelivered (needed W 128.4/129.3 -> est ~66 ps if delivered)." % (
            "" if var == "A" else "b", "one sub-tree per earliness class" if var == "A" else "W/E location-split class sub-trees"))
s = note + "\n" + s.replace("name: hubmesh_a3e1c", "name: " + name).replace("source: HBM-HUBMESH-4", "source: HBM-HUBMESH-6")
open(dst, "w").write(s)
