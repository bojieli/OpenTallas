"""Exact direct PF frame buses in the selected die top; no historical link aliasing."""
from __future__ import annotations
import re


def direct_frame_links(instances, text):
    """Recognize a whole 1104-bit frame xo->x wire and price its as-built wire as zero.

    Only direct source text connections qualify. The strict bind supplies its
    eventual transport age; this does not resurrect retired w_x_* station chains.
    """
    widths = {m[2]: int(m[0]) - int(m[1]) + 1 for m in re.findall(
        r'\bwire\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*(pf_xo_\w+)\s*;', text)}
    uses = {}
    for name, inst in instances.items():
        for port, expr in inst['conns'].items():
            for wire in set(re.findall(r'\bpf_xo_\w+\b', expr)):
                uses.setdefault(wire, []).append((name, port, expr.strip()))
    out = {}
    for wire, rows in sorted(uses.items()):
        if widths.get(wire) != 1104:
            raise ValueError('PF frame wire must declare the whole 1104-bit ABI: ' + wire)
        if len(rows) != 2 or any(expr != wire for _, _, expr in rows):
            raise ValueError('PF frame wire is not an exact two-endpoint whole-word connection: ' + wire)
        if re.search(r'\bassign\s+' + re.escape(wire) + r'\b', text):
            raise ValueError('PF frame wire has a separate assign driver: ' + wire)
        if any(not re.fullmatch(r'col_h(?:9|10)_l4_lp_asb_(?:x|nx)', instances[n]['master']) for n, _, _ in rows):
            raise ValueError('PF frame wire endpoint is not a selected native frame: ' + wire)
        src = [(n,p) for n,p,_ in rows if p == 'xo']
        dst = [(n,p) for n,p,_ in rows if p == 'x']
        if len(src) != 1 or len(dst) != 1 or src[0][0] == dst[0][0]:
            raise ValueError('PF frame wire needs one xo producer and one x consumer: ' + wire)
        out[wire] = dict(stations=0, landing=None, internal_landing=None, K=None, E=None,
                         src=src,dst=dst,age_edges=0,land_master=None,abutted=True,
                         direct_source_wire=wire,width=1104,source_identity='exact selected top whole-word xo->x')
    return out
