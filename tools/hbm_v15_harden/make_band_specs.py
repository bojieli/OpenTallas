#!/usr/bin/env python3
"""HBM-V15-HARDEN 2026-10-15: ref_tile specs for the v15.1 service band masters hfd_svc_v15_<q>_s<k>.

The 17 band masters are wires-only groups of 1..5 physical PCs (ot_hbm_svc_static_pc); bands with the same PC count
differ only in the module name and the internal instance names (u_pc<physical id>), so ONE view per PC count is hardened
and renamed for the others (tools/ref_tile/rename_view.py) once closed.  N=1 (SE_s8) is the PC itself (same ports,
wires only): it takes the closed PC view renamed, no route.

Two structural candidates per N (A/B, coordinator 08:15 10-15):
  A  cluster: N hard ot_hbm_svc_static_pc children (closed view hv15_svc_pc) in one W->E row, wires-only parent with
     a balanced spine; each PC directly under its band N-face (VM side) and over its S-face (PHY side).
  B  flat tile: the same N PCs + N real 128x256 SRAMs in one CTS domain, outline N x the PC tile (140.4 x 112.32 um
     per PC), one clock root (~1.3k FF per PC) instead of a spine over N separately-rooted children.
Faces follow the v15.1 dataflow: VM landing/control/status N, PHY S, clock/reset W."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'tools/ref_tile/specs_hbm_v15_harden'
SR128 = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2'
PCV = 'physical/ref_tile/hv15_svc_pc/views/ot_hbm_svc_static_pc'
PC = 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_static_pc.sv'
RTL = 'physical/hbm_accel_die_views/svc/v15/rtl'
EXTRA = ['tools/hbm_v15_harden', 'physical/hbm_accel_die_views/svc/v15/rtl', 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2',
         SR128, 'physical/ref_tile/hv15_svc_pc/views']
# representative band per PC count (same-count bands are name-only variants, checked by sha of the normalised source)
REP = {2: ('hfd_svc_v15_SE_s7', ['SE_s7']),
       3: ('hfd_svc_v15_SW_s4', ['SW_s4', 'SE_s6']),
       4: ('hfd_svc_v15_SW_s0', ['SW_s0', 'SE_s0', 'SW_s2', 'SE_s2', 'SW_s3', 'SE_s4', 'SW_s5', 'SE_s5', 'SW_s6', 'SW_s7']),
       5: ('hfd_svc_v15_SW_s1', ['SW_s1', 'SE_s1', 'SE_s3'])}
FACES = dict(N=['fill_v', 'fill_bank', 'fill_epoch', 'fill_slot', 'fill_data', 'read_v', 'read_bank', 'read_epoch', 'read_slot',
                'out_v', 'out_data', 'open_v', 'open_bank', 'open_epoch', 'open_count', 'retire_v', 'retire_bank', 'retire_epoch',
                'cmd_v', 'cmd_write', 'cmd_bank', 'cmd_epoch', 'cmd_addr', 'cmd_step',
                'block_ready', 'bank_owned', 'busy', 'done', 'fault'],
             S=['k_v', 'k_rdy', 'k_addr', 'k_len', 'k_tag', 'k_we', 'k_wdata', 'k_wstrb', 'k_wr_done', 'kr_v', 'kr_rdy', 'kr_tag',
                'kr_beat', 'kr_data'],
             W=['clk', 'rst_n'])


def benches(top):
    b = [dict(name='exact', cmd=f'bash tools/hbm_v15_harden/bench_svc_band.sh {{RUN}}/bench/exact 0 {top}', expect='pass',
              threads=1, peak_ram_gb=4, needs=['iverilog'], pass_regex='BAND_EQUIV PASS', min_count_regex=r'checks=(\d+)')]
    for m in (1, 2):
        b.append(dict(name=f'mutant{m}', cmd=f'bash tools/hbm_v15_harden/bench_svc_band.sh {{RUN}}/bench/mut{m} {m} {top}',
                      expect='fail', threads=1, peak_ram_gb=4, needs=['iverilog']))
    return b


def job(name, purpose, top):
    return dict(owner='Claude:HBM-V15-HARDEN', branch='claude/hbm-v15-harden-1015b', tag='hv15b', purpose=purpose,
                extra_paths=EXTRA, record_to=f'results/rtl/ref_tile/{name}', benches=benches(top))


OUT.mkdir(parents=True, exist_ok=True)
for n, (top, members) in REP.items():
    src = f'{RTL}/{top}.sv'
    names = ', '.join('hfd_svc_v15_' + m for m in members)
    # A: cluster of N closed PC children, one row, PC origins on the 43.2 um child lattice
    a = f'hv15_svcband_p{n}_c'
    spec = dict(name=a, top=top, kind='cluster', sources=[src], clock_port='clk', reset_ports=['rst_n'], pins=FACES,
                outline=dict(w=round(172.8 * n + 43.2, 2), h=181.44), pg_layer='M7',
                children=[dict(view=PCV, count=1, inst=f'u_pc{i}', at=[round(43.2 + 172.8 * i, 2), 43.2]) for i in range(n)],
                route=dict(pd=0.5, period_ps=833.333, threads=8, peak_ram_gb=24, hold_margin_ns=0.03),
                job=job(a, f'v15.1 service band, {n} PCs, candidate A (wires-only cluster of {n} closed hv15_svc_pc children, spine): '
                           f'one view for {names}. Bench: lockstep vs {n} stand-alone PCs, 2 wiring mutants.', top))
    # instance names in the representative are u_pc<physical id>: bind the children by the actual names
    import re
    insts = re.findall(r'ot_hbm_svc_static_pc\s+(u_pc\d+)\s*\(', (ROOT / src).read_text())
    assert len(insts) == n, (top, insts)
    for c, i in zip(spec['children'], insts):
        c['inst'] = i
    (OUT / f'{a}.json').write_text(json.dumps(spec, indent=1) + '\n')
    # B: flat tile, N PCs + N SRAMs, one CTS root
    b = f'hv15_svcband_p{n}_f'
    spec = dict(name=b, top=top, kind='tile', sources=[src, PC, SR128 + '/ot_sram_1r1w_128x256_m1_r2c2_bb.v'], clock_port='clk',
                reset_ports=['rst_n'], pins=FACES, layer_cap='M5', recipe=2, macros=[dict(view=SR128, count=n)],
                outline=dict(w=round(140.4 * n, 2), h=112.32),
                route=dict(pd=0.5, period_ps=833.333, threads=8, peak_ram_gb=24, hold_margin_ns=0.03),
                job=job(b, f'v15.1 service band, {n} PCs, candidate B (flat: {n} PCs + {n} real 128x256 SRAMs, one CTS root, '
                           f'outline {n} x PC tile): one view for {names}. Bench: lockstep vs {n} stand-alone PCs, 2 wiring mutants.', top))
    (OUT / f'{b}.json').write_text(json.dumps(spec, indent=1) + '\n')
    print(n, top, a, b, insts)
