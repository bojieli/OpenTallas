#!/usr/bin/env python3
"""Full-shape WINDOW physical characterization using the existing all-corner driver.

No I/O waiver. This component run cannot replace a source-qualified enclosing
S81 clock/load/slot check; that remains explicitly pending in the model.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
 'rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_pipeline_context.sv',
 'rtl/dsrom_sys/s81_window_la/ot_dsrom_window_attn_source_la.sv',
 *[f'rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_{n}_pipeline.sv' for n in ('source','stage','writer','row_merge')],
 'rtl/dsrom_sys/s81_window_la/ot_dsrom_window_la_stage.sv',
 'rtl/dsrom_sys/s81_window_la/ot_dsrom_hbm_wmux.sv',
 'rtl/dsrom_sys/s81_window_la/ot_dsrom_window_stream_la_s81.sv',
 'rtl/chip/window_owner_safe/ot_chip_v41x_window_attn_source_owner_safe.sv',
 'rtl/chip/window_owner_safe/ot_chip_v41x_window_kv_prefetch_owner_safe.sv',
 *[f'rtl/chip/ot_chip_v41x_window_{n}.sv' for n in ('refill_schedule','retention','row_codec','stage4','stream')],
 'rtl/chip/ot_chip_v41x_attn_row_merge.sv']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--pnr-stop-after',choices=('floorplan','cts','finish'),default='finish',
                   help='Existing driver phase boundary; floorplan obtains the changed full-shape SS map before parent allocation is ready.')
    a=p.parse_args(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    cmd=['python3','tools/run_abi3_physical.py','--view','asap7','--top','ot_dsrom_window_pipeline_context',
         *[x for s in SOURCES for x in ('--source',s)],
         '--clock-period-ns','0.8333333333333333','--clock-uncertainty-ns','0.060',
         '--clock-uncertainty-hold-ns','0.025','--orfs-corner','WC','--hold-corners','WC,BC',
         '--io-delay-fraction','0.2','--stages','pnr',
         '--pnr-stop-after',a.pnr_stop_after,
         '--die-area','0','0','1550','1550','--core-area','5','5','1545','1545',
         '--place-density','0.5','--orfs-var','ADDER_MAP_FILE=',
         '--orfs-var','IO_PLACER_H=M4 M6 M8',
         '--orfs-var','IO_PLACER_V=M5 M7 M9',
         '--routing-layers','M2','M9',
         '--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited',
         '--purpose','characterization','--nickname-tag','window_full_pipeline_r1',
         '--keep-workdir',str(out/'work'),'--output',str(out/'physical.json')]
    sha=lambda f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
    rec=dict(command=cmd,source_sha256={s:sha(s) for s in SOURCES},
             driver_sha256=sha('tools/run_abi3_physical.py'),
             allcorner_spef_helper_sha256=sha('tools/orfs_allcorner_spef.py'),
             IO_waiver=False,period_ps=1000/1.2,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
             memory='fully priced actual FF implementation; actual corner Liberty clkQ/load and routed captures',
             clock_source='actual shared WINDOW streaming clk pin at 1.2GHz',
             purpose='full component characterization; actual enclosing parent CTS/IO/slot qualification pending',
             parent_context_proof=False,default_view_output_load_fF=3.898,
             actual_parent_loads=False,adoption=False)
    rec.update(IO_pin_layers={'horizontal':['M4','M6','M8'],'vertical':['M5','M7','M9']},
               IO_min_distance_tracks=2,
               pin_access_basis='actual unchanged-source full-shape placed-ODB probe:151588 legal positions for70354 signal IO; no CTS/route/parent credit',
               physical_phase_boundary=a.pnr_stop_after,
               synthesis_basis='ORFS WC/SS mapping once; omit redundant host TT mapping; original TT evidence retained')
    (out/'recipe.json').write_text(json.dumps(rec,indent=2)+'\n')
    if a.execute:
        env=dict(os.environ,OT_ORFS_NUM_CORES='16')
        r=subprocess.run(cmd,cwd=ROOT,env=env)
        (out/'terminal.exit').write_text(str(r.returncode)+'\n')
        raise SystemExit(r.returncode)


if __name__=='__main__': main()
