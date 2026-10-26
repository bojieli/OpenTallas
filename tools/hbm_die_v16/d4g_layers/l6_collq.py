#!/usr/bin/env python3
"""H-D4G GEN2 10-18 (HBM-COLLQ claude/hbm-collq-1018 + HBM-RTL4 ring B claude/hbm-rtl4-ringb-1018): contract post-layer
L6 -- per-quadrant COLL gather master + ring B (two-ring all-gather), bound from the two committed binding records.

    l6_collq.py IN_contract.json[.gz] OUT_contract.json --report R.json

Bindings  results/arch/hbm_die_d4g/ring_b/ring_b_binding.json   hcollb_<q> (ot_hgi_coll_ring_b_stop) x4, ring B cw/ccw
                                                                 edges (q0 SW -> q1 SE -> q3 NE -> q2 NW, = ring A), qid straps
          results/arch/hbm_die_d4g/collq/collq_binding.json      hb_coll_<q> master swap (SW ot_hfd_coll_q3_hard_v8x,
                                                                 SE/NW/NE ot_hfd_coll_q2_hard_v8g: u_ring = ot_hgi_coll_ring_ag),
                                                                 hcollgi/hcollgl (gather issue / land), hcollrs (COLL read static
                                                                 owner split, ot_hbm_idx_vm_share2_static), hcollks (kq write split),
                                                                 its 308 edges, qid / tgt straps
Re-source the existing hb_coll_<q>.vm_rq / vm_rr / vm_kq <-> vmb_<q><b> edges keep their bank-side end and slices; the COLL end
          moves to hcollrs_<q>.vm_rq / vm_rr and hcollks_<q>.vm_kq (the binding's a_* edges give hb_coll its side back).
Host      hcollgi_<q> = F20 targets 176..179 (free in host_status TGTS and the ingress TARGET_MASK; L3.host_slots: t_ready /
          t_active / t_fault + mask).  Extra sticky faults -> host_status t_fault (NF widened, no target id): gi.tgt_fault,
          gl.fault, rs.fault, ks.fault, hcollb.fault (the binding's 'quadrant fault OR / host status beside hb_coll').
Clocks    every new clk / clk_pair = stream (hb_ckgen.pll_stream), rst_n = the COLL region reset hb_coll_<q> uses
          (hb_ckgen.por_stream); regional roots / landings come from the die flow (region map), not this layer.
Nothing is tied: every new input is driven by a binding edge, a strap, or a clock/reset; the layer asserts that no binding
edge drives a sink bit that is already driven.  Pure-python.
"""
import argparse, collections, json, sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import l3_vm_hc_coll as L3M  # noqa: E402

REGION = 'd4g_gen2_l6_collq'
L3M.REGION = REGION
ROOT = L3M.ROOT
RB = ROOT / 'results/arch/hbm_die_d4g/ring_b/ring_b_binding.json'
CQ = ROOT / 'results/arch/hbm_die_d4g/collq/collq_binding.json'
Q = ['SW', 'SE', 'NW', 'NE']
TGT = dict(SW=176, SE=177, NW=178, NE=179)
OWN = 'HBM-COLLQ / HBM-RTL4 (COLL gather master + ring B), bound by H-D4G GEN2'


class L6(L3M.L3):
    def edge(self, src, snk, basis, clock='stream', name=None):
        super().edge(src, snk, basis, clock)
        self.E[-1]['name'] = name or f'l6_{self.n:05d}'

    def clocks_of(self, n):
        for p, d in self.I[n]['ports'].items():
            if d['direction'] == 'input' and p.startswith('clk'):
                self.clock(n, p)
        self.clock(n, 'rst_n', 'reset')


def driven(E, CR, ST, die_pins):
    drv = collections.defaultdict(set)
    for e in E:
        drv[(e['sink'][0], e['sink'][1])] |= set(range(e['sink'][2], e['sink'][3]))
    return drv


