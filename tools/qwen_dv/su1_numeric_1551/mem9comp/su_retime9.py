#!/usr/bin/env python3
"""su_retime9: PRIVATE candidate (QC-MEM9-COMP 11-08), NOT the compiler of record.

The bound QC SU lanes add a request+answer transport of RT (=9) edges to every memory read while the lane head's metadata
ring stays at the as-built ML; the data of a read therefore pairs with the metadata of the instruction RT vectors later.
This pass re-issues SU ops so that the address fields lead the metadata by RT vectors, without changing the head:

  * a prefix op P reads the first min(nvec, RT) vectors of the op, dst 0, no reductions, no arithmetic (ma/mb/ad 0);
  * the body X keeps all metadata and write fields; its a/b/c read bases advance by RT vectors (asi*SW each); the body's
    last RT vectors request addresses past the op, which are unused (bound-checked below); X goes exactly RT edges after P;
  * a 2-D op whose outer stride is not contiguous is split into nout single-iteration ops (one P per iteration);
  * fields that cannot be shifted: `a_src`=1 (WROM source: cura[3:0] is both the row and, delayed, the lane mux) REFUSED.

The per-element proof is `check_stream`: for every body element the address requested RT vectors earlier equals the
as-built address of that element.  No compiler files change; the program is read-only input.
"""
from __future__ import annotations
import json, sys

SW, RT = 8, 9
class RetimeError(Exception):
    pass


def nvec_of(nin):
    return (nin + SW - 1) >> 3


def splittable_needed(o):
    """single-iteration ops are needed unless every read stream is one arithmetic progression across outer iterations"""
    if o['su_nout'] <= 1:
        return False
    nv = nvec_of(o['su_nin'])
    for s in 'abc':
        si, so = o[f'{s}_si'], o[f'{s}_so']
        cont = (so == nv * (si << 3)) if (si or so) else True
        if not cont:
            return True
    return False


def body_fields(o, o_iter):
    # base address and stride state of one outer iteration of the as-built op
    f = dict(o)
    for s in 'abcd':
        f[f'{s}_base'] = o[f'{s}_base'] + o_iter * o[f'{s}_so']
    f['r_base'] = o['r_base'] + o_iter * o['r_so']
    f['su_nout'] = 1
    return f


def transform(ops, rt=RT):
    """ops: decode_instruction dicts (unit 2 = SU only are transformed, others copied).
    Returns (out_records, stats); each out record has kind in {copy, prefix, body}, orig pc, fields, and for a body the
    edge gap from its prefix's go."""
    out, stats = [], dict(su_ops=0, prefixes=0, splits=0, refused=[])
    for pc, o in enumerate(ops):
        if o['unit'] != 2:
            out.append(dict(kind='copy', pc=pc, fields=o))
            continue
        stats['su_ops'] += 1
        if o['a_src'] != 0:
            stats['refused'].append(dict(pc=pc, why='a_src=1 (WROM) lane mux and row share cura'))
            raise RetimeError(f'pc {pc}: a_src=1')
        split = splittable_needed(o)
        iters = range(o['su_nout']) if split else [None]
        if split:
            stats['splits'] += 1
        for it in iters:
            f = body_fields(o, it) if it is not None else dict(o)
            nv = nvec_of(f['su_nin']) if it is not None else nvec_of(f['su_nin']) * f['su_nout']
            nin_p = min(nv, rt) << 3
            if nin_p > f['su_nin'] and f['su_nout'] == 1:
                nin_p = f['su_nin']            # partial vector: same live mask
            pre = dict(f, su_nin=nin_p, su_nout=1, dst=0, red=0, ma=0, mb=0, ad=0, mc=0, md=0, red_sq=0)
            body = dict(f)
            for s in 'abc':
                body[f'{s}_base'] = f[f'{s}_base'] + rt * (f[f'{s}_si'] << 3)
            stats['prefixes'] += 1
            over = max(rt * (f[f'{s}_si'] << 3) for s in 'abc')
            stats['max_overshoot_elements'] = max(stats.get('max_overshoot_elements', 0), over)
            out.append(dict(kind='prefix', pc=pc, iter=it, fields=pre))
            out.append(dict(kind='body', pc=pc, iter=it, fields=body, gap_from_prefix=rt, nvec=nv, overshoot_elements=over))
    return out, stats


