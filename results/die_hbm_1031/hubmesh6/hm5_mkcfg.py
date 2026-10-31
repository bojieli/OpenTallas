import sys
src, dst, name, note = sys.argv[1:5]
G = {"W": (["clk_c66","clk_c67","clk_c68","clk_c69"], ["clk_c60","clk_c61","clk_c62","clk_c23"]),
     "CW": (["clk_c58","clk_c59","clk_c60","clk_c61","clk_c62","clk_c23"], ["clk_c55","clk_c56","clk_c57","clk_c58","clk_c59"]),
     "C": (["clk_c70","clk_c71","clk_c72","clk_c73"], ["clk_c67","clk_c68","clk_c69","clk_c70"]),
     "E": (["clk_c24","clk_c63","clk_c64","clk_c65"], ["clk_c22","clk_c63","clk_c64","clk_c65","clk_c66"])}
s = open(src).read()
i = s.index("        groups:\n"); j = s.index("      core_tap_prefix")
b = "        groups:\n"
for k, (nw, ne) in G.items():
    b += "          e185p4_%s:\n            lead_ps: 185.4\n            taps:\n              NW_hub: [%s]\n              NE_hub: [%s]\n" % (k, ", ".join(nw), ", ".join(ne))
s = s[:i] + b + s[j:]
lines = s.split("\n")
lines[0] = note
s = "\n".join(lines).replace("name: hubmesh_a3e1", "name: " + name)
open(dst, "w").write(s)
