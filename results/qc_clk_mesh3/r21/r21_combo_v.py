"""R21: combo.v = kit route.v + ctree.v, the exact composition of die_clock_mesh.cmd_combo (combo.tcl unchanged)."""
import re, sys
from pathlib import Path
rv, cv, out = (Path(x).read_text() for x in sys.argv[1:3]) , None, None
rv, cv = Path(sys.argv[1]).read_text(), Path(sys.argv[2]).read_text()
mh = re.match(r"\s*module\s+(\w+)\s*\(([^)]*)\);", rv)
rports = [p.strip() for p in mh.group(2).split(",") if p.strip()]
rbody = rv[mh.end():rv.rindex("endmodule")]
mc = re.search(r"module\s+die_ctree\s*\(([^)]*)\);", cv, re.S)
cports = [p.strip() for p in mc.group(1).split(",") if p.strip()]
assert not set(rports) & set(cports)
cbody = cv[mc.end():cv.rindex("endmodule")]
Path(sys.argv[3]).write_text(f"module die_combo ({', '.join(rports + cports)});\n" + rbody + cbody + "endmodule\n")
