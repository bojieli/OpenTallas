#!/usr/bin/env python3
"""Run under ot-run: run.py REPO NEW_SCRATCH. No RTL/reset/LEC changes."""
import json, os, pathlib, shutil, subprocess, sys
repo, root = map(pathlib.Path, sys.argv[1:3])
root.mkdir(parents=True, exist_ok=False)
rtl = pathlib.Path(__file__).with_name('cut_vehicle.sv')
seq = '/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib'
image = os.environ.get('OT_ORFS_IMAGE', 'openroad/orfs:asap7lock')
env = {k:v for k,v in os.environ.items() if k not in ('OT_LEC_RESET_CYCLES','OT_LEC_RAW_BASE_STEPS','OT_LEC_RESET_CONTRACT')}
results = {}
for name in ('folded', 'native_named', 'native_wrongstage'):
    kit = root/name
    (kit/'rtl').mkdir(parents=True)
    shutil.copy2(rtl, kit/'rtl/cut.sv')
    netlist = kit/'run/results/asap7/cut_vehicle/base/1_2_yosys.v'
    netlist.parent.mkdir(parents=True)
    (kit/'config.mk').write_text('export DESIGN_NAME = cut_vehicle\nexport PLATFORM = asap7\nexport VERILOG_FILES = /work/rtl/cut.sv\nexport VERILOG_INCLUDE_DIRS = /work/rtl\nexport VERILOG_DEFINES = -DSYNTHESIS\nexport SYNTH_HDL_FRONTEND = verilog\n')
    keep = '' if name == 'folded' else '-keepdc'
    ys = f'read_verilog -sv /work/rtl/cut.sv; hierarchy -top cut_vehicle; proc; flatten; opt -full {keep}; techmap; opt -full {keep}; rename -wire; dfflibmap -liberty {seq}; opt_clean; rename -wire; write_verilog -noattr /work/run/results/asap7/cut_vehicle/base/1_2_yosys.v'
    with (kit/'synth.log').open('w') as log:
        subprocess.run(['docker','run','--rm','--cpus','2','--memory','4g','--memory-swap','4g','-v',f'{kit}:/work','-w','/OpenROAD-flow-scripts/flow',image,'bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec yosys -Q -T -p "$1"','bash',ys],check=True,stdout=log,stderr=subprocess.STDOUT)
    if name == 'native_wrongstage':
        s = netlist.read_text()
        old = '.D(\\g[4].u.g_r.r [0])'
        assert s.count(old) == 1
        netlist.write_text(s.replace(old, '.D(\\g[3].u.g_r.r [0])'))
    with (kit/'lec_run.log').open('w') as log:
        subprocess.run([sys.executable,str(repo/'tools/die_plan/lec.py'),str(kit),'--mem','4'],env=env,stdout=log,stderr=subprocess.STDOUT)
    j = json.loads((kit/'lec/lec.json').read_text())
    assert j['reset_contract']['used'] == 4 and j['reset_contract']['contract'] is None
    results[name] = {k:j[k] for k in ('verdict','counts','reset_contract','reason')}
assert results['native_named']['verdict'] == 'EQUIVALENT', results
assert results['native_wrongstage']['verdict'] == 'NOT EQUIVALENT', results
assert results['folded']['verdict'] != 'EQUIVALENT', results
(root/'result.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
