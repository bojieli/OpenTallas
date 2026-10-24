#!/usr/bin/env python3
"""KV-P3 10-23: non-core clock regions + reset root of plan v3.2 (bind/blockers_v31.json item 5).  The die_plan schema
has ONE clock (clk_core spine) and a die-pin reset source, so these are a sidecar until PLAN-TOOL adds clock regions.
Consumers from the as-built rtl6 die.v (pll pin sinks mapped to plan partitions, scratch clocks.py):
  pll_hbm_Q (Q = WS/WN/ES/EN): phy_Q_0..7 (HBM PHY slices, whole partition), pc_Q_0..7 (kvpc/kvs_grp hck), hroot_Q
  (kc pll_hbm); pll_phy / pll_host / pll_ingest: hub_Wi only (host core); pll_fwd: sys_c (qkd_ckbump forwarded clock).
Rules (TOPDOWN): regional spine per clock on M8/M9 from the PLL in hub_C, repeaters <= 450 um, one tap per consuming
partition (pc/hroot/hub_Wi become multi-clock partitions: one tap per clock), neighbour skew <= 80 ps TT+FF between
abutting partitions of the SAME clock; buses are registered in the domain of their leaf ports (phy-facing pc buses on
clk_hbm_Q, phy partitions entirely clk_hbm_Q); core<->hbm crossings stay inside the leaves (kvpc/kc CDC as built).
Reset root: the plan reset spine is sourced by host.die_rst_n (hub_Wi), not the die pin; hub_Wi's own synchroniser
takes the die power-on reset pin.
    python3 clocks_v32.py die_plan.json > clocks_v32.json"""
import json
import sys

P = json.load(open(sys.argv[1]))
T = P['partition_types']
pos = {}
for p in P['partitions']:
    t = T[p['type']]
    w, h = t['outline_um']
    pos[p['name']] = (p['origin_um'][0] + w / 2, p['origin_um'][1] + h / 2, p['type'])
root = pos['hub_C'][:2]
REP = 450.0


def region(name, parts, why, domain_buses):
    far = max(abs(pos[x][0] - root[0]) + abs(pos[x][1] - root[1]) for x in parts)
    return dict(name=name, source=dict(part='hub_C', leaf='pll', pin=name.replace('clk_', 'pll_')), why=why,
                spine=dict(layers=['M8', 'M9'], root_um=[round(root[0], 2), round(root[1], 2)], topology='fishbone',
                           reach_max_um=round(far, 1), repeaters_max=int(far // REP)),
                taps={x: dict(type=pos[x][2], tap='centre (second tap where the type has a core tap)') for x in parts},
                insertion_ps=250, insertion_tol_ps=40, neighbour_skew_ps=80, domain_buses=domain_buses)


R = []
for q in ('WS', 'WN', 'ES', 'EN'):
    parts = [f'phy_{q}_{k}' for k in range(8)] + [f'pc_{q}_{k}' for k in range(8)] + [f'hroot_{q}']
    R.append(region(f'clk_hbm_{q}', parts, 'HBM PC clock of quadrant ' + q,
                    'phy partitions: every bus; pc: the phy-facing buses (pc__pi/po, front/return_hbm_data, land_es/er, '
                    'hes/her, hcompletion_v/we); hroot: kc pll_hbm logic (no lane)'))
for n in ('phy', 'host', 'ingest'):
    R.append(region(f'clk_{n}', ['hub_Wi'], f'host-internal clock ({n}); consumers only in hub_Wi (qkd_host_rt ck_*)',
                    'none (internal to hub_Wi)'))
R.append(region('clk_fwd', ['sys_c'], 'die-to-die forwarded clock to qkd_ckbump.pll_ck (d2d bump)', 'none (bump)'))
out = dict(schema='opentallas.kv_p3.clock_regions.v1', plan_note=P['note'][:80], core=P['clock'], regions=R,
           reset_root=dict(source=dict(part='hub_Wi', leaf='host', pin='die_rst_n'), por=dict(part='@die', bus='rst_n',
                           sinks=['hub_Wi reset synchroniser only']), bits_as_built=5760,
                           rule='async assert / sync release per partition (2 stages), data and stations reset-less, '
                                'release counted; hub_C PLL lock -> host -> die_rst_n'),
           tool_requests=['schema: clocks[] (name, source part/leaf pin, spine, insertion, neighbour skew) and per-type '
                          'clock_taps{clock: tap_um}; per-bus clock (default core)',
                          'gen_rtl: one clk port per clock of the type; boundary flops of a bus on its clock',
                          'g2: route every clock spine root -> its taps; report reach per clock',
                          'reset.source may be a partition bus (hub_Wi die_rst_n); die_top: por pin -> that partition'])
json.dump(out, sys.stdout, indent=1)
