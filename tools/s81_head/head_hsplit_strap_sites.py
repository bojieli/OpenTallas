#!/usr/bin/env python3
"""DIE-HEAD-84 HSPLIT: count strap sites of the two halves (head_count_strap_sites.apply, in place on PLAN)."""
import json, sys
sys.path[:0] = ["tools/die_plan", "tools/s81_head"]
from head_count_strap_sites import apply
f = sys.argv[1]; p = json.load(open(f))
out = apply(p, f, ".", types={"hd_host_w", "hd_host_e"})
q, rep = out if isinstance(out, tuple) else (out, None)
json.dump(q, open(f, "w"), indent=1); print(json.dumps(rep))
