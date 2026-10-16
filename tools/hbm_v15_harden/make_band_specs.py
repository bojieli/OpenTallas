#!/usr/bin/env python3
"""Generate service band kits from source-pinned per-PC windows in the current die contract.
The unchanged CLOSED PC child is physically unqualified at native boundary budgets.
These kits repair parent geometry without adopting that child or changing cycles.
"""
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'tools/ref_tile/specs_hbm_v15_harden'
CONTRACT = 'results/arch/hier_contract_1015/hbm_v15.json'
PCV = 'physical/ref_tile/hv15_svc_pc/views/ot_hbm_svc_static_pc'
RTL = 'physical/hbm_accel_die_views/svc/v15/rtl'
EXTRA = ['tools/hbm_v15_harden', RTL, 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2',
         'rtl/hbm_accel/loader/service_native', 'physical/ref_tile/hv15_svc_pc/views', 'results/arch/hier_contract_1015/service_pc_windows', CONTRACT]
REP = {1: 'SE_s8', 2: 'SE_s7', 3: 'SW_s4', 4: 'SW_s0', 5: 'SW_s1'}
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
    assert hashlib.sha256((ROOT / src).read_bytes()).hexdigest() == slot['source_sha256']
    assert slot['io_tcl'] == f'results/arch/hier_contract_1015/service_pc_windows/n{n}.tcl'
    members = sorted({s['cell'] for s in hc['slots'] if s['cell'] in hc['sub_layouts'] and s['cell'].startswith('hfd_svc_v15_') and len(hc['sub_layouts'][s['cell']]) == n})
    insts = re.findall(r'ot_hbm_svc_static_pc\s+(u_pc\d+)\s*\(', (ROOT / src).read_text())
    assert len(insts) == n
    kids = []
    for c, i in zip(hc['sub_layouts'][top], insts):
        x = float(c['origin']['x'])
        kids.append(dict(view=PCV, count=1, inst=i, at=[x, float(c['origin']['y'])]))
    cps = [f'clk_pc{k}' for k in range(n)]
    name = f'hv15_svcband_pcwin_n{n}'
    bench = [dict(name='exact', cmd=f'bash tools/hbm_v15_harden/bench_svc_band.sh {{RUN}}/bench/exact 0 {top}', expect='pass',
                  threads=1, peak_ram_gb=4, needs=['iverilog'], pass_regex='BAND_EQUIV PASS', min_count_regex=r'checks=(\d+)')]
    for m in ((1, 2, 3) if n > 1 else (1, 2)):
        bench.append(dict(name=f'mutant{m}', cmd=f'bash tools/hbm_v15_harden/bench_svc_band.sh {{RUN}}/bench/mut{m} {m} {top}',
                          expect='fail', threads=1, peak_ram_gb=4, needs=['iverilog']))
    spec = dict(name=name, top=top, kind='cluster', sources=[src], clock='entries', clock_port=cps[0], clock_ports=cps,
                reset_ports=['rst_n'], pins=dict(N=cps + N_FACE, S=S_FACE), outline=dict(slot['outline'], exact=True), pg_layer=slot['pg_layer'],
                signal_max_layer=slot['signal_max_layer'], io_tcl=f'results/arch/hier_contract_1015/service_pc_windows/n{n}.tcl',
                child_lattice_um=43.2, children=kids, recipe=2, contract=dict(file=CONTRACT, slot=slot['name']),
                route=dict(pd=0.5, period_ps=833.333, threads=8, peak_ram_gb=24, hold_margin_ns=0.03),
                job=dict(owner='Codex:HBM-HARDEN-1103', branch='codex/hbm-hardening-1103', tag='pcwin1',
                         purpose=(f'v15.1 service band, {n} PC(s), built to H-DIE grant slot {slot["name"]} (1036.8x399.6, children at the '
                                  f'granted origins, one clock entry per PC): one view for {", ".join(members)}. Bench: per-PC clock '
                                  f'ownership + lockstep vs {n} stand-alone PCs; wiring/clock mutants.'),
                         extra_paths=EXTRA, record_to=f'results/rtl/ref_tile/{name}', benches=bench))
    (OUT / f'{name}.json').write_text(json.dumps(spec, indent=1) + '\n')
    print(name, top, members, [k['at'] for k in kids])
