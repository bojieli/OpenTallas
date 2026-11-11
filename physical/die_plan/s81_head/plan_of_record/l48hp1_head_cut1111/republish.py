import sys, importlib.util
from pathlib import Path
root = Path(sys.argv[1]); out = Path(sys.argv[2]); types = sys.argv[3].split(',')
sys.path[:0] = [str(root / "tools/die_plan"), str(root / "tools/s81_head")]
spec = importlib.util.spec_from_file_location("hcsd", root / "tools/s81_head/head_cland_stage_delta.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.republish(out, root, types, out / "source_sidecar.json")
print("republished", types)
