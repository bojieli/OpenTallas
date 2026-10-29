import json, sys
from pathlib import Path
sys.path.insert(0, "tools/die_plan")
import port_bind_gate as PBG
D = Path(sys.argv[1]); man = Path(sys.argv[2]).read_text().split()
wr = {p.name: p.read_text() for p in sorted(D.glob("*.sv")) if p.name.startswith("ot_s81hd_")}
srcs = [Path(x).read_text(errors="replace") for x in man if not Path(x).name.startswith(("ot_s81hd_", "s81_head_top")) or not x.startswith(str(D))]
n = PBG.nested_check(wr, srcs, max_list=100000)
Path(sys.argv[3]).write_text(json.dumps(n, indent=1) + "\n")
print("PORT_BIND_NESTED", n["verdict"], json.dumps({k: v for k, v in n.items() if k != "examples"}))
