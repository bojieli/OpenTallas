#!/usr/bin/env python3
"""Opt-in, serialized FUSED operand materialization for preserved P3 images.

Insert real DMA.LOAD / SU bypass records; preserve original payload addresses
with copies before/after the native FUSED operation. No pointer-only repair.
Temporary storage is chosen from words dead in the original image, with all
in-flight original operations drained before materialization. This is a compiler
candidate, not a native replay or an 8-SM timing qualification.
"""
from __future__ import annotations
import argparse, copy, json, math
from pathlib import Path
import numpy as np
import image_check as IC
import isa_rows as IR
from hgi_sim import records as RC
import hbm_generic_iface as HGI

LIMIT = 1 << 19
WAIT = (1 << len(HGI.D_UNITS)) - 1


def extents(r, rx, k):
    d = r.desc[k]
    if d.space != 'VM': return []
    rows = rx.n if rx else 1
    stride = rx.rs.get(k, 0) if rx else 0
    # Selector tables can name any of the statically reserved expert slots.
    if rx and rx.rsel and ((rx.emask >> IR.OPND.index(k)) & 1):
        rows = getattr(r, "_selector_rows", None)
        if rows is None: raise ValueError("RSEL output without actual UNION slot bound")
    span = d.n if d.m <= 1 else (d.m - 1) * d.stride + d.n
    if d.indexed:
        bound = getattr(r, '_index_bound', None)
        if bound is None: raise ValueError('indexed VM read without live TOPK producer bound')
        span += (bound - 1) * d.dyn_mul
    if d.n_sel or d.dyn_sel or d.lstride or d.l1stride:
        raise ValueError(f'dynamic VM operand {r.unit}.{r.op}.{k} needs a source-qualified bound')
    return [(d.base + row * stride, d.base + row * stride + span) for row in range(rows)]


def mark(mask, ranges, value=True):
    for lo, hi in ranges:
        if lo < 0 or hi > LIMIT: raise ValueError(f'VM interval [{lo},{hi}) outside capacity')
        mask[lo:hi] = value


def writes(r, k):
    return k in ('O', 'R') or (k == 'D' and r.unit == 'IDX' and r.op == 'INDEX' and (r.param >> 12) & 1)


def repair_rid_tables(recs, base):
    """Materialize TOPK ids before storage reuse; bind UNION / indexed users.

    The preserved multi-row image incorrectly names a different allocation in
    UNION.A and the per-position gather I. A real bypass copy pins the actual
    emitted TOPK output, with all units drained before its storage can be reused.
    """
    out=[]; aliases=[]; fixes=[]
    for off,r,rx,raw in recs:
        rr=copy.deepcopy(r); xx=copy.deepcopy(rx)
        if rr.unit=='IDX' and rr.op=='UNION':
            old=rr.desc['A']; aliases.append((old.base,old.stride,old.m,old.n))
            rr.desc['A'].base=base; rr.desc['A'].stride=8; rr.wait=WAIT
            fixes.append({'offset':off,'consumer':'UNION.A','old':old.base,'new':base})
        if 'I' in rr.desc and rr.desc['I'].space=='VM':
            d=rr.desc['I']
            for old,stride,rows,n in reversed(aliases):
                row,inner=divmod(d.base-old,stride or 8)
                if 0<=row<rows and 0<=inner<n:
                    fixes.append({'offset':off,'consumer':'I','old':d.base,'new':base+row*8+inner})
                    d.base=base+row*8+inner; rr.wait=WAIT
                    if xx and 'I' in xx.rs: xx.rs['I']=8
                    break
        out.append((off,rr,xx,IR.encode(rr,xx)))
        if rr.unit=='IDX' and rr.op=='TOPK':
            aliases=[(rr.desc['O'].base,xx.rs.get('O',0) if xx else 0,xx.n if xx else 1,rr.desc['O'].n)]
            target=copy.copy(rr.desc['O']);target.base=base
            cp=copy_rec(rr.desc['O'],target,'pin actual TOPK ids')
            cx=IR.RowX(n=xx.n,rs={'A':xx.rs.get('O',0),'O':8}) if xx else None
            out.append((None,cp,cx,IR.encode(cp,cx)))
    return out,fixes


