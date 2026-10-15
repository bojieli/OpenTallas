#!/usr/bin/env python3
"""HBM-V15-HARDEN 2026-10-15 (r2): ref_tile specs for the v15.1 service band masters hfd_svc_v15_<q>_s<k>, built to the
H-DIE top-down grant results/arch/hier_contract_1015/hbm_v15.json v1 (7aa4a2686): slot 1036.8 x 399.6 um, kind cluster,
N closed ot_hbm_svc_static_pc children (view hv15_svc_pc) at the granted origins, VM/control pins N, PHY pins S, and ONE
CLOCK ENTRY PER PC (grant per_pc_root_request: the svcPC native audit failed L408.99/C508.02/spread104.7 on one band
clock) -> band RTL clk_pc0..clk_pc<N-1> (tools/hbm_svc_v15_contract.py), wires-only "entries" cluster.

Bands with the same PC count are name / instance-name variants (identical normalised source and identical granted child
layout), so ONE view per PC count N=1..5 is hardened and renamed for the other bands once closed.
Deviations from the slot, carried as slot_change_request (die lead to confirm): clk -> clk_pc0..clk_pc<N-1> (the grant's own
request); cluster PG M7 over M5-capped children (ref_tile cluster layer rule); first/last child pulled to >= 20 um from
the core edge (23.76 / 872.64 um instead of 10.8 / 885.6: ref_tile channel rule).  Pin offsets are left to the placer
(no pin_ranges): the granted N spans put every bus in 386..638 um, up to ~620 um from the far PC (wire_reach)."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'tools/ref_tile/specs_hbm_v15_harden'
CONTRACT = 'results/arch/hier_contract_1015/hbm_v15.json'
PCV = 'physical/ref_tile/hv15_svc_pc/views/ot_hbm_svc_static_pc'
RTL = 'physical/hbm_accel_die_views/svc/v15/rtl'
EXTRA = ['tools/hbm_v15_harden', RTL, 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2',
         'rtl/hbm_accel/loader/service_native', 'physical/ref_tile/hv15_svc_pc/views']
REP = {1: 'SE_s8', 2: 'SE_s7', 3: 'SW_s4', 4: 'SW_s0', 5: 'SW_s1'}
SCR = ('H-DIE grant 7aa4a2686 hier_contract_1015/hbm_v15.json v1 per_pc_root_request: band clk -> clk_pc0..clk_pc<N-1> (one entry '
       'per PC); ref_tile cluster rule PG M7 strapping M5 children (slot says tile M5); edge PCs at >= 20 um from the core '
       'edge (23.76/872.64 vs 10.8/885.6). HBM-V15-HARDEN el1015-hbm-v15-harden.log')
N_FACE = ['rst_n', 'open_v', 'open_bank', 'open_epoch', 'open_count', 'fill_v', 'fill_bank', 'fill_epoch', 'fill_slot', 'fill_data',
          'read_v', 'read_bank', 'read_epoch', 'read_slot', 'out_v', 'out_data', 'retire_v', 'retire_bank', 'retire_epoch',
          'cmd_v', 'cmd_write', 'cmd_bank', 'cmd_epoch', 'cmd_addr', 'cmd_step', 'block_ready', 'bank_owned', 'busy', 'done', 'fault']
S_FACE = ['k_v', 'k_rdy', 'k_addr', 'k_len', 'k_tag', 'k_we', 'k_wdata', 'k_wstrb', 'k_wr_done', 'kr_v', 'kr_rdy', 'kr_tag',
          'kr_beat', 'kr_data']

hc = json.loads((ROOT / CONTRACT).read_text())
OUT.mkdir(parents=True, exist_ok=True)
for n, b in REP.items():
    top = f'hfd_svc_v15_{b}'
    src = f'{RTL}/{top}.sv'
    slot = next(s for s in hc['slots'] if s['cell'] == top)
    members = sorted({s['cell'] for s in hc['slots'] if s['cell'] in hc['sub_layouts'] and s['cell'].startswith('hfd_svc_v15_') and len(hc['sub_layouts'][s['cell']]) == n})
    insts = re.findall(r'ot_hbm_svc_static_pc\s+(u_pc\d+)\s*\(', (ROOT / src).read_text())
    assert len(insts) == n
    kids = []
    for c, i in zip(hc['sub_layouts'][top], insts):
        x = min(max(float(c['origin']['x']), 23.76), 872.64)
        kids.append(dict(view=PCV, count=1, inst=i, at=[x, float(c['origin']['y'])]))
    cps = [f'clk_pc{k}' for k in range(n)]
    name = f'hv15_svcband_n{n}'
    bench = [dict(name='exact', cmd=f'bash tools/hbm_v15_harden/bench_svc_band.sh {{RUN}}/bench/exact 0 {top}', expect='pass',
                  threads=1, peak_ram_gb=4, needs=['iverilog'], pass_regex='BAND_EQUIV PASS', min_count_regex=r'checks=(\d+)')]
    for m in ((1, 2, 3) if n > 1 else (1, 2)):
        bench.append(dict(name=f'mutant{m}', cmd=f'bash tools/hbm_v15_harden/bench_svc_band.sh {{RUN}}/bench/mut{m} {m} {top}',
                          expect='fail', threads=1, peak_ram_gb=4, needs=['iverilog']))
    spec = dict(name=name, top=top, kind='cluster', sources=[src], clock='entries', clock_port=cps[0], clock_ports=cps,
                reset_ports=['rst_n'], pins=dict(N=cps + N_FACE, S=S_FACE), outline=dict(slot['outline'], exact=True), pg_layer='M7',
                child_lattice_um=2.16, children=kids, slot_change_request=SCR,
                route=dict(pd=0.5, period_ps=833.333, threads=8, peak_ram_gb=24, hold_margin_ns=0.03),
                job=dict(owner='Claude:HBM-V15-HARDEN', branch='claude/hbm-v15-harden-1015b', tag='g1',
                         purpose=(f'v15.1 service band, {n} PC(s), built to H-DIE grant slot {slot["name"]} (1036.8x399.6, children at the '
                                  f'granted origins, one clock entry per PC): one view for {", ".join(members)}. Bench: per-PC clock '
                                  f'ownership + lockstep vs {n} stand-alone PCs; wiring/clock mutants.'),
                         extra_paths=EXTRA, record_to=f'results/rtl/ref_tile/{name}', benches=bench))
    (OUT / f'{name}.json').write_text(json.dumps(spec, indent=1) + '\n')
    print(name, top, members, [k['at'] for k in kids])