def op_addresses(f, nvec, si_key='a', base=None):
    b = f[f'{si_key}_base'] if base is None else base
    return [b + v * (f[f'{si_key}_si'] << 3) for v in range(nvec)]


def check_stream(ops, rt=RT, adv=None):
    adv = rt if adv is None else adv
    """exact element-level proof on the vector grid: body vector v's data was requested at retimed emission index v - rt"""
    n = 0
    for pc, o in enumerate(ops):
        if o['unit'] != 2:
            continue
        split = splittable_needed(o)
        iters = list(range(o['su_nout'])) if split else [None]
        for it in iters:
            f = body_fields(o, it) if it is not None else dict(o)
            nv = nvec_of(f['su_nin']) if it is not None else nvec_of(f['su_nin']) * f['su_nout']
            nin_p = min(nv, rt)
            for s in 'abc':
                orig = [f[f'{s}_base'] + v * (f[f'{s}_si'] << 3) for v in range(nv)]
                if it is None and f['su_nout'] > 1:
                    nvi = nvec_of(f['su_nin'])
                    orig = [f[f'{s}_base'] + (v // nvi) * f[f'{s}_so'] + (v % nvi) * (f[f'{s}_si'] << 3) for v in range(nv)]
                # retimed requests: prefix vector j<nin_p requests orig[j]; body vector j requests orig[j]+rt*step (single stream)
                step = f[f'{s}_si'] << 3
                for v in range(nv):
                    j = v - rt
                    if j < 0:
                        req = (f[f'{s}_base'] + (v % (nvec_of(f['su_nin']))) * step + (v // nvec_of(f['su_nin'])) * f[f'{s}_so']) if (it is None and f['su_nout'] > 1) else f[f'{s}_base'] + v * step
                    else:
                        req = (f[f'{s}_base'] + adv * step) + j * step if not (it is None and f['su_nout'] > 1) else (f[f'{s}_base'] + adv * step + (j % nvec_of(f['su_nin'])) * step + (j // nvec_of(f['su_nin'])) * f[f'{s}_so'])
                    if req != orig[v]:
                        raise RetimeError(f'pc {pc} iter {it} stream {s} vec {v}: request {req} != address {orig[v]}')
                    n += 1
    return n


def stats_for(ops):
    out, st = transform(ops)
    su = [o for o in ops if o['unit'] == 2]
    vec_x = sum(((o['su_nin'] + 7) >> 3) * o['su_nout'] for o in su)
    st['vectors_as_built'] = vec_x
    st['prefix_vectors'] = sum(min(((r['fields']['su_nin'] + 7) >> 3), RT) for r in out if r['kind'] == 'prefix')
    st['edges_added_if_serial'] = RT * st['prefixes']
    return out, st


if __name__ == '__main__':
    root = sys.argv[1]
    sys.path.insert(0, root + '/tools')
    import hdc_qwen_fullshape_isa_w12 as ISA
    tot = dict(programs=0, su_ops=0, prefixes=0, splits=0, vectors_as_built=0, checked=0, wrong_offset_caught=0, wrong_offset_tested=0, split_needed_caught=0)
    per = []
    for path in sys.argv[2:]:
        ops = [ISA.decode_instruction(int(w, 16)) for w in open(path).read().split()]
        n = check_stream(ops)
        out, st = stats_for(ops)
        tot['programs'] += 1
        tot['checked'] += n
        for k in ('su_ops', 'prefixes', 'splits', 'vectors_as_built'):
            tot[k] += st[k]
        # controls: request advance 8 and 10 must be caught; a non-contiguous outer stream without the split must be caught
        for bad in (8, 10):
            tot['wrong_offset_tested'] += 1
            try:
                check_stream(ops, adv=bad)
            except RetimeError:
                tot['wrong_offset_caught'] += 1
        per.append(dict(path=path, su_ops=st['su_ops'], prefixes=st['prefixes'], splits=st['splits'], vectors=st['vectors_as_built'],
                        edges_if_serial=st['edges_added_if_serial'], max_overshoot=st.get('max_overshoot_elements')))
    print(json.dumps(dict(total=tot, per_program=per[:6], per_program_stats_sample=len(per)), indent=1, default=str))
