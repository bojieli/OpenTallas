#!/usr/bin/env python3
"""H-DIE grants v7 step 2 (2026-10-15 ~19:25, coordinator queue): H-HARDEN + H-ELEM-A/H-SU requests.
 (1) hb_dbk_<q>: wires-only cluster ot_hgi_dma_back_static_vp4_banks = 1 controller ot_hgi_dma_back_static_vp4_controller
     (69.12 x 69.12, closed + native PASS) + 8 ot_hgi_dma_back_landing_bank (140.4 x 88.56, closed + native PASS, own
     clock entries clk_bank[7:0]).  Slot 488.16 x 360.72 (was 432: 3 x 140.4 bank columns on the 43.2-um child lattice),
     grown away from the quadrant centre (SW/NW left, SE/NE right) into free area (checked against every die slot and
     plan block).  Children at the 43.2 lattice: banks (0,0) (172.8,0) (345.6,0) (0,129.6) (172.8,129.6) (345.6,129.6)
     (0,259.2) (172.8,259.2), controller (345.6,259.2).  ONE controller master for all four stacks (DEDUPE): STK enters as
     a 2-bit strap pin stk[1:0] tied per instance as a declared logical constant (RTL change: H-HARDEN).
 (2) hb_ckgen: wires-only cluster = PLL abstract ot_hbm_pll_bb (172.8) + 4 hfd_ckgen_rel leaves (21.6, closed + native
     PASS).  Slot 259.2 x 220.32 (was 216 x 216): PLL at (22.32, 23.76) with 20-um channels, leaves in a column at
     x 215.28, y 23.76 + 41.6 k.  Pins: refclk, por_n N; pll_hbm/pll_stream/pll_serial/pll_link + por_hbm/por_stream/
     por_serial/por_link S M5 (the die trees tap S).
 (3) ot_hbm_svc_static_vm_delivery: NO slot.  The SM-specific service engine (adopted 18:15) retires the svc bands that
     were delivery's fill source; every controller K port belongs to an SM service group.  The VM HBM path is an open
     H-DIE structural item (compiler-windowed K-port share or dedicated PCs); hold the lane split until it is designed.
 (4) SU RF route: RF_RELAY = 36 stages on each of the 16 core->core routes (su_rf_route_pins.json paths), relay homes
     at equal arc length along each path (channels + relay rows only); same-core routes: 36 stages in the relay row
     at the core's channel-facing pin, 4.8 um apart.  Serial 900 MHz, 41 b/stage.
Idempotent.
"""
import json, math, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
GF = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
RF = ROOT / 'results/arch/hbm_die_v15/compact660_v5/su_rf_route_pins.json'
G = json.loads(GF.read_text()); S = {s['name']: s for s in G['slots']}
rec = dict(date='2026-10-15', owner='H-DIE', changes=[])


def pack(face_ports, L, start=None, pitch=0.096):
    out = []
    for f, plist in face_ports.items():
        bits = sum(w for _, w in plist)
        x = start.get(f) if start and f in start else round((L[f] - bits * pitch) / 2 / 0.048) * 0.048
        for n, w in plist:
            out.append(dict(name=f'{n}[{w - 1}:0]' if w > 1 else n, face=f, layer='M5' if f in 'NS' else 'M4',
                            span_um=[round(x, 3), round(x + w * pitch, 3)], offset=round(x + w * pitch / 2, 3)))
            x += w * pitch
    return out


