# DIE-PROTO 2325: put a new die_trial signal kit under an existing combined-GRT clock section (Codex combo_legal:
# legal-site BUFx24 tree, 4W/8W NDR, M8-M9).  combo.v: replace the old signal body/ports; combo.tcl: new pre + old tail.
import re, sys, os
oldkit, oldcombo, newkit, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
def split(rv):
    mh = re.match(r"\s*module\s+(\w+)\s*\(([^)]*)\);", rv)
    return [p.strip() for p in mh.group(2).split(",") if p.strip()], rv[mh.end():rv.rindex("endmodule")]
op, ob = split(open(oldkit + "/grt/route.v").read()); np_, nb = split(open(newkit + "/grt/route.v").read())
cv = open(oldcombo + "/combo.v").read()
mh = re.match(r"\s*module\s+die_combo\s*\(([^)]*)\);", cv); allp = [p.strip() for p in mh.group(1).split(",") if p.strip()]
assert allp[:len(op)] == op, "old combo header != old kit ports"
cp = allp[len(op):]
rest = cv[mh.end():]
i = rest.index(ob); clockpart = rest[i + len(ob):]; decl = rest[:i]
assert set(np_).isdisjoint(cp)
v = "module die_combo (" + ", ".join(np_ + cp) + ");\n" + decl + nb + clockpart
open(out + "/combo.v", "w").write(v)
ct = open(oldcombo + "/combo.tcl").read(); tail = ct[ct.index("source /work/grt/obs.tcl"):]
t = open(newkit + "/grt/grt.tcl").read(); pre = t.split("source /work/grt/obs.tcl")[0]
pre = pre.replace("read_verilog /work/grt/route.v", "foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }\nread_verilog /out/combo.v")
pre = pre.replace(re.search(r"link_design \S+", pre).group(0), "link_design die_combo")
open(out + "/combo.tcl", "w").write(pre + tail)
print("ports", len(np_), "clock ports", len(cp), "old sig ports", len(op))
