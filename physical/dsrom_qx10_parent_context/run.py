#!/usr/bin/env python3
"""One pinned full QX10/native-parent physical job; invoke through host guard."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE='physical/dsrom_qx10_parent_context'
RTL=[f'rtl/v41rom/{n}.sv' for n in (
    'ot_v41_rom_elem_q_qx_w10','ot_v41_kreg','ot_v41_chain3',
    'ot_v41_rom_elem_w10','ot_v41_bterm','ot_v41_chain','ot_v41_segtree','ot_v41_bf16_lanes',
    'ot_v41_fadd','ot_v41_bterm2_w10','ot_v41_chain2','ot_v41_segtree2','ot_v41_bf16_lanes2',
    'ot_v41_bterm3_w10','ot_v41_segtree3','ot_v41_segtree4','ot_v41_segtree5')]
RTL += [f'{BASE}/selected_0032/{n}.sv' for n in (
    'ot_v41_rom_elem_qx_w10','ot_v41_bterm4_w10','ot_v41_chain4','ot_v41_fadd2')]
RTL += [f'rtl/hdc/{n}.sv' for n in ('ot_hdc_fpu','ot_hdc_fp32_mul_pipe','ot_hdc_delay','ot_hdc_cg')]
RTL += ['rtl/proto/ot_fp32_add_rne_pipe.sv','rtl/common/ot_prefix.sv',
        f'{BASE}/parent_loader/ot_v41_pair_pq_ld_frontend.sv',
        'rtl/v41rom/ot_v41_ret.sv','rtl/v41die/ot_v41_retn_w17w10.sv',
        f'{BASE}/ot_v41_qx10_native_parent.sv']
ROM=[f'physical/asap7_memory_macros/{n}/{n}_bb.v' for n in ('ot_rom_8192x274_m8','ot_rom_4096x274_m8')]


def command(out, boundary_hold=False):
    args=[sys.executable,'tools/run_abi3_physical_persistent.py',
          '--persistent-workdir',str(out/'work'),'--launch-receipt',str(out/'receipt.json'),
          '--view','asap7','--top','ot_v41_qx10_native_parent']
    for src in RTL+ROM:args += ['--source',src]
    args += ['--param','QX=10','--clock-period-ns','0.833333333333',
             '--clock-uncertainty-ns','.060','--clock-uncertainty-hold-ns','.025',
             '--core-input-delay-min-ns','.360','--core-input-delay-max-ns','.727',
             '--output-delay-min-ns','.360','--output-delay-max-ns','.727',
             '--sdc-append',f'{BASE}/boundary.sdc','--stages','pnr',
             '--die-area','0','0','1040.256','239.76',
             '--core-area','2.16','2.16','1038.096','237.60',
             '--place-density','.6','--macro-place-halo','2','2',
             '--macro-view','ot_rom_4096x274_m8=physical/asap7_memory_macros/ot_rom_4096x274_m8',
             '--max-transition-ns','.32','--slew-margin-percent','40','--hold-margin-ns','.025',
             '--orfs-corner','WC','--hold-corners','WC,BC','--pnr-stop-after','finish',
             '--orfs-var','SYNTH_HDL_FRONTEND=slang',
             '--orfs-var','PDN_TCL=/src/tools/chip_assembly/tcl/pdn_w10_elem_m7_ir.tcl',
             '--orfs-var','FASTROUTE_TCL=/src/physical/dsrom_v9_parent_context/fastroute.tcl',
             '--orfs-var','ROUTING_LAYER_ADJUSTMENT=0.22','--orfs-var','SETUP_SLACK_MARGIN=15',
             '--orfs-var','CTS_CLUSTER_SIZE=30','--orfs-var','CTS_CLUSTER_DIAMETER=50',
             '--orfs-var','CTS_BUF_DISTANCE=60','--routing-layers','M2','M8',
             '--step-tcl',f'POST_PDN={BASE}/regions.tcl',
             '--step-tcl',f'POST_MACRO_PLACE={BASE}/macros.tcl',
             '--step-tcl','POST_TAPCELL=physical/common/ot_macro_track_assert_hook.tcl',
             '--step-tcl',f'PRE_CTS={BASE}/clock.tcl','--step-tcl',f'POST_CTS={BASE}/clock.tcl',
             '--step-tcl',f'PRE_GLOBAL_ROUTE={BASE}/replay_checks.tcl',
             '--keep-heavy-artifacts','--output',str(out/'physical.json')]
    if boundary_hold:
        args += ['--step-tcl',f'POST_DETAIL_PLACE={BASE}/hold_boundary.tcl']
    return args


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--print',action='store_true')
    ap.add_argument('--lint-only',action='store_true')
    ap.add_argument('--phase',choices=('all','smoke','physical'),default='all')
    ap.add_argument('--boundary-hold',action='store_true')
    a=ap.parse_args();out=a.out.resolve()
    model_name='boundary_hold_model.json' if a.boundary_hold else 'model.json'
    model=json.loads((ROOT/'results/uarch/dsrom_qx10_parent_context_20261005'/model_name).read_text())
    if not model['full_context_build_ready']:raise SystemExit('existing model vetoes joined context')
    actual=hashlib.sha256((ROOT/f'{BASE}/selected_0032/ot_v41_rom_elem_qx_w10.sv').read_bytes()).hexdigest()
    if actual!=model['source']['engine_sha256']:raise SystemExit('selected 0032 engine changed')
    if a.print:
        print(json.dumps(command(out,a.boundary_hold),indent=2));raise SystemExit(0)
    if a.lint_only:
        verilator=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
        raise SystemExit(subprocess.run([str(verilator),'--lint-only','-Wno-fatal','-Wno-lint','-Wno-style',
            '--top-module','ot_v41_qx10_native_parent','-GQX=10',*RTL,
            *[p.replace('_bb.v','.v') for p in ROM]],cwd=ROOT).returncode)
    pins=json.loads((ROOT/'results/uarch/dsrom_qx10_parent_context_20261005/source_inventory.json').read_text())
    for path,digest in pins['files'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise SystemExit(f'pinned joined-context source changed: {path}')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():
        raise SystemExit('long job requires its own clean pinned source worktree')
    out.mkdir(parents=True,exist_ok=True)
    # One directed minimum integration check before physical execution. No
    # checkpoint replay, random campaign, or whole S81 simulation.
    verilator=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    smoke=[str(verilator),'--binary','--timing','-Wno-fatal','-Wno-lint','-Wno-style',
           '--top-module','tb_native_parent','--Mdir',str(out/'smoke_objects'),'-j','1','-CFLAGS','-O1',
           *RTL,*[p.replace('_bb.v','.v') for p in ROM],f'{BASE}/tb_native_parent.sv']
    if a.phase!='physical':
        if (out/'smoke.rc').exists():raise SystemExit('smoke has an actual terminal; preserve it')
        (out/'smoke.command.json').write_text(json.dumps(smoke)+'\n')
        with (out/'smoke.build.log').open('w') as log:
            rc=subprocess.run(smoke,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
        (out/'smoke.build.rc').write_text(str(rc)+'\n')
        if rc:raise SystemExit(rc)
        with (out/'smoke.log').open('w') as log:
            rc=subprocess.run([str(out/'smoke_objects/Vtb_native_parent')],cwd=out,
                              stdout=log,stderr=subprocess.STDOUT).returncode
        (out/'smoke.rc').write_text(str(rc)+'\n')
        if rc:raise SystemExit(rc)
        if a.phase=='smoke':raise SystemExit(0)
    if not (out/'smoke.rc').exists() or (out/'smoke.rc').read_text().strip()!='0':
        raise SystemExit('minimum native parent semantic gate is not PASS')
    os.environ['OT_ORFS_NUM_CORES']='4'
    raise SystemExit(subprocess.run(command(out,a.boundary_hold),cwd=ROOT).returncode)
