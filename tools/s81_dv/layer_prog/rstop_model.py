"""S81 ring stop edge model shared by the compiler, the cut replay and the token composer (FAM-S81-LEPE-4 XG-1).

ot_s81sl_rstop: line in pin -> line out pin RSTOP_HOP edges a stop.  A slice type bound with OT_S81SL_RSTOP_XMID1
(rstop XMID 1, main f67a57cea1) registers every stop input face once more: + RSTOP_XMID_EXTRA edges at that stop.
The bind stubs the C-layer stop, so LATCHECK never sees the edge; every timing consumer prices it here, per slice, from
the plan's partition_types verilog_defines, and fails closed when it cannot say which stops are XMID.
"""
import json
import os
import re
from pathlib import Path

RSTOP_HOP = 2
RSTOP_XMID_DEFINE = 'OT_S81SL_RSTOP_XMID1'
RSTOP_XMID_EXTRA = 1


def rstop_hop(die, inst, base=RSTOP_HOP):
    """edges of the ring stop of slice instance inst (u_s_<col><tier>): base, + RSTOP_XMID_EXTRA on an XMID 1 slice.
    die is anything with a rstop_xmid set (absent = no XMID stop)."""
    return base + (RSTOP_XMID_EXTRA if inst in getattr(die, 'rstop_xmid', ()) else 0)


def rstop_xmid_slices(plan):
    """slice instances whose partition type carries OT_S81SL_RSTOP_XMID1 (partition s_<col><tier>_<layer> ->
    u_s_<col><tier>).  A define on a partition that names no slice fails closed."""
    types = plan.get('partition_types') or {}
    out = set()
    for p in plan.get('partitions') or []:
        t = types.get(p.get('type'), {})
        if RSTOP_XMID_DEFINE not in (t.get('verilog_defines') or []):
            continue
        m = re.match(r'^(s_[0-7][NS])(_|$)', p['name'])
        if not m:
            raise ValueError(f'{RSTOP_XMID_DEFINE} on partition {p["name"]} (type {p.get("type")}) names no slice stop')
        out.add('u_' + m.group(1))
    return frozenset(out)


def bound_rstop_xmid(bound_dir, prov_plan, root, tree=None):
    """the bind's own plan (provenance_bind plan, relative to the bind tree) -> (xmid slices, plan path).
    OT_S81_RSTOP_XMID_PLAN overrides the path; an unresolved plan fails closed (the +1 must not slip past)."""
    env = os.environ.get('OT_S81_RSTOP_XMID_PLAN')
    cands = [Path(env)] if env else []
    if prov_plan and not env:
        rel = Path(prov_plan)
        cands += [rel] if rel.is_absolute() else [a / rel for a in Path(bound_dir).resolve().parents] + \
            ([Path(tree) / rel] if tree is not None else []) + [Path(root) / rel]
    for c in cands:
        if c.is_file():
            return rstop_xmid_slices(json.loads(c.read_text())), c
    raise ValueError(f'bound plan {prov_plan} not found for the rstop XMID model (set OT_S81_RSTOP_XMID_PLAN)')


def programme_rstop_xmid(manifest):
    """the XMID stops a compiled programme was scheduled with (dv_layer_compile manifest rstop_xmid).  A bound-data
    programme compiled before the model (no rstop_xmid key) fails closed: recompile it; a legacy (unbound) one has none."""
    if 'rstop_xmid' in manifest:
        return frozenset(manifest['rstop_xmid'])
    if manifest.get('bound_data'):
        raise ValueError('bound-data programme has no rstop_xmid record (compiled before the XMID stop model): recompile')
    return frozenset()


def leg_xmid_extra(xmid, links=7):
    """extra edges on ONE worst-case on-die leg end (farthest slice -> end slice, `links` ring links, each entering a
    stop): E-bound enters columns 8-links..7, W-bound 6..7-links; the worst tier and direction."""
    worst = 0
    for t in 'NS':
        for cols in (range(8 - links, 8), range(links - 1, -1, -1)):
            worst = max(worst, sum(1 for c in cols if f'u_s_{c}{t}' in xmid))
    return worst * RSTOP_XMID_EXTRA
