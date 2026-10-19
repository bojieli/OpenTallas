#!/usr/bin/env python3
"""HBM-CHAIN3 10-18 (coordinator 0hk, HBM-IDXAM3 09:53 note): contract post-layer L8 -- the uniform n+12 IDX operand reader.

    l8_idx_n12.py IN_contract.json[.gz] OUT_contract.json --report R.json

(a) hb_idx__op_{SW,SE,NW,NE}  ot_hbm_idx_vm_query_static -> ot_hbm_idx_vm_query_static_n12 (CLOSED hidx_op_n12_1018-n12-7bfb8c78c,
    view physical/ref_tile/hidx_op_n12_1018; port-identical: same ports / widths / pins / outline as the n+10 shell).  The core's VM
    face captures at n+12: the round trip carries the shell's two pin flops plus TWO fixed edges outside the tile.
(b) The two outside edges = ONE die relay stage on vm_rq and ONE on vm_rr (closed hbfd_rly classes, plain fixed-latency register,
    no flow control) on EVERY quadrant of this netlist.  The 09:53 note puts them on SE/NE/NW only because SW was to get its +1/+1
    from the registered share ot_hbm_idx_vm_share_static_amr inside hb_idx__ctl r3 (ot_hbm_idx_rootctl_static_am); that master is
    NOT closed and NOT bound here (hb_idx__ctl = ot_hbm_idx_rootctl_static, whose ot_hbm_idx_vm_share_static index face is a zero-
    latency pass-through, as hb_idx__nwsh share2 on NW).  So SW takes the same 1+1 relays; when hb_idx__ctl is rebound to the
    registered share, drop SW's relays (and NW's when nwsh gets its registered face).  Exactly 1+1: tb_vm_query_n12 MUT4/5/7.
    vm_rq 136 b -> hbfd_rly_136 (the SE/NE 8 x 17-b bank slices fan out of its o); vm_rr 2,056 b -> hbfd_rly_1136 + 624 + 304 side by
    side (2,064 b, spare i 2,056..2,063 tied low, o open: the relay class PAD rule of l3's U-ring relay).  Every existing edge keeps
    its far end and its slice; only the op end moves to the relay (edges that straddle a relay-class boundary are split).
Clocks  relay ck = stream (hb_ckgen.pll_stream), rs = hb_ckgen.por_stream (the reset hb_idx__op_<q> uses).
Compiler tools/hbm_idx_static_calendar.py PIN 'registered' vm_rt 2 -> 4 (operand blocks reach idx_q 2 edges later on all quads).
Pure-python; asserts no op VM bit is left on a direct edge and no sink bit is double-driven.
"""
import argparse, collections, json, sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import l3_vm_hc_coll as L3M  # noqa: E402

REGION = 'd4g_gen2_l8_idx_n12'
L3M.REGION = REGION
Q = ('SW', 'SE', 'NW', 'NE')
OLD, NEW = 'ot_hbm_idx_vm_query_static', 'ot_hbm_idx_vm_query_static_n12'
RQ_W, RR_W = 136, 2056
RR_CLASSES = (1136, 624, 304)
# flow of the relay tiles (pin faces only; the die flow places relay chains between their placed ends)
FLOW = dict(SW=('WE', 'EW'), NW=('WE', 'EW'), SE=('EW', 'WE'), NE=('EW', 'WE'))
OWN = 'HBM-IDXAM3 n+12 operand reader (0hk), bound by HBM-CHAIN3 GEN2'


class L8(L3M.L3):
    def edge(self, src, snk, basis, clock='stream', name=None):
        super().edge(src, snk, basis, clock)
        self.E[-1]['name'] = name or f'l8_{self.n:05d}'


