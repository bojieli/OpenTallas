#!/usr/bin/env python3
"""Source-identical d017 R128/PQ screen in an expanded standalone slot."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
BASE = Path('physical/s81_pq_r128_expanded')
sys.path.insert(0, str(ROOT/'tools'))


def command(work, output):
    binding = json.loads((ROOT/BASE/'source_binding.json').read_text())
    for f in binding['files']:
        if hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest() != f['sha256']:
            raise ValueError('Pinned input changed: '+f['path'])
    model = json.loads((ROOT/BASE/'model.json').read_text())
    # The analytical model is generated and verified before pinning. Runtime
    # checks the emitted record hash above without importing unrelated designs.
    args = ['--view','asap7','--top','ot_v41_pqc_spine_screen']
    for f in binding['files']:
        if f['role'] == 'RTL': args += ['--source',f['path']]
    args += ['--clock-period-ns','.770','--clock-uncertainty-ns','.060',
        '--clock-uncertainty-hold-ns','.025','--corner','TT','--orfs-corner','WC',
        '--hold-corners','WC,BC','--max-transition-ns','--max-fanout','32',
        '--orfs-var','ADDER_MAP_FILE=','--orfs-var','NUM_CORES=16',
        '--orfs-var','VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS',
        '--orfs-var','SYNTH_KEEP_MODULES=ot_dsrom_aq12m_mul ot_dsrom_aq12m',
        '--sdc-append',str(BASE/'io_budget_r128.sdc'),
        '--slew-margin-percent','40','--hold-margin-ns','.040',
        '--param','PQ=1','--param','R=128','--stages','pnr',
        '--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited',
        '--keep-heavy-artifacts','--nickname-tag','s81_pq_r128_expanded',
        '--keep-workdir',str(work),'--output',str(output)]
    for stage, name in [('PRE_CTS','io_ref_pre.tcl'),('PRE_GLOBAL_ROUTE','io_ref_pre.tcl'),
                        ('POST_CTS','io_ref_post.tcl'),('POST_GLOBAL_ROUTE','io_ref_post.tcl')]:
        args += ['--step-tcl',stage+'='+str(BASE/name)]
    args += ['--die-area','0','0']+[str(v) for v in model['geometry']['die_um']]
    args += ['--core-area']+[str(v) for v in model['geometry']['core_box_um']]
    return args


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--pnr-stop-after')
    a=p.parse_args(); args=command(a.work,a.output)
    if a.pnr_stop_after: args += ['--pnr-stop-after',a.pnr_stop_after]
    import run_abi3_physical as flow
    flow.build_parser().parse_args(args)
    if a.prepare_only:
        print(json.dumps(dict(status='PREPARED_NOT_RUN',argv=args,physical_closed=False),indent=2));return 0
    rc=flow.main(args,synth_timeout=None,flow_timeout=None)
    if rc or a.pnr_stop_after: return rc
    return subprocess.call([sys.executable,str(ROOT/'tools/w18/corner_sta.py'),
        '--orfs-dir',str(a.work/'orfs'),'--post-sdc',str(BASE/'signoff_r128.sdc'),
        '--output',str(a.output.with_name(a.output.stem+'_corner_sta.json'))],cwd=ROOT)

if __name__ == '__main__': raise SystemExit(main())
