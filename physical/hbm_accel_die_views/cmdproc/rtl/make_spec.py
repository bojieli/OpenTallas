#!/usr/bin/env python3
"""hfd_cmdproc interim wrapper spec: two unchanged ot_ds_hbm_cmdproc20 (ENABLE 1, NSM 16; the RTL's command mask
cmd[44 +: NSM] caps NSM at 16), one per die half (S: SW + SE stacks, N: NW + NE), on the die control trees.
Control leaf of SM slot s in a stack (103 b, die_top_lint SM_LAYOUT + sm_desc): start, op_rows13, op_c16, op_g8,
op_gs, op_fmt2, release_in | busy, arrive, released | d_valid, d_base32, d_lines24 | d_ready."""
import json
from pathlib import Path

W = 103
spec = dict(master='hfd_cmdproc', note=(
    'INTERIM: two unchanged ot_ds_hbm_cmdproc20 (ENABLE 1, NSM 16) on the die ports; not routed before, not closed. '
    'Program store and doorbell are loaded through the loader bus f_loader (cmd_we/addr/wdata 73 b + db_v/token/pos/'
    'job/generation 74 b); launch_v[n] drives SM n start and d_valid, launch_pc the op fields (40 b) and d_base, '
    'launch_pos d_lines; SM arrive -> t_barrier, barrier release f_barrier -> release_in, SM released -> sm_done. '
    'res_v/res_data/sm_fault/cpl_rdy have no die net (cfg chain); completion/status outputs fold into spare die '
    'output bits. The pipelined issue sequencer of the ledger is not built.'),
    instances=[])
halves = dict(S=('SW', 'SE'), N=('NW', 'NE'))
for h, (qa, qb) in halves.items():
    b = dict(clk='clk', rst_n='rst_n')
    base = 0 if h == 'S' else 147
    # loader bus: [base, base+73) program store, [base+73, base+147) doorbell
    b['cmd_we'] = f'die:f_loader[{base}:{base + 1}]'
    b['cmd_addr'] = f'die:f_loader[{base + 1}:{base + 9}]'
    b['cmd_wdata'] = f'die:f_loader[{base + 9}:{base + 73}]'
    o = base + 73
    for nm, w in (('db_v', 1), ('db_token', 17), ('db_pos', 20), ('db_job', 32), ('db_generation', 4)):
        b[nm] = f'die:f_loader[{o}:{o + w}]'
        o += w
    starts, pcs, poss, dval = [], [], [], []
    done = []
    for k, q in enumerate((qa, qb)):
        for s in range(8):
            c0 = s * W
            n = 8 * k + s
            starts.append(f'{q}:{c0}')
    # launch_v bit n -> start and d_valid of SM n: one die bit each (lists of 1-bit ranges per output bit is not
    # expressible with a whole-output binding, so use the slice concatenation: start bits of the 16 SMs)
    b['launch_v'] = ['die:' + '+'.join(f'c{q}[{s * W}:{s * W + 1}]' for q in (qa, qb) for s in range(8)),
                     'die:' + '+'.join(f'c{q}[{s * W + 45}:{s * W + 46}]' for q in (qa, qb) for s in range(8))]
    b['launch_pc'] = [f'die:c{q}[{s * W + 1}:{s * W + 33}]' for q in (qa, qb) for s in range(8)] + \
                     [f'die:c{q}[{s * W + 46}:{s * W + 78}]' for q in (qa, qb) for s in range(8)]
    b['launch_pos'] = [f'die:c{q}[{s * W + 78}:{s * W + 98}]' for q in (qa, qb) for s in range(8)]
    b['launch_token'] = [f'die:t_su_{q}[0:17]' for q in (qa, qb)]
    b['sm_done'] = 'die:' + '+'.join(f'c{q}[{s * W + 44}:{s * W + 45}]' for q in (qa, qb) for s in range(8))
    b['sm_fault'] = 'cfg'
    b['res_v'] = 'cfg'
    b['res_data'] = 'cfg'
    b['cpl_rdy'] = 'const:1'
    spec['instances'].append(dict(name=f'cp{h}', module='ot_ds_hbm_cmdproc20',
                                  file='rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',
                                  params=dict(TW=17, PW=20, CONTEXT_POSITIONS=1048576, ENABLE=1, NSM=16, NCMD=256), bind=b))
# SM arrive (slot bit 43) -> barrier arrive senses; barrier release -> release_in (slot bit 41): wrapper wiring
ex, eo = [], []
for qi, q in enumerate(('SW', 'SE', 'NW', 'NE')):
    for s in range(8):
        n = 8 * qi + s
        eo.append((f't_barrier', n, n + 1, f'i_c{q}[{s * W + 43}]'))
        eo.append((f'c{q}', s * W + 41, s * W + 42, f'i_f_barrier[{n}]'))
spec['extra_out'] = eo
spec['kept_out_regs'] = True  # one kept ot_hfd_oreg1 per die output bit (no merged output drivers)
spec['face_stages'] = 3  # owner margin-first rule 2026-10-06: pin flop + 2 stages each face (1.4 mm views)
Path(__file__).with_name('spec.json').write_text(json.dumps(spec, indent=1) + '\n')