def run(c, rep):
    rb, cq = json.loads(RB.read_text()), json.loads(CQ.read_text())
    R = L3M.Rtl()
    l6 = L6(c, R)
    I, E = l6.I, l6.E
    for q in Q:
        assert f'hb_coll_{q}' in I and f'hcollgi_{q}' not in I and f'hcollb_{q}' not in I, q
    # 1 master swap of hb_coll_<q> (same body; NEW isa_ring / isa_lp_data out, ra_* in, ag_* out)
    for q in Q:
        n = f'hb_coll_{q}'; b = cq['instances'][n]
        old_ports = dict(I[n]['ports'])
        l6.remaster(n, b['master'], b['params'], b['change'][:200])
        newp = I[n]['ports']
        gone = [p for p in old_ports if p not in newp]
        chg = [p for p in old_ports if p in newp and old_ports[p] != newp[p]]
        assert not gone and not chg, (n, gone, chg)
        rep.setdefault('remaster', {})[n] = dict(master=b['master'], new_ports=sorted(set(newp) - set(old_ports)))
    # 2 new instances
    for src, binding in (('ring_b', rb), ('collq', cq)):
        for n, b in binding['instances'].items():
            if n.startswith('hb_coll_'):
                continue
            l6.inst(n, b['master'], b.get('params', {}), b['slot'], (b.get('note') or b.get('placement') or '')[:300],
                    b.get('owner', OWN))
            l6.clocks_of(n)
    # 3 re-source the COLL <-> bank edges through the shares (bank end + slices unchanged)
    res = collections.Counter()
    for e in E:
        s, t = e['source'], e['sink']
        for q in Q:
            hc = f'hb_coll_{q}'
            if s[0] == hc and s[1] == 'vm_rq' and t[0].startswith(f'vmb_{q}'):
                e['source'] = [f'hcollrs_{q}', 'vm_rq', s[2], s[3]]; res['rq'] += 1
            elif s[0] == hc and s[1] == 'vm_kq' and t[0].startswith(f'vmb_{q}'):
                e['source'] = [f'hcollks_{q}', 'vm_kq', s[2], s[3]]; res['kq'] += 1
            elif t[0] == hc and t[1] == 'vm_rr' and s[0].startswith(f'vmb_{q}'):
                e['sink'] = [f'hcollrs_{q}', 'vm_rr', t[2], t[3]]; res['rr'] += 1
            else:
                continue
            e['basis'] = (e.get('basis') or '') + f' | {REGION}: re-sourced through the COLL static owner split'
            e['region'] = REGION
    assert res == {'rq': 32, 'rr': 32, 'kq': 32}, dict(res)
    l6.log.update({f'resourced_{k}': v for k, v in res.items()})
    # 4 binding edges (ring B + COLLQ); no sink bit may already be driven
    drv = driven(E, l6.CR, l6.ST, c['die_pins'])
    for src, binding in (('ring_b', rb), ('collq', cq)):
        for e in binding['edges']:
            t = e['sink']
            have = drv[(t[0], t[1])] & set(range(t[2], t[3]))
            assert not have, (e['name'], t, sorted(have)[:4])
            for p_, end in ((e['source'], 'output'), (e['sink'], 'input')):
                d = I[p_[0]]['ports'].get(p_[1])
                assert d and d['direction'] == end and p_[3] <= d['bits'], (e['name'], p_, d)
            l6.edge(e['source'], e['sink'], f'{binding["lane"]} {binding["branch"]}: ' + (e.get('rule') or binding['element'][:80]),
                    e.get('clock', 'stream'), name=e['name'])
            drv[(t[0], t[1])] |= set(range(t[2], t[3]))
            l6.log[f'edges_{src}'] += 1
    # 5 straps
    for binding in (rb, cq):
        for s in binding['straps']:
            assert I[s['inst']]['ports'][s['port']]['bits'] == s['hi'] - s['lo'], s
            l6.strap(s['inst'], s['port'], s['value'], s['reason'])
    # 6 host: F20 targets 176..179 (gather masters) + extra sticky faults
    hs = I['host_status']
    tg = hs['params']['TGTS'].split("'h")[1]
    used = {int(tg[i:i + 2], 16) for i in range(0, len(tg), 2)}
    assert not used & set(TGT.values()), sorted(used & set(TGT.values()))
    l6.host_slots([(TGT[q], f'hcollgi_{q}') for q in Q])
    extra = [(f'hcollgi_{q}', 'tgt_fault') for q in Q] + [(f'{m}_{q}', 'fault') for q in Q for m in ('hcollgl', 'hcollrs', 'hcollks', 'hcollb')]
    nf = int(hs['params']['NF'])
    for k, (n, p) in enumerate(extra):
        l6.edge([n, p, 0, 1], ['host_status', 't_fault', nf + k, nf + k + 1],
                'static component sticky fault observation (COLLQ / ring B); never reschedules execution')
    hs['params']['NF'] = nf + len(extra); hs['ports']['t_fault']['bits'] = nf + len(extra)
    l6.log['host_faults_added'] = len(extra)
    rep['host'] = dict(targets=TGT, NT=hs['params']['NT'], NF=hs['params']['NF'], extra_faults=extra)
    # 7 gaps the bindings close (if carried)
    closed = [g['id'] for g in c['gaps'] if g['id'].startswith(('G-D4G-RINGB-CMD', 'G-D4G-RINGB-PUB'))]
    c['gaps'] = [g for g in c['gaps'] if g['id'] not in closed]
    rep['gaps_closed'] = closed + cq['closes_gaps']
    notes = c.get('notes'); c['notes'] = {}
    ex, bad = l6.finish()
    nl = c['notes']
    c['notes'] = notes + [dict(region=k, note=v) for k, v in nl.items()] if isinstance(notes, list) else dict(notes or {}, **nl)
    rep.update(log=dict(l6.log), exposed_inputs=ex, unlisted_exposed=bad, summary=c['summary'],
               open_outputs_collq=[o for o in c['open_outputs'] if o[0].startswith(('hcoll', 'hb_coll_'))])
    return ex, bad, l6


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = L3M.ld(a.inp)
    rep = dict(schema='opentallas.hbm.d4g.gen2_l6_collq.v1', region=REGION, inp=str(a.inp))
    ex, bad, l6 = run(c, rep)
    json.dump(c, open(a.out, 'w'), indent=None)
    Path(a.report).write_text(json.dumps(rep, indent=1, default=str))
    print('L6', json.dumps(dict(l6.log)), 'exposed', len(ex), 'bits', sum(x[2] for x in ex), 'unlisted', len(bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
