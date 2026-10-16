"""Opt-in zero-cycle KV11 G/FT/T2 placement candidates; no physical claim.

The selected source plan preserves the existing two-row band and every actual
leaf. Full actual-net/LEF/DEF evidence is in qwen_gft_geometry_0253/all32.
Default remains unchanged. A die GEN/route requires the lead's model review.
"""
import os

PLANS = {
    'balanced_394.2': dict(gx=394.2, tx=43.2, sx=745.2, needs_reset_reallocation=True),
    'balanced_405.864': dict(gx=405.864, tx=54.864, sx=756.864, needs_reset_reallocation=False),
    'balanced_409.32': dict(gx=409.32, tx=58.32, sx=760.32, needs_reset_reallocation=False),
}


def selected():
    name=os.environ.get('OT_KV_GFT_GEOMETRY','')
    if not name:return None
    if name not in PLANS:raise ValueError(f'unknown OT_KV_GFT_GEOMETRY={name!r}')
    p=dict(PLANS[name],name=name,ftg=(356.4,189.54),fts=(685.8,191.7))
    if p['needs_reset_reallocation']:
        raise ValueError('balanced_394.2 is review-only: 15 actual reset-relay clearances need reallocation')
    return p
