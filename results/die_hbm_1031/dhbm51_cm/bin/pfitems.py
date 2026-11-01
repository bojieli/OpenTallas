import json,sys
from pathlib import Path
for k in sys.argv[1:]:
    d=json.load(open(Path(k)/"preflight.json")) if (Path(k)/"preflight.json").is_file() else {}
    print(Path(k).name, list(d.keys())[:12])
    def walk(o,p=""):
        if isinstance(o,dict):
            for a,b in o.items():
                if a in ("macro_channels","clock_entry_clear","macro_pin_grid","macro_instances","island_macro_clear","macro_boxes"): print("  ",p+a,json.dumps(b)[:230])
                walk(b,p+a+".")
    walk(d)
