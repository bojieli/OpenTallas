#!/usr/bin/env python3
"""r2h variants of fpq_r2f (Q-COMPUTE-DIE 00:30 10-16): fix the 19 residual cut windows by pin-face/placement moves.
usage: mk_r2h.py NAME FLAGS   FLAGS subset of: A (ucie abuts collective E face, serdes0 beyond it),
  B (su64 external/seq group pins -> su64 W face; seq_su MY so its pins face su64), C (port tile bw pins spread over
  the whole bw face height), D (collective E-face stx0/srx0/shared pins spread to align with the abutting PHY pins)"""
import json, sys, copy, collections
from pathlib import Path
SRC = Path('/home/ubuntu/artifacts/globalfp/qwen/fpq-2210'); OUT = Path(__file__).resolve().parent
name, flags = sys.argv[1], sys.argv[2]
g = json.load(open(SRC / 'fpq_r2f-graph.json')); H = json.load(open(SRC / 'fpq_r2f-homes.json')); h = H['homes']
I = {i['n']: i for i in g['insts']}
def base(p): return p['name'].split('[')[0]
def idx(p): return int(p['name'].split('[')[1][:-1]) if '[' in p['name'] else 0
if 'A' in flags:
    c = h['io_collective']; x = c['x'] + c['w'] + 4.32
    h['io_ucie']['x'] = round(x, 3); h['io_serdes']['x'] = round(x + h['io_ucie']['w'] + 4.32, 3)
if 'B' in flags:
    M = g['masters']['qfd_sp_su64_sfu']
    move = {'external_a_q', 'external_a_addr', 'external_vm_a_addr', 'external_a_re', 'external_vm_a_re', 'si', 'sd', 'acc'}
    for p in M['pins']:
        if base(p) in move:
            r = p['rect']; wdt = r[2] - r[0]; p['rect'] = [0.0, r[1], wdt, r[3]]
    h['seq_su']['o'] = 'MY'
    # seq_su faces su64 across the 346-um gap: align seq pin rows (111..514) with su64 rows (267..836)
    h['seq_su']['y'] = round(h['sp_su64_sfu']['y'] + 160.0, 3)
if 'C' in flags:
    for mn, M in g['masters'].items():
        if not mn.startswith('qfd_port_tiles'): continue
        grp = collections.defaultdict(list)
        for p in M['pins']:
            if base(p).startswith('bw') and base(p)[2:].isdigit(): grp[base(p)].append(p)
        if not grp: continue
        keys = sorted(grp, key=lambda k: int(k[2:])); n = sum(len(grp[k]) for k in keys)
        lo, hi = 120.0, M['h'] - 120.0; k0 = 0
        for k in keys:
            for p in sorted(grp[k], key=idx):
                y = lo + (hi - lo) * k0 / max(1, n - 1); r = p['rect']; t = r[3] - r[1]
                p['rect'] = [r[0], round(y - t / 2, 3), r[2], round(y + t / 2, 3)]; k0 += 1
if 'D' in flags:
    M = g['masters']['qfd_collective_static_io_production']
    # spread each E-face wide group over the full face height (die-assigned pins; master has no view)
    E = [b for b in ('stx0', 'srx0', 'shared_tx', 'shared_rx')]
    ps = [p for p in M['pins'] if base(p) in E]
    ps.sort(key=lambda p: (E.index(base(p)), idx(p))); n = len(ps); lo, hi = 40.0, M['h'] - 40.0
    for k, p in enumerate(ps):
        y = lo + (hi - lo) * k / max(1, n - 1); r = p['rect']; t = r[3] - r[1]
        p['rect'] = [r[0], round(y - t / 2, 3), r[2], round(y + t / 2, 3)]
if 'V' in flags:
    # VM hub at the owner-reported coherent paired-bank footprint 4872 x 3239.36 um (Q-VM 2330: 487 hard leaves = 10.05 mm2
    # fill 96.9% of the old 4708.8 x 2203.2 frame); top edge stays on su64, grows south; S-face consumers move with it
    M = g['masters']['qfd_sp_vector_memory_par']; W0, H0 = M['w'], M['h']; W1, H1 = 4872.0, 3239.36; dy = H1 - H0
    for p in M['pins']:
        r = p['rect']
        if r[1] < 1.0 and r[3] < 1.0 + (r[3] - r[1]): pass                      # S face stays at y=0
        else: r[1] += dy; r[3] += dy
        if abs(r[2] - W0) < 1.0: r[0] += W1 - W0; r[2] += W1 - W0
    M.update(w=W1, h=H1)
    for i in g['insts']:
        if i['m'] == 'qfd_sp_vector_memory_par': i.update(w=W1, h=H1)
    v = h['sp_vector_memory']; v['y'] = round(v['y'] - dy, 3); v['w'] = W1; v['h'] = H1
    for n in ('native59', 'embed_prov'):
        h[n]['y'] = round(h[n]['y'] - dy, 3)
if 'W' in flags:
    # A realised as the GEN does it (native_static_io_bind column order swapped): the abutting PHY (UCIe) owns the E
    # window at y 600 (+2 slots for clk/rst_n), SerDes0 follows above it and crosses the UCIe PHY on upper metal
    M = g['masters']['qfd_collective_static_io_production']
    order = [('ucie_up', None), ('shared_tx_valid', None), ('shared_tx', None), ('shared_rx_valid', None), ('shared_rx', None)]
    s0 = [('serdes_up0', None), ('serdes_tx_valid0', None), ('stx0', None), ('serdes_rx_valid0', None), ('srx0', None)]
    byb = collections.defaultdict(list)
    for p in M['pins']: byb[base(p)].append(p)
    y = 600.0 + 2 * .048
    def col(items, y):
        for b, _ in items:
            for p in sorted(byb.get(b, []), key=idx):
                r = p['rect']; t = r[3] - r[1]; p['rect'] = [r[0], round(y - t / 2, 4), r[2], round(y + t / 2, 4)]; y += .048
        return y
    end = col(order, y); col(s0, max(end, 660.0) + 8.0 + 2 * .048)
if 'E' in flags:
    # widen the seq_su -> su64 channel: seq_su flush to the port_tiles_1_f1 E edge + 21.6
    pf = h['sp_port_tiles_1_f1']; h['seq_su']['x'] = round(pf['x'] + pf['w'] + 21.6, 3)
for i in g['insts']:
    v = h[i['n']]; i.update(x=v['x'], y=v['y'], o=v['o'])
# overlap check
L = sorted(h.items(), key=lambda kv: kv[1]['x']); ov = []
for a in range(len(L)):
    na, A_ = L[a]
    for b in range(a + 1, len(L)):
        nb, B_ = L[b]
        if B_['x'] >= A_['x'] + A_['w'] - 1e-6: break
        if min(A_['y'] + A_['h'], B_['y'] + B_['h']) - max(A_['y'], B_['y']) > 1e-6: ov.append((na, nb))
H['candidate'] = name; H['params']['r2h_flags'] = flags
json.dump(g, open(OUT / f'{name}-graph.json', 'w')); json.dump(H, open(OUT / f'{name}-homes.json', 'w'), indent=0)
print(name, flags, 'overlaps', ov[:8], 'die', g['die']['w'], g['die']['h'])
