"""DIE-HBM-10 C23q: the PHY_NW / PHY_NE reset-tap edit of apply_c23q.py section 1, applied in place to a plan built
before that edit (no later chain step -- ft_corridor, c23q_root_site, census-complete -- reads a hard type's reset tap,
so the result equals a re-run of the corrected chain).  Rewrites die_plan.sha256.
usage: c23q_reset_tap_fix.py PLAN_DIR"""
import hashlib, json, sys
from pathlib import Path
d = Path(sys.argv[1]); p = d / "die_plan.json"; P = json.loads(p.read_text())
for n, x in (("PHY_NW", 0.0), ("PHY_NE", None)):
    t = P["partition_types"][n]
    t["reset"]["tap_um"] = [t["outline_um"][0] if x is None else x, 172.8]
    print(n, t["reset"])
p.write_text(json.dumps(P, indent=1))
(d / "die_plan.sha256").write_text(hashlib.sha256(p.read_bytes()).hexdigest() + "  die_plan.json\n")