def run(c, rep):
    R = L3M.Rtl()
    l8 = L8(c, R)
    I, E = l8.I, l8.E
    for q in Q:
        op = f'hb_idx__op_{q}'
        assert I[op]['master'] == OLD, (op, I[op]['master'])
        old = {p: (d['direction'], d['bits']) for p, d in I[op]['ports'].items()}
        l8.remaster(op, NEW, {}, 'uniform n+12 operand reader (0hk); VM face round trip +2 = 1 relay on vm_rq + 1 on vm_rr')
        new = {p: (d['direction'], d['bits']) for p, d in I[op]['ports'].items()}
        assert old == new, (op, old, new)
        assert new['vm_rq'] == ('output', RQ_W) and new['vm_rr'] == ('input', RR_W), new
    rep['relays'] = {}
    for q in Q:
        op = f'hb_idx__op_{q}'; frq, frr = FLOW[q]
        slot = I[op].get('slot')
        rq = f'hidxr_{q}_rq'
        l8.inst(rq, f'hbfd_rly_{RQ_W}_{frq}', {}, slot, f'IDX {q} operand reader vm_rq: ONE fixed die relay stage (n+12 VM face, 0hk; '
                f'flow {frq})', OWN)
        rr = [f'hidxr_{q}_rr{j}' for j in range(len(RR_CLASSES))]
        for j, wcl in enumerate(RR_CLASSES):
            l8.inst(rr[j], f'hbfd_rly_{wcl}_{frr}', {}, slot, f'IDX {q} operand reader vm_rr bits {sum(RR_CLASSES[:j])}..'
                    f'{min(sum(RR_CLASSES[:j + 1]), RR_W) - 1}: ONE fixed die relay stage (n+12 VM face, 0hk; flow {frr})', OWN)
        for rn in [rq] + rr:
            l8.clock(rn, 'ck')
            l8.clock(rn, 'rs', 'reset')
        # re-source the op end of every existing VM edge
        moved = collections.Counter(); new_edges = []
        for e in E:
            s, t = e['source'], e['sink']
            if s[0] == op and s[1] == 'vm_rq':
                e['source'] = [rq, 'o', s[2], s[3]]; moved['rq_bits'] += s[3] - s[2]
                e['basis'] = (e.get('basis') or '') + f' | {REGION}: op end through the vm_rq relay {rq}'; e['region'] = REGION
            elif t[0] == op and t[1] == 'vm_rr':
                lo, hi = t[2], t[3]; base = 0; parts = []
                for j, wcl in enumerate(RR_CLASSES):
                    a_, b_ = max(lo, base), min(hi, base + wcl)
                    if a_ < b_:
                        parts.append((j, a_, b_, base))
                    base += wcl
                first = True
                for j, a_, b_, b0 in parts:
                    so = s[2] + (a_ - lo)
                    seg = dict(e, source=[s[0], s[1], so, so + b_ - a_], sink=[rr[j], 'i', a_ - b0, b_ - b0], bits=b_ - a_,
                               basis=(e.get('basis') or '') + f' | {REGION}: op end through the vm_rr relay {rr[j]}', region=REGION)
                    if not first:
                        seg['name'] = e['name'] + f'_s{j}'
                    new_edges.append((e, seg, first)); first = False
                moved['rr_bits'] += hi - lo
        for e, seg, first in new_edges:
            if first:
                e.clear(); e.update(seg)
            else:
                E.append(seg)
        assert moved == {'rq_bits': RQ_W, 'rr_bits': RR_W}, (q, dict(moved))
        l8.edge([op, 'vm_rq', 0, RQ_W], [rq, 'i', 0, RQ_W], f'{OWN}: vm_rq -> its die relay stage')
        base = 0
        for j, wcl in enumerate(RR_CLASSES):
            use = min(wcl, RR_W - base)
            l8.edge([rr[j], 'o', 0, use], [op, 'vm_rr', base, base + use], f'{OWN}: vm_rr die relay stage -> operand reader')
            if use < wcl:
                l8.ST.append(dict(inst=rr[j], port='i', lo=use, hi=wcl, value=0, master=I[rr[j]]['master'],
                                  reason=f'PAD (DEDUPE standard relay hbfd_rly_{wcl}, logical width {use}, spare bits {use}..{wcl - 1} '
                                         'tied low; outputs open) -- relay class rule, ot_hbm_rly.sv'))
            base += wcl
        rep['relays'][q] = dict(rq=rq, rr=rr, flow=dict(rq=frq, rr=frr), classes=dict(rq=RQ_W, rr=list(RR_CLASSES)))
    # no sink bit driven twice
    drv = collections.defaultdict(int)
    for e in E:
        t = e['sink']
        for b in range(t[2], t[3]):
            drv[(t[0], t[1], b)] += 1
    dup = [k for k, v in drv.items() if v > 1 and k[0].startswith(('hidxr_', 'hb_idx__op_'))]
    assert not dup, dup[:5]
    rep['remaster'] = {f'hb_idx__op_{q}': dict(old=OLD, new=NEW, view='physical/ref_tile/hidx_op_n12_1018',
                                               closure='hidx_op_n12_1018-n12-7bfb8c78c') for q in Q}
    rep['why_sw_too'] = ('hb_idx__ctl is ot_hbm_idx_rootctl_static (share = zero-latency pass-through) in this netlist; the registered '
                         'share (rootctl_static_am r3/r4) is not closed / not bound -> SW needs the same 1+1 relays as SE/NW/NE')
    rep['compiler'] = 'tools/hbm_idx_static_calendar.py PIN registered vm_rt 2 -> 4'
    notes = c.get('notes'); c['notes'] = {}
    ex, bad = l8.finish()
    nl = c['notes']
    c['notes'] = notes + [dict(region=k, note=v) for k, v in nl.items()] if isinstance(notes, list) else dict(notes or {}, **nl)
    rep.update(log=dict(l8.log), exposed_inputs=ex, unlisted_exposed=bad, summary=c['summary'])
    return ex, bad, l8


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = L3M.ld(a.inp)
    rep = dict(schema='opentallas.hbm.d4g.gen2_l8_idx_n12.v1', region=REGION, inp=str(a.inp))
    ex, bad, l8 = run(c, rep)
    json.dump(c, open(a.out, 'w'), indent=None)
    Path(a.report).write_text(json.dumps(rep, indent=1, default=str))
    print('L8', json.dumps(dict(l8.log)), 'exposed', len(ex), 'bits', sum(x[2] for x in ex), 'unlisted', len(bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