def live_at_fused(recs):
    """Conservative backward read-before-write liveness; loop writes never kill.

    Unknown dynamic VM extents are refused, never guessed. FUSED operators occur
    outside expert loops; their output becomes live only after it is materialized.
    """
    # Derive indexed score-gather ranges from their actual TOPK id producer.
    tables = {}; selector_tables = {}
    for _, r, rx, _ in recs:
        if rx and rx.rsel and rx.emask:
            if rx.rtab not in selector_tables: raise ValueError("RSEL has no preceding UNION producer")
            r._selector_rows = rx.n * selector_tables[rx.rtab]
        if r.unit == "IDX" and r.op == "UNION":
            selector_tables[r.desc["R"].base] = r.imm_b
        for k, d in r.desc.items():
            if d.space == 'VM' and d.indexed:
                source = r.desc.get('I')
                hits = [bound for lo, hi, bound in tables.values() if source is not None and lo <= source.base < hi]
                if len(hits) != 1: raise ValueError(f'indexed VM operand {r.unit}.{r.op} I={source} has no unique live TOPK producer; tables={tables}')
                r._index_bound = hits[0]
        copy_bound = None
        if r.unit == 'SU' and r.op == 'VOP' and r.sut and r.sut.get('dst') == 1 and set(r.desc)=={'A','O'} and all(not v for k,v in r.sut.items() if k!='dst'):
            a=r.desc['A']; hits=[bound for lo,hi,bound in tables.values() if lo<=a.base<hi]
            if len(hits)==1: copy_bound=hits[0]
        for k in r.desc:
            if writes(r, k):
                for lo, hi in extents(r, rx, k):
                    tables = {key:val for key,val in tables.items() if not (lo < val[1] and val[0] < hi)}
        if r.unit == 'IDX' and r.op in ('TOPK', 'UNION'):
            bound = r.desc['A'].n if r.op == 'TOPK' else r.imm_a
            for lo,hi in extents(r,rx,'O'): tables[lo] = (lo,hi,bound)
        elif copy_bound is not None:
            for lo,hi in extents(r,rx,'O'): tables[lo]=(lo,hi,copy_bound)
    inside = []; depth = 0
    for _, r, _, _ in recs:
        inside.append(depth > 0)
        if r.unit == 'CTL' and r.op == 'LOOP': depth += 1
        if r.unit == 'CTL' and r.op == 'ENDLOOP': depth -= 1
    live = np.zeros(LIMIT, dtype=bool); result = {}
    for ix in range(len(recs) - 1, -1, -1):
        _, r, rx, _ = recs[ix]
        if r.unit == 'FUSED' and r.op in ('HC_PRE_NORM', 'HC_POST'):
            if inside[ix]: raise ValueError('FUSED inside selector loop is unsupported')
            result[ix] = live.copy()
        for k in r.desc:
            if writes(r, k) and not inside[ix] and r.pred == "ALWAYS": mark(live, extents(r, rx, k), False)
        for k in r.desc:
            if not writes(r, k): mark(live, extents(r, rx, k))
        if r.unit == 'CTL' and r.op == 'LOOP' and r.param & (1 << 17):
            mark(live, [(r.imm_a, r.imm_a + 1)])
        if rx and rx.rsel: mark(live, [(rx.rtab, rx.rtab + 32 * 6 * rx.n)])
    return result


def allocate(forbidden, words, phase=0, alignment=256):
    for base in range(phase * 8, LIMIT - words + 1, alignment):
        if not forbidden[base:base + words].any():
            forbidden[base:base + words] = True
            return base
    raise ValueError(f'no {words}-word materialization buffer at phase {phase}')


def copy_rec(src, dst, tag):
    if src.space == 'HBM':
        return RC.Rec('DMA', 'LOAD', wait=WAIT, desc={'A': copy.copy(src), 'O': copy.copy(dst)}, tag=tag)
    if src.space != 'VM' or dst.space != 'VM': raise ValueError('copy operand space')
    if src.fmt != dst.fmt: raise ValueError('bit-preserving copy cannot change format')
    sut = {name: 0 for name, _, _ in HGI.D_SUT_LAYOUT}
    sut['dst'] = 1  # all arithmetic/rounding stages bypassed, FP32 VM bits preserved
    return RC.Rec('SU', 'VOP', wait=WAIT, sut=sut,
                  desc={'A': copy.copy(src), 'O': copy.copy(dst)}, tag=tag)


