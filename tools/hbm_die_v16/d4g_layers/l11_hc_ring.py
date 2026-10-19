#!/usr/bin/env python3
"""HC-RINGPLAN 10-19: GEN2d contract post-layer L11 -- HC CLOSED RING (after l10_hc_chx.py).

    l11_hc_ring.py IN_contract.json[.gz] OUT_contract.json --report R.json

DIE-HBM-LEAD 10-19 01:40 (lanes/H-D4G.md): in the GEN2d floorplan every quadrant's HC banks form one 3 x 3 ring block
(d4g_gen2d_grants_hcring.py; b7 abuts b0), so the U-form b7 -> b0 die relay hcx_<q>_* goes and its register edge moves INTO
bank 0: ot_hbm_hc_bankq0_static DRLY 1 -> 2 (the existing s_i -> s_o chain-exit register chain).  Hub DRLY 2 / CHX 11,
root QDRLY 2 / QCHX 11, b0 CPO 1, b1/3/4/5/7 CPI = CPO = 1 and ledger hc_tree 41 are unchanged (one calendar, one hub/root
kit): the chain exit still sees bank-0 exit register + one more edge before the hub's s_i.
This layer
  * removes hcx_<q>_* and every relay-tree instance (rfNNNN_*, d4f relay planner: stations / forwarded half-cycle hops /
    landings) whose tree touches an hcx relay -- the trees hcb_<q>7 -> hcx and hcx -> hcb_<q>0 -- with all their edges,
    straps, clock/reset bindings and die pins (landing fault outputs);
  * re-wires hcb_<q>0.s_i[2048:0] bit-exactly to the bank-7 source bits it received through the removed path
    (sum_out[2047:0] + f_out, traced bit by bit through the identity relays), as direct abutment edges;
  * sets hcb_<q>0 DRLY 2 (requires DRLY 1 + CPO 1 on input, i.e. L10 applied).
Ports do not change.  Exit != 0 on any missing instance, untraceable or non-bank-7 bit, or a param mismatch.
"""
import argparse, gzip, json, re, sys

Q4 = ('SW', 'SE', 'NW', 'NE')
THRU = {'i': 'o', 'a': 'b'}   # relay data in -> out (ot_hbm_rly / ot_hbm_lane masters are bitwise identity)