# (1) DMA back
W1, H1 = 488.16, 360.72
for q in ('SW', 'SE', 'NW', 'NE'):
    s = S[f'hb_dbk_{q}']
    if s['outline']['w'] != W1:
        if q in ('SW', 'NW'):
            s['origin']['x'] = round(s['origin']['x'] - (W1 - s['outline']['w']), 3)
        s['outline'] = dict(w=W1, h=H1)
    s.update(cell='ot_hgi_dma_back_static_vp4_banks', kind='cluster', grant='wires_only_cluster_v7',
             source='rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks.sv', version=7,
             params=dict(STK=('SW', 'SE', 'NW', 'NE').index(q)),
             children=[dict(inst=f'u_bank{b}', view='physical/ref_tile/hv15_dbk_bank/views/ot_hgi_dma_back_landing_bank',
                            at=[[0, 0], [172.8, 0], [345.6, 0], [0, 129.6], [172.8, 129.6], [345.6, 129.6], [0, 259.2], [172.8, 259.2]][b])
                       for b in range(8)] + [dict(inst='u_control', view='physical/ref_tile/hv15_dbk_vp4_ctl_stk0/views/ot_hgi_dma_back_static_vp4_controller',
                                                 at=[345.6, 259.2], dedupe='one master for all stacks: stk[1:0] strap pin (H-HARDEN RTL)')])
    s['pins'] = pack({'W': [('rq', 136), ('rr', 2056)],
                      'N': [('wb_reserve_v', 1), ('wb_reserve_bank', 1), ('wb_fill_bank', 1), ('wb_reserve_epoch', 16),
                            ('wb_fill_epoch', 16), ('wb_reserve_sectors', 12), ('wb_reserve_base', 32), ('wb_fill_start', 1),
                            ('wb_ready', 1), ('wd', 2312), ('wa', 12)],
                      'E': [('clk', 1), ('clk_bank', 8), ('rst_n', 1), ('cycle', 32), ('mv_v', 1), ('mv', 227), ('issue_at', 32),
                            ('drain_at', 32), ('mv_wb_bank', 1), ('mv_wb_epoch', 16), ('mv_src', 1), ('mv_done', 1),
                            ('mv_fault', 1), ('quiet', 1), ('busy', 1)]},
                     dict(N=W1, S=W1, E=H1, W=H1))
rec['changes'].append('hb_dbk x4 -> wires-only vp4 cluster 488.16 x 360.72 (1 controller + 8 banks), one controller master (stk strap)')
# (2) ckgen
s = S['hb_ckgen']
s.update(outline=dict(w=259.2, h=220.32), kind='cluster', grant='wires_only_cluster_v7', version=7,
         children=[dict(inst='u_pll', view='physical/hbm_pll_views/ot_hbm_pll_bb', at=[22.32, 23.76])] +
                  [dict(inst=f'u_rel{k}', view='physical/ref_tile/hbm_ckgen_rel/views/hfd_ckgen_rel', at=[215.28, round(23.76 + 41.6 * k, 2)])
                   for k in range(4)])
s['pins'] = pack({'N': [('refclk', 1), ('por_n', 1)],
                  'S': [('pll_hbm', 1), ('pll_stream', 1), ('pll_serial', 1), ('pll_link', 1),
                        ('por_hbm', 1), ('por_stream', 1), ('por_serial', 1), ('por_link', 1)]},
                 dict(N=259.2, S=259.2), pitch=4.8)
rec['changes'].append('hb_ckgen -> 259.2 x 220.32 wires-only cluster (PLL + 4 ckgen_rel), por_* + pll_* S M5, refclk/por_n N')
# (3) delivery
G.setdefault('retired_masters', {})['ot_hbm_svc_static_vm_delivery'] = (
    'no slot (v7): svc bands retired by the SM-specific engine; VM HBM path = OPEN H-DIE structural item '
    '(compiler-windowed K-port share or dedicated PCs); lane split on hold')
rec['changes'].append('ot_hbm_svc_static_vm_delivery: no slot; VM HBM path open (H-DIE)')
# (4) RF relays
R = json.loads(RF.read_text()); N = 36
relays = []
for r in R['routes']:
    pts = r['path']
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    L = sum(seg)
    homes = []
    for k in range(1, N + 1):
        if L == 0:
            x, y = pts[0]; dx = 4.8 * k * (1 if r['src_pin']['face'] == 'E' else -1)
            homes.append([round(x + dx, 3), round(y, 3)]); continue
        t = L * k / (N + 1); i = 0
        while t > seg[i] and i < len(seg) - 1:
            t -= seg[i]; i += 1
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        f = t / seg[i] if seg[i] else 0
        homes.append([round(x0 + (x1 - x0) * f, 3), round(y0 + (y1 - y0) * f, 3)])
    relays.append(dict(src=r['src'], dst=r['dst'], bits=r['bits'], length_um=r['length_um'], stages=N,
                       max_hop_um=round(L / (N + 1), 1) if L else 4.8, homes=homes))
G['su_rf_relays_v7'] = dict(RF_RELAY=N, clock='serial 900 MHz', bits_per_stage=41, routes=relays,
                            relay_flops=N * 41 * len(relays),
                            rule='equal arc length along the su_rf_route_pins.json paths (channels / relay rows only)')
rec['changes'].append(f'SU RF: {N} relay homes x {len(relays)} routes (max hop {max(x["max_hop_um"] for x in relays)} um)')
G['grants_v7_1925'] = rec
GF.write_text(json.dumps(G, indent=1) + '\n')
print(json.dumps(rec, indent=1))
