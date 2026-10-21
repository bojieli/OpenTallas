#!/usr/bin/env python3
"""Reticle W AND H check for HBM die grants.

OWNER 10-21 ~08:45 supersedes the 10-16 half-mm margin: release dies may
use the full 26 x 33 mm outline (858 mm2). The approximately0.1mm seal ring
is inside that outline; it is not a further inferred reticle exclusion.
Evidence: memory/owner-full-reticle-1021.md, confirmed by takeover owner.
An area-only check remains insufficient: both physical dimensions must fit.
Explicit callers can still request a larger margin for their own plan.
"""
RETICLE_UM = (33000.0, 26000.0)
MARGIN_UM = 0.0


def check_die(w, h, margin_um=MARGIN_UM):
    lo, sh = max(w, h), min(w, h)
    m_long, m_short = RETICLE_UM[0] - lo, RETICLE_UM[1] - sh
    return dict(die_um=[round(w, 3), round(h, 3)], long_margin_um=round(m_long, 3), short_margin_um=round(m_short, 3),
                margin_req_um=margin_um, ok=bool(m_long >= margin_um - 1e-6 and m_short >= margin_um - 1e-6))


def require_die(w, h, who='grant writer', margin_um=MARGIN_UM):
    r = check_die(w, h, margin_um)
    if not r['ok']:
        raise SystemExit(f'{who}: RETICLE FAIL {r} (need >= {margin_um} um margin in W AND H, reticle 33 x 26 mm)')
    return r


def require_contract(C, who='grant writer', margin_um=MARGIN_UM):
    die = next(s for s in C['slots'] if s.get('kind') == 'die')
    return require_die(die['outline']['w'], die['outline']['h'], who, margin_um)


if __name__ == '__main__':
    import json, sys
    C = json.load(open(sys.argv[1]))
    print(json.dumps(require_contract(C, sys.argv[1])))
