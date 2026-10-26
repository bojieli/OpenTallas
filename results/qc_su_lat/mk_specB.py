# mk_specB.py SPEC_IN SPEC_OUT XW XE : QC-SU-LAT variant B -- W legs fed from a W band trunk at XW, E + MACRO legs from an
# E band trunk at XE (both straight from the S-face root), instead of every leg hanging off one W band (W-detour).
import sys,re
src,dst,xw,xe=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4])
t=open(src).read()
root=re.search(r"set ot_ms_root \{([\d.]+) ([\d.]+)\}",t); rx,ry=root.group(1),root.group(2)
bands=re.findall(r"\{(R\d) \{[^}]*? ([\d.]+)\}\}",t[t.index("ot_ms_bands"):t.index("ot_ms_legs")])
legs_txt=t[t.index("set ot_ms_legs"):t.index("set ot_ms_macros")]
nb=["set ot_ms_bands {"]
for n,y in bands:
  nb.append(" {B%sW {%s %s %g %s %g %s}}"%(n[1:],rx,ry,xw,ry,xw,y)); nb.append(" {B%sE {%s %s %g %s %g %s}}"%(n[1:],rx,ry,xe,ry,xe,y))
nb.append("}\n")
nl=["set ot_ms_legs {"]
for m in re.finditer(r"\{(R\d)([WME]) R\d \{([\d. ]+)\} (\{\{[^}]*\}\}|MACRO)\}",legs_txt):
  b,k,pts,reg=m.groups(); p=pts.split(); y=p[1]
  bx=xw if k=="W" else xe; side="W" if k=="W" else "E"
  # new polyline: band node (bx,y) -> (leg end x, y) -> leg end
  nl.append(" {%s%s B%s%s {%g %s %s %s %s %s} %s}"%(b,k,b[1:],side,bx,y,p[-2],y,p[-2],p[-1],reg))
nl.append("}\n")
out=t[:t.index("set ot_ms_bands")]+"\n".join(nb)+"\n".join(nl)+t[t.index("set ot_ms_macros"):]
out="# QC-SU-LAT variant B (2026-10-26): split W/E band trunks (W x=%g, E x=%g), legs <=~35 um; derived from %s\n"%(xw,xe,src)+out
open(dst,"w").write(out); print(out)
