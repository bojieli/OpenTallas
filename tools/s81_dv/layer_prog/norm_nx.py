#!/usr/bin/env python3
"""TOK-DS-GAPS (10-24): arithmetic output words of the slice norm on a DATA cut -- the xfin NX flit (per-beat partial
sums of squares) of the norm-smoke slice, from the layer fixtures' INPUTS through the repository reference model.

Why: the data cuts (cut_0S / cut_0N / cut_7) replayed fault-free but the compiler encoded no output word on them (their
outputs were the off-die RD all-gather and the plan-only NX / XQ exchanges), so no data-cut replay was an exactness check.
The slice the compiler issues the attn norm on (lower_norm_smoke: HLOAD, GAIN, 5 x NORMR, XFIN_GO) emits ONE NX flit
per norm on its line / V faces; its payload is a pure function of the layer-entry state (H, GAIN, delayed pre):

  x   = BF16(seqsum_j pre[j] * h[j])                  hdc_golden_v41.Model.hc_pre (= fixture ops/<s>.hc_pre, asserted)
  p_k = csum(x[e:e+64] * x[e:e+64]),  e = 320 sid + 64 k   hdc_golden_v41.csum, R-ARITH chunk8 (fixture meta arith)
        (ot_s81dv_norm.sv header: each 64-lane beat is an aligned 8-chunk subtree of the golden csum, so the slice's
        ot_hbm_norm_grp produces exactly these per-beat partials; the 80 partials' padded tree = fixture <s>.norm.sumsq,
        asserted)

ABI of the flit (RTL of record, rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv + slice/ot_s81sl_rstop.sv):
  ot_s81dv_xfin collector: col[32 k +: 32] = leaf k partial; inj when leaf NVL-1 arrives; xstop injects the flit on eo
  (hops HE = NS / 2 = 8) and wo (hops HW = NS - 1 - NS / 2 = 7) on the same edge, base b = 5 sid.
  ot_s81sl_rstop nxb(): [0] 1, [3:1] K_NX 3, [8:4] {0, h}, [12:9] sid, [20:13] b, [21 +: 160] d; the snake-end side
  (map_e / map_w) leaves on V (vo = nxb[275:0]); the other on the physical line port (S tier: E port = eo, W port = wo;
  N tier: E port = wo, W port = eo).  A flit is ONE 276-b lane word (width 276): it is whole when lane 0 lands.

Layer-entry residency (the inputs): the entry H (4 BF16 HC copies, rows 0..31), the norm gains (rows 64..79) and the
delayed pre (row GU_FFN 1008) are written into the slice's 5 leaves by native XR CTL target-5 row writes (entry_inputs.py
packing, the production entry path of the first layer; for a later layer they model the state the previous layer left
in the leaf store).  They are emitted as CTL events BEFORE the layer (negative layer cycles, two edges apart, the
qualified target-5 cadence), not as calendar rows: the layer calendar / host boot are unchanged.  The replay drives
them on the cut's line input lanes like every other CTL beat (dv_cut_replay: payload186 events).

Edge: NX_AFTER_LAST_NORMR = edges from the last NORMR CTL event (the compiler's event cycle) to the slice's ro_e / vo
output register taking the flit.  MEASURED on the fc31 RTL (not a model): run_data L0 cut_0S (epyc3 tok-ds/fc31,
zero-data replay of the same calendar, t0 100): the flit landed on w_tvN_s_0S_lnd at bench 466 (lane age 4) and on
w_xrE_0S_l0_lnd at 477 (lane age 15) -> both = output edge 362 = NORMR k4 event 226 + 136.  The data-independent latency
is a pipeline constant (go_to_partial_normr 115 + leaf relay + xfin collector / xstop + rstop flops).
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]

NX_AFTER_LAST_NORMR = 136
NS, NVL, K_NX = 16, 5, 3
HE, HW = NS // 2, NS - 1 - NS // 2
ENTRY_CADENCE = 2          # target-5 CTL beats two edges apart (entry_boot.py: the qualified source cadence)
ENTRY_GUARD = 40           # last entry write -> first layer CTL beat of the tier (commit margin before HLOAD)
LANE = 276


def _golden():
    sys.path.insert(0, str(ROOT / 'tools'))
    import hdc_golden_v41 as V
    return V


def _arr(fixtures, rel):
    files = json.loads((Path(fixtures) / 'files.json').read_text())
    spec = files[rel]
    return np.fromfile(Path(fixtures) / rel, dtype=np.dtype(spec['dtype'])).reshape(spec['shape'])


def partials(fixtures, which='attn'):
    """the 80 per-beat partial sums of squares (FP32 bit patterns) of the layer's <which> norm input, from io/h_in +
    io/pre_in through the reference model; asserts the model reproduces the fixture's hc_pre and norm.sumsq"""
    fixtures = Path(fixtures)
    meta = json.loads((fixtures / 'meta.json').read_text())
    if meta.get('arith') != 'chunk8':
        raise ValueError(f'fixture arith {meta.get("arith")!r}: the slice partial ABI is the chunk8 csum subtree')
    if which != 'attn':
        raise ValueError('only the attn norm input is a pure function of the layer-entry state (ffn: attn outputs)')
    V = _golden()
    old = V.ARITH
    V.set_arith('chunk8')
    try:
        F = np.float32
        h = _arr(fixtures, 'io/h_in.bin').astype(F)
        pre = _arr(fixtures, 'io/pre_in.bin').astype(F)
        x = V.to_bf16(V.seqsum([V.mul(pre[j], h[j]) for j in range(4)]))
        ref = _arr(fixtures, f'ops/{which}.hc_pre.bin').astype(F)
        if not np.array_equal(np.asarray(x, F).view(np.uint32), ref.view(np.uint32)):
            raise ValueError(f'reference hc_pre differs from fixture ops/{which}.hc_pre (model / fixture mismatch)')
        sq = V.mul(x, x)
        p = [F(V.csum(sq[64 * v:64 * v + 64])) for v in range(NS * NVL)]
        tot = F(V.split_sum_parts(p))
        ss = _arr(fixtures, f'ops/{which}.norm.sumsq.bin').astype(F)
        if np.asarray(tot, F).view(np.uint32) != ss.view(np.uint32)[0]:
            raise ValueError(f'partial tree {tot} != fixture {which}.norm.sumsq {ss[0]}')
        return [int(np.asarray(v, F).view(np.uint32)) for v in p]
    finally:
        V.set_arith(old)


