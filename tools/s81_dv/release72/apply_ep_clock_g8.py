#!/usr/bin/env python3
"""S81 DIE72 G8: per-region clock trees for the four MU72 end parents (s_0S, s_0N, s_7S, s_7N).

G2..G7 bound all 12 clock ports of an end parent (ck_S, ck_K, ck_ML, ck_L0/1/3/4, ck_CAP_RT/CW/CE/RN/RS) to the one slice
region root ('diagnostic implementation root').  G8 gives every port its own declared die-top clock input
ck_ep_<inst>_<port>, exactly as the 72 frames' ck_r0/1/2 (frame_bind instance_clock_ports + clock_domains rows:
833.333 ps, same PLL fixed phase, not asynchronous to core) -> one clock tree per region of the end slot; the region
crossings inside the parent are the existing landed transports.  Usage: apply_ep_clock_g8.py BIND_TABLE PLAN
Applied after the MU72 overlay (which sets the module + clk/clk_extra of each end-parent master row)."""
import json, sys
from pathlib import Path

EP = ('s_0S', 's_0N', 's_7S', 's_7N')
tp, pp = Path(sys.argv[1]), Path(sys.argv[2])
t = json.loads(tp.read_text()); plan = json.loads(pp.read_text())
blocks = {b['name']: b for b in plan['blocks']}
icp = t.setdefault('instance_clock_ports', {}); doms = t.setdefault('clock_domains', {})
n = 0
for inst in EP:
    b = blocks[inst]; m = t['masters'][b['master']]
    ports = m.get('clock_ports') or [m['clk']] + list(m.get('clk_extra', []))
    assert len(ports) == 12 and len(set(ports)) == 12, (inst, ports)
    assert inst not in icp, inst
    row = {}
    for k, p in enumerate(ports):
        net = f'ck_ep_{inst}_{p[3:] if p.startswith("ck_") else p}'
        assert net not in doms, net
        row[p] = net
        doms[net] = dict(period_ps=833.333, asynchronous_to_core=False, relationship='same_pll_fixed_phase',
                         source_kind='die_top_input', receiver_instance=f'u_{inst}', receiver_clock_port=p, receiver_region=p[3:],
                         receiver_pin_xy_um=[round(b['x'] + b['w'] / 2, 3), round(b['y'] + (k + 0.5) * b['h'] / 12, 3)],
                         receiver_pin_source='S81 G8 plan seed (end-parent per-region clock tree; actual pin from the GEN)')
        n += 1
    icp[inst] = row
t['ep_clock_note_g8'] = ('S81-G8 10-21: per-region clock trees on the 4 MU72 end parents (12 die-top roots each, '
                         'ck_ep_<inst>_<region>); was one slice-region root for all 12 ports')
tp.write_text(json.dumps(t, indent=1) + '\n')
print('EP_CLOCK_G8', len(EP), 'instances', n, 'roots')
