#!/usr/bin/env python3
"""One uncapped CURRENT station route, real ties and mapped receiver loads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
import run_abi3_physical_persistent as persistent

p = argparse.ArgumentParser()
p.add_argument('--run', type=Path, required=True)
a = p.parse_args()
run = a.run.resolve()
run.mkdir(parents=True, exist_ok=False)
manifest = json.loads((HERE / 'sources.json').read_text())
for path, digest in manifest['generated_pins'].items():
    assert hashlib.sha256((HERE / path).read_bytes()).hexdigest() == digest
shared = ROOT / 'tools/run_abi3_physical.py'
original = shared.read_text()
old = 'f"write_verilog -noattr {raw_netlist}"'
assert original.count(old) == 1
code = original.replace(old, 'f"write_verilog {raw_netlist}"')
# The old exact-host-map route bypassed ORFS synth.tcl's hilomap. Constants
# reached OpenROAD as implicit one_/zero_ power nets with logic consumers.
# Map them to the *actual* platform tie masters before stat/write_verilog;
# floorplan.tcl can then repair tie fanout normally. Do not relabel PG nets.
needle = '                "splitnets -ports",'
assert code.count(needle) == 1
code = code.replace(needle,
    '                "hilomap -singleton -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L",\n' + needle)
guard = 'if endpoint_netlist and metrics.get("sequential_cell_count", 0) < 270418:'
assert code.count(guard) == 1
code = code.replace(guard, 'if endpoint_netlist and metrics.get("sequential_cell_count", 0) < 5916:')
code = code.replace('Routed W11 endpoint netlist fell below the original full-size guard',
                    'Routed full NO2 CURRENT station fell below inherited actual full-state inventory')
driver = types.ModuleType('descartes_w2_current_driver')
driver.__file__ = str(shared)
sys.modules[driver.__name__] = driver
exec(compile(code, str(shared), 'exec'), driver.__dict__)
(run / 'adapter.json').write_text(json.dumps(dict(
    source_driver_sha256=hashlib.sha256(original.encode()).hexdigest(),
    effective_driver_sha256=hashlib.sha256(code.encode()).hexdigest(),
    attrs_preserved=True, tie_mapping='actual ASAP7 TIEHIx1_ASAP7_75t_R/H, TIELOx1_ASAP7_75t_R/L',
    constant_PG_relabeling=False, functional_replay=False,
    source_manifest_sha256=hashlib.sha256((HERE / 'sources.json').read_bytes()).hexdigest()), indent=2)+'\n')
base = ROOT / 'physical/hbm_die_abstracts_20261006/links/station_physical_20261006'
sdc = run / 'source_local.sdc'
native_synth = driver.run_synthesis


def synth(*args, **kwargs):
    result = native_synth(*args, **kwargs)
    work = args[3]
    mapped = result['netlist']
    text = mapped.read_text()
    if 'TIEHIx1_ASAP7_75t_R' not in text or 'TIELOx1_ASAP7_75t_R' not in text:
        raise driver.FlowError('actual platform tie mapping missing')
    loads = run / 'receiver'
    subprocess.run(['python3', str(base/'measure_receiver.py'), '--mapped', str(mapped),
                    '--out', str(loads), '--src', str(ROOT)], check=True, cwd=ROOT)
    subprocess.run(['python3', str(base/'make_component_sdc.py'), '--loads', str(loads),
                    '--NO', '2', '--out', str(sdc)], check=True, cwd=ROOT)
    (run/'mapped_inventory.json').write_text(json.dumps(result['record'], indent=2)+'\n')
    return result


def endpoint(block, work, case):
    assert block['parameters'] == dict(ENABLE=1, NO=2, REGISTERED_CURRENT=1)
    shutil.copyfile(work/'mapped.v', case/'w11_endpoint_mapped.v')
    shutil.copyfile(sdc, case/'source_local.sdc')
    return dict(mapped_netlist_sha256=driver.sha256_file(work/'mapped.v'),
                basis='exact full CURRENT station host map, attributes and physical tie cells retained; legacy filename only')


def pins(regions):
    patterns = {'^(clk_sm|por_n|in_.*|release_.*)$':'clk_sm por_n in_* release_*',
                '^(fclk_o|out_.*|ACK_.*)$':'fclk_o out_* ACK_*'}
    return '\n'.join('set_io_pin_constraint -region '+r['edge']+':* -pin_names {'+patterns[r['regex']]+'}' for r in regions)+'\n'


driver.run_synthesis = synth
driver.prepare_w11_orfs_endpoint_netlist = endpoint
driver.io_constraints_tcl = pins
rel = str(HERE.relative_to(ROOT))
argv = ['--view','asap7','--top','ot_hbm_native_frame_station']
for source in ('bank_legacy_static.sv','bank_current_static.sv','ot_hbm_native_station.sv','ot_hbm_native_frame_station.sv'):
    argv += ['--source', rel+'/'+source]
argv += ['--source','rtl/common/ot_fwd_link_stage.sv',
         '--source','physical/hbm_die_abstracts_20261006/links/ot_hbm_native_register_slice.sv',
         '--param','ENABLE=1','--param','NO=2','--param','REGISTERED_CURRENT=1',
         '--clock-port','clk_sm','--clock-period-ns','0.833333333',
         '--clock-uncertainty-ns','0.06','--clock-uncertainty-hold-ns','0.025',
         '--orfs-corner','WC','--hold-corners','WC,BC','--hold-margin-ns','0.01',
         '--core-utilization','38','--place-density','0.60',
         '--stages','synth,pnr','--keep-heavy-artifacts',
         '--orfs-var','NUM_CORES=16','--orfs-var','ADDER_MAP_FILE=',
         '--orfs-var','PLACE_PINS_ARGS=-min_distance 1 -min_distance_in_tracks',
         '--orfs-var','IO_PLACER_H=M4 M6','--orfs-var','IO_PLACER_V=M5 M7',
         '--orfs-var','CORE_ASPECT_RATIO=0.25','--orfs-var','SDC_FILE=/work/source_local.sdc',
         '--step-tcl','PRE_IO_PLACEMENT='+rel+'/pin_faces.tcl',
         '--step-tcl','PRE_CTS='+rel+'/forwarded_subtree.tcl',
         '--pin-region','^(clk_sm|por_n|in_.*|release_.*)$=bottom',
         '--pin-region','^(fclk_o|out_.*|ACK_.*)$=top',
         '--purpose','signoff_target','--nickname-tag','Descartes_CURRENT_NO2_H55',
         '--output',str(run/'physical.json')]
(run/'argv.json').write_text(json.dumps(argv, indent=2)+'\n')
os.environ.update(OT_ORFS_NUM_CORES='16',OPENTALLAS_ORFS_IMAGE='openroad/orfs:asap7lock')
try:
    rc = persistent.launch(driver, argv, workdir=run/'work', receipt=run/'launch.json')
except BaseException as exc:
    (run/'terminal.json').write_text(json.dumps(dict(status='FAILED_WORK_PRESERVED',
        reason=str(exc), physical_qualified=False), indent=2)+'\n')
    raise
else:
    (run/'terminal.json').write_text(json.dumps(dict(status='DRIVER_RETURNED',
        exit_code=rc, physical_record=str(run/'physical.json')), indent=2)+'\n')
    raise SystemExit(rc)
