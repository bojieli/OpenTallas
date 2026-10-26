#!/usr/bin/env python3
"""TOKc-SEGCAL 10-22: materialize the HP13 die-form source set (the frozen HP13 frontend inventory,
results/arch/qw_headprep_1021/rrloc_projection/native_frontend/input_source_inventory.json) into OUT.

origin/main carries the HP13 parent (rtl/qwen_dv/headprep13) but not every child source the frozen frontend read; the
missing / newer-on-main files are taken from the git commit whose blob has the inventory sha256 (verified here).  The
HP13 parent files themselves (qfd_tt_ctlm_dv_lpf_hp13*.sv, lp, h16za) are taken from the WORKING TREE (this branch, with
the QW-SEGCAL go port), everything else from git.  Simulation-only extras (memory macro models, F16 wtn) are added from
the commits named below.

    python3 materialize_hp13_sources.py REPO WT OUT        -> OUT/<path> files + OUT/hp13_sources.f + OUT/MATERIALIZE.json
"""
import hashlib, json, os, subprocess, sys
REPO, WT, OUT = sys.argv[1:4]
INV = 'results/arch/qw_headprep_1021/rrloc_projection/native_frontend/input_source_inventory.json'
FROM_WT = ('rtl/qwen_dv/headprep13/',)
# inventory sha256 -> commit (resolved 10-22 by blob sha256 over git log --all)
PIN = {
    'rtl/qwen_sys/program_receiver_20261014/qkd_program_pw_observer_p.sv': 'b67b84cc7a6e6810555e5833fa2eb209154403be',
    'rtl/qwen_sys/dvm_20261014/ot_qfd_xpf_static_schedule_p.sv': '1b54c2ee3b055ce9d5988deffd7d5782cc6463c2',
    'rtl/lib/ot_ks_add.sv': 'b67b84cc7a6e6810555e5833fa2eb209154403be',
    'rtl/qwen_split/mu/qfd_sys_face_mu_dhuser_p.sv': '1b54c2ee3b055ce9d5988deffd7d5782cc6463c2',
    'rtl/qwen_dv/qfd_mu_context_guard.sv': '15b992cb06537f46afab3dc55d911d0780786582',
    'rtl/qwen_dv/qfd_dv_calendar_rom.sv': 'b67b84cc7a6e6810555e5833fa2eb209154403be',
    'rtl/qwen_dv/qfd_dv_typed_witness_control.sv': '15b992cb06537f46afab3dc55d911d0780786582',
    'rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv': '8349f4a116626c59dfdb5ab8670f818514faa0e8',
    'rtl/lib/ot_reset_sync.sv': 'e02c2a4f1a8bf957d60875d1bedeb73630f25ee9',
    'rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv': '5384178be91d12b76b7936b0b61362ad3170cc84',
    'rtl/common/landed_parent/ot_pl_land_reset_forest.sv': '3acc94aecbf8a9d13c52a4164b370c2dd36ff0c4',
    'rtl/common/landed_parent/ot_pl_land_n32.sv': '3c7b42bdf8ea176a63306141a03614c6219d7d96',
}
# simulation-only extras (not in the synthesis inventory: macro models, F16 wtn of the unelaborated F16WTN branch)
EXTRA = {
    'rtl/qwen_dv/qfd_tt_ctlm_dv_wtn.sv': 'fe279525a',
    'rtl/qwen_dv/headprep13/h16za/native32_helpers.sv': None,
    'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v': 'origin/main',
    'physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v': 'origin/main',
    'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v': 'origin/main',
    'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v': 'origin/main',
    'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v': 'origin/main',
}
# the generated HP13 landed-parent bench (rtl/qwen_dv/headprep13/lp/*_lp_bench.sh, die parameters, random lockstep +
# mutants + lp.py region audit): its tb / bench from the worktree, lp.py, its spec and the CALR bench ROM model
LP_EXTRA = {
    'rtl/qwen_dv/headprep13/lp/tb_qfd_tt_ctlm_dv_lpf_hp13_lp.sv': (None, None),
    'rtl/qwen_dv/headprep13/lp/qfd_tt_ctlm_dv_lpf_hp13_lp_bench.sh': (None, None),
    'tools/landed_parent/lp.py': ('origin/main', None),
    'tools/landed_parent/endpoint_domains.py': ('origin/main', None),
    'tools/landed_parent/specs/qfd_tt_ctlm_dv_lpf_hp13_rrloc.json':
        ('origin/main', 'results/arch/qw_headprep_1021/rrloc_projection/generated/qfd_tt_ctlm_dv_lpf_hp13_rrloc.json'),
    'calr/ot_rom_4096x266_m8_calrbench.v': ('6d2544566', 'results/rtl/qw_calr_1020/ctlm9c/ot_rom_4096x266_m8_calrbench.v'),
}
SKIP = {'physical_abstracts.v', 'physical_abstracts.json', 'full_generic_hp13.ys', 'construct_hp13.py', 'run_frontend.sh',
        'tools/qwen_dv/ctlm6_bound_macro.py'}
inv = json.loads(subprocess.run(['git', '-C', REPO, 'show', f'origin/main:{INV}'], capture_output=True, check=True).stdout)['files']
rec, srcs = {}, []
def put(p, b):
    d = os.path.join(OUT, p); os.makedirs(os.path.dirname(d), exist_ok=True); open(d, 'wb').write(b)
for p, h in inv.items():
    if p in SKIP:
        continue
    if p.startswith(FROM_WT):
        b, src = open(os.path.join(WT, p), 'rb').read(), 'worktree'
    else:
        c = PIN.get(p, 'origin/main')
        b, src = subprocess.run(['git', '-C', REPO, 'show', f'{c}:{p}'], capture_output=True, check=True).stdout, c
    s = hashlib.sha256(b).hexdigest()
    rec[p] = dict(source=src, sha256=s, inventory_sha256=h, identical=(s == h))
    if s != h and src != 'worktree':
        sys.exit(f'sha256 mismatch {p} from {src}')
    put(p, b); srcs.append(p)
for p, c in EXTRA.items():
    b = open(os.path.join(WT, p), 'rb').read() if c is None else \
        subprocess.run(['git', '-C', REPO, 'show', f'{c}:{p}'], capture_output=True, check=True).stdout
    rec[p] = dict(source=c or 'worktree', sha256=hashlib.sha256(b).hexdigest(), extra=True)
    put(p, b); srcs.append(p)
for p, (c, src) in LP_EXTRA.items():
    b = open(os.path.join(WT, p), 'rb').read() if c is None else \
        subprocess.run(['git', '-C', REPO, 'show', f'{c}:{src or p}'], capture_output=True, check=True).stdout
    rec[p] = dict(source=f'{c}:{src or p}' if c else 'worktree', sha256=hashlib.sha256(b).hexdigest(), lp_bench=True)
    put(p, b)
open(os.path.join(OUT, 'hp13_sources.f'), 'w').write(''.join(f'{p}\n' for p in srcs))
json.dump(rec, open(os.path.join(OUT, 'MATERIALIZE.json'), 'w'), indent=1)
print('materialized', len(srcs), 'files; worktree-changed vs inventory:',
      [p for p, r in rec.items() if r.get('identical') is False])