def nxb(sid, hops, data160):
    """ot_s81sl_rstop nxb(): the line / V word of an xfin flit"""
    return 1 | K_NX << 1 | (hops & 0xF) << 4 | (sid & 0xF) << 9 | ((NVL * sid) & 0xFF) << 13 | data160 << 21


def flit_ports(sid):
    """slice port -> hops of the flit it carries (ot_s81sl_rstop map_e / map_w, tier E / W port roles)"""
    col, tier = sid >> 1, sid & 1
    map_e = col == 0 if tier else col == 7
    map_w = col == 7 if tier else col == 0
    out = {}
    if map_e:
        out['vo'] = HE
    elif map_w:
        out['vo'] = HW
    # physical E port: S tier eo, N tier wo; W port the other
    e_side, w_side = (('wo', 'eo') if tier else ('eo', 'wo'))
    for port, side in (('ro_e', e_side), ('ro_w', w_side)):
        mapped = map_e if side == 'eo' else map_w
        if not mapped:
            out[port] = HE if side == 'eo' else HW
    return out


def entry_writes(die, fixtures, sid):
    """the slice's layer-entry target-5 rows (entry_inputs.compile_inputs packing, hash-checked inputs)"""
    sys.path.insert(0, str(Path(__file__).parent))
    from entry_inputs import compile_inputs
    img = compile_inputs(die, fixtures)
    return [w for w in img['writes'] if w['sid'] == sid], img['input_sources']


def emit(die, prog, smoke, fixtures, ctl_cycles):
    """entry-state CTL events + the NX flit output words for the norm-smoke slice; replaces the plan-only NX event.
    ctl_cycles = every CTL event cycle already on the smoke slice's tier (the entry writes end ENTRY_GUARD before them).
    Negative control: dv_cut_replay --mutant corrupt:<line lane>:<bit> flips a bit of the first entry write."""
    sl, sid = smoke['slice'], smoke['sid']
    p = partials(fixtures)
    mine = p[NVL * sid:NVL * sid + NVL]
    data = sum(v << (32 * k) for k, v in enumerate(mine))
    writes, sources = entry_writes(die, fixtures, sid)
    port = smoke['ctl_latency']['entry_port']
    last = min(ctl_cycles) - ENTRY_GUARD
    n = len(writes)
    evs = []
    for i, w in enumerate(writes):
        pl = int(w['ctl_payload186'], 16)
        evs.append(dict(cycle=last - ENTRY_CADENCE * (n - 1 - i), inst=sl, port=port, dir='in', kind='CTL',
                        tag=f"entry.{w['region']}.leaf{w['leaf']}.row{w['row']}", payload=f'entry {pl:047x}',
                        payload186=f'{pl:047x}', entry_state=True))
    go_last = max(e['cycle'] for e in prog.events if e.get('inst') == sl and e['kind'] == 'CTL'
                  and str(e.get('tag', '')).startswith('attn.NORMR.k'))
    edge = go_last + NX_AFTER_LAST_NORMR
    prog.events[:] = [e for e in prog.events if not (e.get('inst') == sl and e.get('kind') == 'NX'
                                                       and e.get('tag') == 'attn.partial_roots')]
    for pt, hops in sorted(flit_ports(sid).items()):
        v = nxb(sid, hops, data)
        prog.events.append(dict(cycle=edge, inst=sl, port=pt, ports=[pt], dir='out', kind='NX', tag='attn.partial_roots',
                                width=LANE, valid_bit=0, words=[[edge, f'{v:x}', f'{(1 << LANE) - 1:x}']],
                                payload=f'xfin NX flit sid {sid} hops {hops}: partials ' +
                                        ' '.join(f'{x:08x}' for x in mine),
                                source='hdc_golden_v41 chunk8 csum of BF16(hc_pre(io/h_in, io/pre_in))^2 per 64-beat'))
    prog.events.extend(evs)
    return dict(slice=sl, sid=sid, entry_writes=n, entry_first=evs[0]['cycle'], entry_last=evs[-1]['cycle'],
                entry_sources=sources, nx_edge=edge, nx_after_last_normr=NX_AFTER_LAST_NORMR,
                nx_ports=flit_ports(sid), partials=[f'{x:08x}' for x in mine],
                qualification='NX flit = arithmetic output word of the slice norm (hc_pre mix, square, chunk8 beat '
                              'sums) from layer-entry inputs; rstd / XQ need the 16-slice composition (not compiled)')


if __name__ == '__main__':
    fx = sys.argv[1]
    p = partials(fx)
    print(json.dumps(dict(partials=[f'{x:08x}' for x in p])))
