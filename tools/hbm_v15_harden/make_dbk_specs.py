#!/usr/bin/env python3
"""HBM-V15-HARDEN 2026-10-15: ref_tile kits for the DMA STORE back engine successor ot_hgi_dma_back_static_vp (pipelined
descriptor validator; same ports as ot_hgi_dma_back_static/_cursor), one per stack STK=0..3, built to the H-DIE T_band2
grant hb_dbk_<q> (results/arch/hier_contract_1015/hbm_v15.json v1: ONE plan 432 x 360.72, NE reference R0, faces
W rq/rr, N writeback, E control+clock, pins at the granted spans)."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'tools/ref_tile/specs_hbm_v15_harden'
hc = json.loads((ROOT / 'results/arch/hier_contract_1015/hbm_v15.json').read_text())
slot = next(s for s in hc['slots'] if s['name'] == 'hb_dbk_NE')
SR128 = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2'
base = lambda n: re.sub(r'\[.*$', '', n)
faces, ranges = {}, {}
for p in slot['pins']:
    faces.setdefault(p['face'], []).append(base(p['name']))
    ranges[base(p['name'])] = [round(p['span_um'][0], 3), round(p['span_um'][1], 3)]
for k, q in enumerate(('SW', 'SE', 'NW', 'NE')):
    name = f'hv15_dbk_vp_stk{k}'
    b = [dict(name='exact', cmd='bash tools/hbm_v15_harden/bench_dma_vp.sh {RUN}/bench/exact 0', expect='pass', threads=1,
              peak_ram_gb=8, needs=['iverilog'], pass_regex='DMA_VP_BENCH_PASS', min_count_regex=r'checks=(\d+)')]
    b += [dict(name=f'mutant{m}', cmd=f'bash tools/hbm_v15_harden/bench_dma_vp.sh {{RUN}}/bench/mut{m} {m}', expect='fail',
               threads=1, peak_ram_gb=8, needs=['iverilog']) for m in (1, 2)]
    spec = dict(name=name, top='ot_hgi_dma_back_static_vp', kind='tile', params=dict(STK=k),
                sources=['rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp.sv', SR128 + '/ot_sram_1r1w_128x256_m1_r2c2_bb.v'],
                clock_port='clk', reset_ports=['rst_n'], pins=faces, layer_cap='M5', recipe=2,
                macros=[dict(view=SR128, count=8)], outline=dict(slot['outline'], exact=True),
                slot_change_request=('H-DIE grant hb_dbk_<q> cell ot_hgi_dma_back_static -> ot_hgi_dma_back_static_vp (identical ports; '
                                     'command accepted DESC_LAT=2 cycles later, compiler sends it 2 cycles earlier); granted pin spans not used: at 1 pin/0.096 um they fail the route pin placer (pin_fit 2 tracks/pin: rr 2056 pins in 197 um W, wd 2312 in 222 um N), faces kept, offsets by the placer. HBM-V15-HARDEN '
                                     'el1015-hbm-v15-harden.log'),
                route=dict(pd=0.5, period_ps=833.333, threads=8, peak_ram_gb=32, hold_margin_ns=0.03),
                job=dict(owner='Claude:HBM-V15-HARDEN', branch='claude/hbm-v15-harden-1015b', tag='vp1',
                         purpose=(f'hb_dbk_{q} DMA STORE back engine STK={k}, structural successor for the cursor CTS gate TT -827 ps '
                                  '(33-level descriptor validation in one cycle): 2-stage descriptor pipeline (range-truncated '
                                  'products + static checks) and registered slot cycles; DESC_LAT=2, issue/drain/beat cycles and '
                                  'faults identical to the cursor fed 2 cycles later; to the T_band2 grant 432x360.72.'),
                         extra_paths=['tools/hbm_v15_harden', 'rtl/hbm_accel/generic/peers/static', 'rtl/hbm_accel/generic/vm/static',
                                      SR128, 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2',
                                      'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2'],
                         record_to=f'results/rtl/ref_tile/{name}', benches=b))
    (OUT / f'{name}.json').write_text(json.dumps(spec, indent=1) + '\n')
    print(name, {f: len(v) for f, v in faces.items()})
