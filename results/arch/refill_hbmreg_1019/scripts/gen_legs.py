#!/usr/bin/env python3
"""REFILL-1725/HBMREG: build legs.tsv (name, expect, regex, cmd) from the kit specs' job.benches + extra legs."""
import json, sys, pathlib
root = pathlib.Path(sys.argv[1]); out = open(sys.argv[2], 'w')
KITS = ['hidx_sel_s1a', 'hbfd_rrl_csync', 'hbm_su_pslice_c5_lp8a', 'hdie_col_idx256r_a']
def leg(name, expect, regex, cmd): out.write('\t'.join([name, expect, regex or 'NONE', cmd]) + '\n')  # NONE: bash read collapses empty tab fields
for k in KITS:
    d = json.load(open(root / 'physical/ref_tile' / k / 'spec.json'))
    for b in d['job']['benches']:
        rx = b.get('pass_regex') if b['expect'] == 'pass' else (b.get('fail_regex') or '')
        leg(f'{k}.{b["name"]}', b['expect'], rx, b['cmd'].replace('{RUN}', f'RUN/{k}.{b["name"]}'))
# extra legs (owner lane evidence, not in kit specs)
leg('idxsel.iv_core_m0', 'pass', 'IDX_SELECTOR_STATIC SHELL0 MUT0 frame2 checked512 errors0 fault0', 'bash rtl/test/hbm_idx_static/run_selector.sh RUN/idxsel.iv_core 0 0')
leg('idxsel.iv_shell_m0', 'pass', 'IDX_SELECTOR_STATIC SHELL1 MUT0 frame2 checked512 errors0 fault0', 'bash rtl/test/hbm_idx_static/run_selector.sh RUN/idxsel.iv_shell 0 1')
leg('idx256r.fan32off_m0', 'pass', 'IDX256R_PASS cases=7', 'bash rtl/test/hbm_collar_idx256r/run_idx256r_one.sh RUN/idx256r.fan32off_m0 0 0')
for m in range(4):
    leg(f'l21.obs_ring_lmut{m}', 'pass' if m == 0 else 'fail', 'OBS RING BENCH PASS' if m == 0 else '',
        f'bash tools/hbm_die_v16/obs_ring_bench.sh {m}; rc=$?; mkdir -p RUN/l21.obs{m}; mv obj_obs_m{m}* RUN/l21.obs{m}/; exit $rc')
H = open(root / 'results/arch/hbm_unread_gen2e3_1019/l21/README.md').read()
leg('l21.strict_replay_combined', 'pass', '^DIE_PORT_BIND PASS',
    'L=results/arch/hbm_unread_gen2e3_1019/l21; mkdir -p RUN/l21.sr && zcat $L/pre_relay_l21.json.gz > RUN/l21.sr/pre_relay.json && '
    'sha256sum RUN/l21.sr/pre_relay.json && bash tools/hbm_die_v16/d4g_layers/l21_strict_replay.sh RUN/l21.sr/pre_relay.json RUN/l21.sr/pb '
    '$L/review_l21_candidate.json $L/manifest_proposal_l21.json 056f138ddbe6ff0f7c47f6292e638525ff6295f9df1c4c2e736e9c9a31b243cd')
