#!/usr/bin/env python3
"""QC-SMALLREG-1 probe: locality v3 (main 810b714798) with count_align_plan.py of MESO-RECONCILE @32e8cbb16 (min-ambiguity
start tree) and the 12.15b spice clock factors per corner (x1.0485 TT / x1.0552 FF on d, p_up, p_dn, unshared).
usage: v3_reconcile.py TOOLS_COPY PLAN OUT TAG=MAP..."""
import sys
tools, plan, out = sys.argv[1:4]
sys.path.insert(0, tools)
import locality as L
F = {"TT": 1.0485, "FF": 1.0552}
_orig = L.cap_corner_rows
def scaled(R):
    o = _orig(R)
    for c, rows in o.items():
        k = next(v for kk, v in F.items() if c.upper().startswith(kk))
        for r in rows:
            for f in ("d_ps", "p_up_ps", "p_dn_ps", "unshared_a_ps", "unshared_b_ps"):
                r[f] *= k
    return o
L.cap_corner_rows = scaled
print("CAP from", L.CAP.__file__)
L.run_v3(plan, "qc", 334.0, out, [tuple(m.split("=", 1)) for m in sys.argv[4:]], (), 0.1, ("fish",), False, None,
         "334 ps/mm routed; count_align_plan @32e8cbb16; spice x1.0485 TT / x1.0552 FF")