def load(p):
    return json.load(gzip.open(p, 'rt') if p.endswith('.gz') else open(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = load(a.inp); I = c['instances']; E = c['edges']; prob = []
    tree = lambda n: (re.match(r'(rf\d+)_', n) or [None, None])[1]
    # 1. trees touching an hcx relay
    hcx = {n for n in I if re.match(r'hcx_(SW|SE|NW|NE)_\d+$', n)}
    for q in Q4:
        if not any(n.startswith(f'hcx_{q}_') for n in hcx):
            prob.append(f'hcx_{q}_*: missing (input must be the GEN2c U-form contract after L10)')
    trees = {tree(e['source'][0]) or tree(e['sink'][0]) for e in E
             if (e['source'][0] in hcx and tree(e['sink'][0])) or (e['sink'][0] in hcx and tree(e['source'][0]))}
    trees.discard(None)
    rm = hcx | {n for n in I if tree(n) in trees}
    # sanity: the removed set may only talk to hcb_<q>7 (data), hcb_<q>0.s_i, hc_<q>.rstb_w (reset); clocks via clock_resets
    for e in E:
        s, t = e['source'][0], e['sink'][0]
        if s in rm and t not in rm and not (re.match(r'hcb_(SW|SE|NW|NE)0$', t) and e['sink'][1] == 's_i'):
            prob.append(f'removed {s} drives {t}.{e["sink"][1]}')
        if t in rm and s not in rm and not (re.match(r'hcb_(SW|SE|NW|NE)7$', s) and e['source'][1] in ('sum_out', 'f_out')) \
                and not (re.match(r'hc_(SW|SE|NW|NE)$', s) and e['source'][1] == 'rstb_w'):
            prob.append(f'removed {t} driven by {s}.{e["source"][1]}')
    # 2. bit drivers: (inst, port, bit) -> (inst, port, bit)
    drv = {}
    for e in E:
        si, sp, slo, shi = e['source']; ti, tp, tlo, thi = e['sink']
        for k in range(thi - tlo):
            drv[(ti, tp, tlo + k)] = (si, sp, slo + k)

    def trace(key):
        seen = 0
        while key[0] in rm:
            inn = next((ip for ip, op in THRU.items() if op == key[1]), None)
            if inn is None or seen > 400:
                return None
            key = drv.get((key[0], inn, key[2])); seen += 1
            if key is None:
                return None
        return key
    newE = []; rep_q = {}
    for q in Q4:
        b0 = f'hcb_{q}0'; b7 = f'hcb_{q}7'
        if b0 not in I or b7 not in I:
            prob.append(f'{b0}/{b7} missing'); continue
        w = I[b0]['ports']['s_i']['bits']
        src = []
        for b in range(w):
            k = drv.get((b0, 's_i', b)); k = trace(k) if k else None
            if k is None or k[0] != b7:
                prob.append(f'{b0}.s_i[{b}] traces to {k}'); src.append(None)
            else:
                src.append(k)
        if None in src:
            continue
        # coalesce runs
        runs = []; lo = 0
        for b in range(1, w + 1):
            if b == w or src[b][1] != src[lo][1] or src[b][2] != src[lo][2] + (b - lo):
                runs.append((lo, b, src[lo][1], src[lo][2])); lo = b
        for j, (tlo, thi, sp, slo) in enumerate(runs):
            newE.append(dict(name=f'l11_hcring_{q}_{j}', bits=thi - tlo, source=[b7, sp, slo, slo + thi - tlo],
                             sink=[b0, 's_i', tlo, thi], clock='stream', ready_or_credit=False, allowed_exception=None,
                             basis='HC-RINGPLAN L11: closed HC ring, b7 chain exit abuts b0 s_i (hcx die relay removed; '
                                   'its edge is bank-0 DRLY 2)', region='d4g_gen2d_l11'))
        rep_q[q] = dict(runs=[[r[2], r[3], r[3] + r[1] - r[0], r[0], r[1]] for r in runs])
        x = I[b0]; p = x.setdefault('params', {})
        if x['master'] != 'ot_hbm_hc_bankq0_static' or p.get('DRLY') != 1 or p.get('CPO') != 1:
            prob.append(f'{b0}: expected ot_hbm_hc_bankq0_static DRLY 1 CPO 1 (L10), got {x["master"]} {p}')
        p['DRLY'] = 2
        x['note'] = (x.get('note') or '') + ' | L11 closed ring: DRLY 2 (b7->b0 die relay edge moved into bank 0; HC-RINGPLAN 10-19)'
        if 'slot' in x:
            x['slot'] = b0
    if prob:
        json.dump(dict(layer='l11_hc_ring', problems=prob), open(a.report, 'w'), indent=1)
        print('L11_FAIL', len(prob)); print('\n'.join(prob[:20])); sys.exit(2)
    nE0, nS0, nC0, nP0 = len(E), len(c['straps']), len(c['clock_resets']), len(c['die_pins'])
    c['edges'] = [e for e in E if e['source'][0] not in rm and e['sink'][0] not in rm] + newE
    c['straps'] = [s for s in c['straps'] if s.get('inst') not in rm]
    c['clock_resets'] = [r for r in c['clock_resets'] if r['instance'] not in rm]
    c['die_pins'] = [d for d in c['die_pins'] if d.get('instance') not in rm]
    for n in rm:
        del I[n]
    c.setdefault('notes', [])
    if isinstance(c['notes'], list):
        c['notes'].append('L11 (HC-RINGPLAN 10-19): closed HC ring per quadrant (GEN2d ring block): hcx_<q>_* die relay + its '
                          'relay trees removed, b7 chain exit -> b0 s_i direct, bankq0 DRLY 2; hub/root/bank chain params and '
                          'ledger hc_tree 41 unchanged')
    rep = dict(layer='l11_hc_ring', removed_instances=len(rm), removed_hcx=sorted(hcx), removed_trees=sorted(trees),
               edges=[nE0, len(c['edges'])], new_edges=len(newE), straps=[nS0, len(c['straps'])],
               clock_resets=[nC0, len(c['clock_resets'])], die_pins=[nP0, len(c['die_pins'])], quadrants=rep_q,
               bank0_params={q: I[f'hcb_{q}0']['params'] for q in Q4}, hc_tree=41, problems=[])
    json.dump(rep, open(a.report, 'w'), indent=1)
    json.dump(c, open(a.out, 'w'))
    print(f'L11_OK removed={len(rm)} (hcx {len(hcx)}, trees {len(trees)}) new_edges={len(newE)} '
          f'die_pins -{nP0 - len(c["die_pins"])} bankq0 DRLY 2 x4')


if __name__ == '__main__':
    main()
