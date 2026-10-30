# DIE-HEAD-39 diagnostic: main nested_check with Verilog (* ... *) attributes stripped before parsing
# (gen_rtl.parse_leaf_ports drops ports declared as "(* keep *) output reg q"). Everything else = main code.
import json, re, sys
from pathlib import Path
sys.path.insert(0, "tools/die_plan")
import port_bind_gate as PBG
strip = lambda t: re.sub(r"\(\*.*?\*\)", "", t)
D = Path(sys.argv[1]); man = Path(sys.argv[2]).read_text().split()
wr = {p.name: strip(p.read_text()) for p in sorted(D.glob("*.sv")) if not p.name.startswith("s81_head_top")}
srcs = [strip(Path(x).read_text(errors="replace")) for x in man if not x.startswith(str(D))]
n = PBG.nested_check(wr, srcs)
Path(sys.argv[3]).write_text(json.dumps(n, indent=1) + "\n")
print("PORT_BIND_NESTED_ATTRSTRIP", n["verdict"], json.dumps({k: v for k, v in n.items() if k != "examples"}))
