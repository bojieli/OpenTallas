"""HEAD real top: tie-VALUE audit PASS on the emitted top, FAIL (G0 ERROR) with one tie bit flipped / one tie dropped"""
import json, re, sys
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import straps as STR, clock_landings as CL
O = sys.argv[2]
st = json.load(open(O + "/straps.json"))
exp = {CL.ident(q): {p: (st["types"][v["type"]]["straps"][p], val) for p, val in v["values"].items()}
       for q, v in st["instances"].items() if v["values"]}
top = open(O + "/gen/s81_head_top.sv").read()
a = STR.audit_count_strap_values(top, exp)
print("clean", a["verdict"], a["checked_bits"], len(exp), "instances")
m = re.search(r"\.(strap_ca_k_\w+)\((\d+)'b([01]+)\)", top)
bits = m.group(3); fl = bits[:-1] + ("1" if bits[-1] == "0" else "0")
mut = top[:m.start(3)] + fl + top[m.end(3):]
b = STR.audit_count_strap_values(mut, exp)
print("flip", m.group(1), bits, "->", fl, b["verdict"], b["severity"], b["errors"][:1])
mut2 = top[:m.start()] + ".dropped_pin(1'b0)" + top[m.end():]
c = STR.audit_count_strap_values(mut2, exp)
print("drop", c["verdict"], c["severity"], c["errors"][:1])
