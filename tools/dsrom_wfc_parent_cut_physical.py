#!/usr/bin/env python3
"""One full-shape native parent cut; all external ports remain timed.

Run only after Kant's fresh CPU/RAM/disk checks and unchanged admission.
SS/FF on the actual final ODB/SPEF, no inferred producer clock insertion,
IO false paths, uncertainty relaxation or wall-time limits. The retained
external 20%-period contract is conditional until actual callers are bound.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['rtl/rom/wavefront/context/ot_dsrom_wfc_parent_cut.sv',
           'rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv',
           'rtl/rom/ot_rom_fabric_router.sv']
STA = r'''
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(WFC_LIB)_*.lib*]] { read_liberty $f }
read_db $::env(WFC_ODB)
read_sdc $::env(WFC_SDC)
read_spef $::env(WFC_SPEF)
set_propagated_clock [all_clocks]
puts "WFC_CONTEXT external_contract_20percent actual_external_producers_unbound"
puts "WFC_WNS setup [sta::worst_slack_cmd max] hold [sta::worst_slack_cmd min]"
report_checks -path_delay max -format full_clock_expanded -digits 4
report_checks -path_delay min -format full_clock_expanded -digits 4
report_check_types -violators -max_slew -max_capacitance -max_fanout -digits 4
foreach {name pattern} {
  configuration {cfg_*}
  caller_completion {core_done core_next_* c8_* coll_busy}
  link {in_* out_* bl_* rcfg_*}
  VM_prompt {vm_* pr_*}
  controller_core {core_start core_token* core_pos* core_user* kv_base*}
} {
  set pins [get_ports $pattern]
  puts "WFC_CLASS $name"
  report_checks -from $pins -path_delay max -format full_clock_expanded -digits 4
  report_checks -to $pins -path_delay max -format full_clock_expanded -digits 4
  report_checks -from $pins -path_delay min -format full_clock_expanded -digits 4
  report_checks -to $pins -path_delay min -format full_clock_expanded -digits 4
}
puts "WFC_DONE"
'''


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def route(source, output):
    output.mkdir(parents=True, exist_ok=False)
    model_path = ROOT/f'results/uarch/dsrom_wfc_decoded_read_20261005/physical_cut_s{source}_model.json'
    model = json.loads(model_path.read_text())
    if not (model['local_characterization_slot_fit'] and model['analytical_tracks_fit']):
        raise RuntimeError('unified model does not fit the dedicated cut')
    exact = json.loads((ROOT/'results/rtl/dsrom_wfc_decoded_read_20261005/full_shape/record.json').read_text())
    for path in SOURCES:
        if path in exact['source_sha256'] and sha(ROOT/path) != exact['source_sha256'][path]:
            raise RuntimeError(f'changed exact-passed controller: {path}')
    params = dict(WAVE=1, WIN=6, MAXU=866, USER_W=10, FLIT=512, NW=21,
                  AW=30, VWA=15, KVW=32768, SOURCE=source, XWORDS=41 if source else 46,
                  RXWORDS=41, SEND_HIDDEN=1, HID_DEST=1, FWD_TOKEN=1,
                  DECODED_READ=1, LOCAL_CONTROL=0)
    cmd = ['python3',str(ROOT/'tools/run_abi3_physical.py'),
           '--view','asap7','--top','ot_dsrom_wfc_parent_cut',
           '--clock-period-ns','0.833','--clock-uncertainty-ns','0.060',
           '--clock-uncertainty-hold-ns','0.025','--orfs-corner','WC',
           '--hold-corners','WC,BC','--stages','pnr','--io-delay-fraction','0.2',
           '--max-transition-ns','library','--max-fanout','32',
           '--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited',
           '--nickname-tag',f'wfc_context_s{source}',
           '--keep-workdir',str(output/'work'),'--output',str(output/'physical.json'),
           '--die-area',*[str(v) for v in model['die_area_um']],
           '--core-area',*[str(v) for v in model['core_area_um']],
           '--routing-layers','M2','M6',
           '--orfs-var','ABC_AREA=0','--orfs-var','ADDER_MAP_FILE=']
    for path in SOURCES:
        cmd += ['--source',path]
    for k,v in params.items():
        cmd += ['--param',f'{k}={v}']
    os.environ['OT_ORFS_NUM_CORES']='20'
    pins={p:sha(ROOT/p) for p in SOURCES + ['tools/run_abi3_physical.py','tools/orfs_allcorner_spef.py']}
    (output/'route_args.json').write_text(json.dumps(dict(argv=cmd,parameters=params,
        source_sha256=pins,model=model),indent=2)+'\n')
    with (output/'route.log').open('w') as f:
        rc=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
    finals=list((output/'work').rglob('6_final.odb'))
    record=dict(route_exit=rc,source_sha256=pins,parameters=params,model=model,
                actual_parent_context_qualified=False,adopted=False,
                external_producer_contract='20% period, unchanged; actual caller/config/VM/prompt clocks and selected slot unbound')
    if len(finals)==1:
        odb=finals[0]; mount=odb.parents[4]
        script=mount/'wfc_context_sta.tcl';script.write_text(STA)
        artifacts=[odb,odb.with_suffix('.spef'),odb.with_suffix('.sdc')]
        record['artifacts_sha256']={p.name:sha(p) for p in artifacts}
        corners={}
        for lib in ['SS','FF']:
            args=['docker','run','--rm','-v',f'{mount}:/work','-e',f'WFC_LIB={lib}']
            for key,p in zip(['ODB','SPEF','SDC'],artifacts):
                args += ['-e',f'WFC_{key}=/work/{p.relative_to(mount)}']
            args += ['openroad/orfs:latest','bash','-lc',
                     'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /work/wfc_context_sta.tcl']
            proc=subprocess.run(args,capture_output=True,text=True)
            text=proc.stdout+proc.stderr
            (output/f'context_{lib}.log').write_text(text)
            item=dict(exit=proc.returncode,completed='WFC_DONE' in text)
            m=re.search(r'WFC_WNS setup (\S+) hold (\S+)',text)
            if m:
                item.update(setup_wns_ps=float(m[1])*1e12,hold_wns_ps=float(m[2])*1e12)
            corners[lib]=item
        record['corners']=corners
        physical=json.loads((output/'physical.json').read_text())
        record['physical_design']=physical['design']
        timing=all(c['completed'] and c['exit']==0 and c.get('setup_wns_ps',-1)>=0
                   and c.get('hold_wns_ps',-1)>=0 for c in corners.values())
        record['routed_cut_timing_met']=timing
        record['verdict']='PASS_CONDITIONAL_ROUTED_CUT_TIMING_ONLY' if timing else 'FAIL_ROUTED_CONTEXT_CUT'
    else:
        record['verdict']='INCOMPLETE_ROUTE_NO_SIGNOFF'
    record['source_unchanged']=all(sha(ROOT/p)==v for p,v in pins.items())
    (output/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    for source in [0,1]:
        result=route(source,args.output/f's{source}')
        print(source,result['verdict'],flush=True)
        # A failure is retained; SOURCE1 remains a distinct mandatory vehicle.
    (args.output/'collector.exit').write_text('0\n')


if __name__=='__main__':
    main()
