"""QC embedding + RoPE row read at the bound transport (QC-TRANSPORT-FIX 11-08).

qfd_native59_svc_obs1 reads the embedding row with a fixed tag ring (e1/e2/e3) that assumes the provider answers at the
pin.  At the bound die the read request and the answer cross the glue <-> native59 lanes, so the words are late by the
landed round trip.  This hook derives the two RTL parameters from the plan of record (depths from the binder, including
landing pads) and returns them for coll_regen:

  EMB_RT_CODE  = landed depth(embed_prov.embed_code_re) + landed depth(native59.emb_code_q)
  EMB_RT_SCALE = landed depth(embed_prov.embed_scale_re) + landed depth(native59.emb_scale_q)

An address may land earlier than its read enable (the flops hold it) but never later, or the read tears.  Every bit of a
port must land at one depth; no number is hand-written here, so a plan change regenerates both values.
"""

NATIVE = 'native59'
PROVIDER = 'embed_prov'


def _one(ctx, path, port):
    depths = set(ctx.depth(path, port).values())
    if len(depths) != 1:
        raise ValueError(f'embed transport: {path}.{port} lands at depths {sorted(depths)} (one depth per port required)')
    return depths.pop()


def derive(ctx):
    """landed depths of the six embedding crossings and the derived RTL parameters"""
    d = dict(code_re=_one(ctx, PROVIDER, 'embed_code_re'), code_addr=_one(ctx, PROVIDER, 'embed_code_addr'),
             code_q=_one(ctx, NATIVE, 'emb_code_q'), scale_re=_one(ctx, PROVIDER, 'embed_scale_re'),
             scale_addr=_one(ctx, PROVIDER, 'embed_scale_addr'), scale_q=_one(ctx, NATIVE, 'emb_scale_q'))
    if d['code_addr'] > d['code_re'] or d['scale_addr'] > d['scale_re']:
        raise ValueError(f'embed transport: an address lands later than its read enable (read tear): {d}')
    d['EMB_RT_CODE'] = d['code_re'] + d['code_q']
    d['EMB_RT_SCALE'] = d['scale_re'] + d['scale_q']
    return d


def regen(ctx):
    d = derive(ctx)
    return ({NATIVE: dict(EMB_RT_CODE=d['EMB_RT_CODE'], EMB_RT_SCALE=d['EMB_RT_SCALE'])},
            dict(rule='EMB_RT_CODE/SCALE = landed re + q of the embedding read (qfd_native59 tag ring, QC-TRANSPORT-FIX)',
                 depths=d, dr_o_added_edges=d['EMB_RT_CODE'],
                 dependent='compiler: the group-1 (embedding/RoPE) dr words leave native59 EMB_RT_CODE edges later than '
                           'the zero-transport ring; the embedding landing windows and ROPE ARM must use t0 + EMB_RT_CODE'))
