from pathlib import Path
import re
r=Path(__file__).parent
s=(r/"mesh.def").read_text()
m=re.search(r"(?ms)- ck_mesh\\b.*?;",s)
if m is None:m=re.search(r"(?ms)- ck_mesh\b.*?;",s)
assert m
new="\n".join(x for x in m.group().splitlines() if "VIA" not in x).rstrip(" ;\n")+" ;"
(r/"mesh_straps.def").write_text(s[:m.start()]+new+s[m.end():])
t=(r/"build.tcl").read_text().replace("/work/mesh.def","/work/mesh_straps.def").replace("mesh_before.odb","mesh_straps.odb").replace("mesh_before.def","mesh_straps_before.def").replace("mesh.sdc","mesh_straps.sdc")
(r/"build_straps.tcl").write_text(t)