def lower_one(r, rx, live):
    from fused_phase_check import check_fused
    if rx and (rx.rsel or rx.rpl): raise ValueError('FUSED selector/remainder mode unsupported')
    original_rows = [rr for _, rr in IR.expand(r, rx)]
    forbidden = live.copy()
    # Original output storage may be borrowed until its new value is published.
    mark(forbidden, extents(r, rx, 'O'), False)
    for k in r.desc:
        if k != 'O': mark(forbidden, extents(r, rx, k))
    emitted, ledger = [], []
    for row, original in enumerate(original_rows):
        f = forbidden.copy(); native = copy.deepcopy(original); native.wait = WAIT
        pending = []; rowlog = {'row': row, 'buffers': {}, 'vm_copy_words': 0, 'hbm_load_words': 0}
        for k in 'ABCO':
            d = original.desc[k]
            align = 8 if k == 'C' else 256
            words = d.n if d.m <= 1 else (d.m - 1) * d.stride + d.n
            base = allocate(f, words, alignment=align)
            target = copy.copy(d); target.space = 'VM'; target.base = base
            target.lstride = target.l1stride = target.dyn_sel = target.dyn_mul = target.n_sel = target.indexed = 0
            native.desc[k] = target
            rowlog['buffers'][k] = {'base': base, 'words': words, 'original_base': d.base, 'source_space': d.space}
            if k != 'O':
                emitted.append((copy_rec(d, target, f'FUSED {r.op} row{row} materialize {k}'), None))
                rowlog['hbm_load_words' if d.space == 'HBM' else 'vm_copy_words'] += words
            else:
                pending.append((copy_rec(target, d, f'FUSED {r.op} row{row} publish O'), None))
                rowlog['vm_copy_words'] += words
        assert not check_fused(native, None)
        emitted.append((native, None)); emitted.extend(pending)
        mark(forbidden, extents(original, None, 'O'))
        ledger.append(rowlog)
    return emitted, ledger


def lower_dir(source, output):
    meta, image, recs, oldviol, _ = IC.run_dir(source)
    original_bytes=len(image)
    rid_base=math.ceil(meta['token']['vm_need_words']/256)*256
    if rid_base+8*meta['N']>LIMIT: raise ValueError('no VM capacity for source-qualified ID table')
    recs,rid_fixes=repair_rid_tables(recs,rid_base)
    live = live_at_fused(recs)
    out = bytearray(); offset_map = {}; ledger = []; publish_pending=False
    for ix, (off, r, rx, raw) in enumerate(recs):
        if off is not None: offset_map[off] = len(out)
        if publish_pending:
            r=copy.deepcopy(r);r.wait=WAIT;raw=IR.encode(r,rx);publish_pending=False
        if ix in live:
            lowered, rows = lower_one(r, rx, live[ix]); begin = len(out)
            for rr, xx in lowered: out.extend(IR.encode(rr, xx))
            publish_pending=True
            ledger.append({'original_offset': off, 'offset': begin, 'op':r.op, 'original_rows':rx.n if rx else 1,
                           'new_records':len(lowered), 'rows':rows})
        else: out.extend(raw)
    offset_map[len(image)] = len(out)
    result = copy.deepcopy(meta)
    for segment in result['token']['segments']:
        oldoff, oldend = segment['offset'], segment['offset'] + segment['bytes']
        segment['offset'] = offset_map[oldoff]; segment['bytes'] = offset_map[oldend] - offset_map[oldoff]
    result['token']['bytes'] = len(out)
    result['token']['vm_need_words']=max(result['token']['vm_need_words'],rid_base+8*meta['N'])
    result['fused_materialization'] = {'source':str(source), 'native_execution':False, 'scheduling':'all-unit drain before each inserted record; row serialization',
        'records':ledger, 'rid_materialization':{'base':rid_base,'words':8*meta['N'],'consumers_fixed':rid_fixes}, 'cost_status':'NOT_PRICED; copy/DMA traffic and lost overlap must be charged before adoption',
        'vm_copy_words':sum(x['vm_copy_words'] for l in ledger for x in l['rows']),
        'hbm_load_words':sum(x['hbm_load_words'] for l in ledger for x in l['rows'])}
    output.mkdir(parents=True,exist_ok=True)
    (output/result['token']['image']).write_bytes(out)
    (output/'emitter.json').write_text(json.dumps(result,indent=1)+'\n')
    _,_,decoded,viol,loops = IC.run_dir(output)
    summary={'source':str(source),'records':len(decoded),'before_violations':len(oldviol),'after_violations':viol,
             'I1_I7_PASS':not viol, 'materialized_fused':len(ledger),
             'vm_copy_words':result['fused_materialization']['vm_copy_words'],
             'hbm_load_words':result['fused_materialization']['hbm_load_words'], 'native_execution':False}
    (output/'lower_check.json').write_text(json.dumps(summary,indent=1)+'\n')
    return summary


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source',type=Path);ap.add_argument('output',type=Path)
    a=ap.parse_args();print(json.dumps(lower_dir(a.source,a.output)))
if __name__=='__main__':main()
