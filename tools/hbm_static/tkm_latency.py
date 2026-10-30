"""Explicit TKM done/stat-cycle offsets from ot_hgi_coll_tkm_static_p.

This helper changes no compiler default. Its zero-argument profile is PIPE0.
Use exact selected parameters and separately measured external face ages.
It gives offsets, not total operator cost or accepted-token throughput.
"""
from __future__ import annotations


def done_offsets(*, kmax=2048, pipe=0, hop=0, frt=0, cb=0, clrb=None,
                 external_input=0, external_output=0):
    """Done/stat offsets relative to the same bare PIPE0 operator calendar.

    Matches static_p's SETTLE, XL and delayed-clear equations. External faces
    are separate from stat_cycles and require their own source measurement.
    Individual intermediate write dates are not inferred for general CLRB.
    """
    if clrb is None:
        clrb = cb
    values = dict(kmax=kmax, pipe=pipe, hop=hop, frt=frt, cb=cb, clrb=clrb,
                  external_input=external_input, external_output=external_output)
    for name, value in values.items():
        if type(value) is not int or value < 0:
            raise ValueError(f'{name} must be a nonnegative integer')
    if not 1 <= kmax <= 2048 or pipe not in (0, 1):
        raise ValueError('requires KMAX 1..2048 and PIPE 0/1')
    tiles = (kmax + 63) // 64
    bare_settle = 3 * tiles + 8
    settle = (3 + hop) * (tiles - 1) + 11 - cb
    if settle < 0:
        raise ValueError('negative SETTLE does not define a supported calendar')
    stream_age = frt + cb + hop * (tiles - 1)
    body = 2 * pipe + 2 * (settle - bare_settle) + 2 * stream_age + 2 * clrb
    return dict(parameters=values, tiles=tiles, bare_settle=bare_settle,
                settle=settle, stream_age=stream_age,
                stat_done_offset_vs_pipe0=body,
                external_done_offset_vs_pipe0=body + external_input + external_output)
