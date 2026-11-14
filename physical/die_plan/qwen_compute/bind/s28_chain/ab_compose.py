#!/usr/bin/env python3
"""QC-S28-BIND: compose the bind's --asbuilt manifest from the ORIGINAL manifest plus the keys the guarded injectors
(cm_inject.py clock_merge, kp_inject.py kit_source_station_pricing) wrote into their own copies.  Each copy must equal
the original except for its one key (fail closed, exit 3).  ab_compose.py MANIFEST OUT KEY=COPY [KEY=COPY ...]"""
import json
import sys
from pathlib import Path

man, out, pairs = sys.argv[1], sys.argv[2], sys.argv[3:]
base = json.loads(Path(man).read_text())
res = json.loads(json.dumps(base))
for kv in pairs:
    k, c = kv.split("=", 1)
    cp = json.loads(Path(c).read_text())
    extra = {x for x in set(cp) | set(base) if x != k and cp.get(x) != base.get(x)}
    if extra or k not in cp:
        print("AB_COMPOSE FAIL", c, "differs from the manifest beyond", k, sorted(extra)[:5])
        sys.exit(3)
    if k in res and res[k] != cp[k] and k in base:
        print("AB_COMPOSE FAIL", k, "already in the manifest with another value")
        sys.exit(3)
    res[k] = cp[k]
if Path(out).resolve().parent != Path(man).resolve().parent:
    print("AB_COMPOSE FAIL OUT must sit beside MANIFEST")
    sys.exit(3)
Path(out).write_text(json.dumps(res, indent=1) + "\n")
print("AB_COMPOSE", out, "keys", [p.split("=")[0] for p in pairs])
