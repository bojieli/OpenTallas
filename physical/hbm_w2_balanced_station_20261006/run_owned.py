#!/usr/bin/env python3
"""One uncapped CHECK station route, real ties and mapped receiver loads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
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
p.add_argument('--reuse-map', type=Path,
               help='Completed map from the same pinned source; never synthesize it twice')
p.add_argument('--core-width', type=float, default=440.0)
p.add_argument('--core-height', type=float, default=110.0)
p.add_argument('--place-density', type=float, default=0.60)
p.add_argument('--tag', default='item6_W2_balanced')
a = p.parse_args()
assert a.core_width > 0 and a.core_height > 0
assert 0 < a.place_density <= 0.60
core_area = a.core_width * a.core_height
run = a.run.resolve()
run.mkdir(parents=True, exist_ok=False)
image = os.environ.get('OPENTALLAS_ORFS_IMAGE', 'openroad/orfs:asap7lock')
os.environ.update(OT_ORFS_NUM_CORES='16', OPENTALLAS_ORFS_IMAGE=image)
# Resolve the installed platform make variables, including its selected VT,
# rather than assuming library pin spellings or reading an unset host env.
query = 'print-ties:;@printf "%s\\n" "$(TIEHI_CELL_AND_PORT)" "$(TIELO_CELL_AND_PORT)"'
tie_command = ['docker','run','--rm','--entrypoint','make',image,
    '--no-print-directory','-s','-f','/OpenROAD-flow-scripts/flow/platforms/asap7/config.mk',
    'PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7', '--eval='+query, 'print-ties']
resolved = subprocess.check_output(tie_command, text=True).strip().splitlines()
assert len(resolved) == 2
hi, lo = [line.split() for line in resolved]
assert len(hi) == len(lo) == 2
assert all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', token) for token in hi+lo)
tie_map = f'hilomap -singleton -hicell {hi[0]} {hi[1]} -locell {lo[0]} {lo[1]}'
(run/'platform_ties.json').write_text(json.dumps(dict(
    TIEHI_CELL_AND_PORT=hi, TIELO_CELL_AND_PORT=lo, command=tie_command,
    installed_image_id=subprocess.check_output(['docker','image','inspect',image,
        '--format','{{.Id}}'], text=True).strip()), indent=2)+'\n')
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
    '                '+repr(tie_map)+',\n' + needle)
guard = 'if endpoint_netlist and metrics.get("sequential_cell_count", 0) < 270418:'
assert code.count(guard) == 1
code = code.replace(guard, 'if endpoint_netlist and metrics.get("sequential_cell_count", 0) < 5916:')
code = code.replace('Routed W11 endpoint netlist fell below the original full-size guard',
                    'Routed full NO2 CURRENT station fell below inherited actual full-state inventory')
driver = types.ModuleType('descartes_w2_current_driver')
driver.__file__ = str(shared)
sys.modules[driver.__name__] = driver
exec(compile(code, str(shared), 'exec'), driver.__dict__)
# The kept forwarding hierarchy makes Yosys emit both a hierarchy summary and
# an expanded cell table. The shared parser counts summary rows as macro cells.
# Use only the final expanded table, whose four physical inverter cells are
# already included, and keep the raw report as evidence.
native_parse_stat = driver.parse_stat
def station_stat(text):
    hierarchy = text.split('=== design hierarchy ===', 1)[1]
    marker = '+----------Count including submodules.'
    table = hierarchy[hierarchy.rindex(marker):]
    record = native_parse_stat(table)
    record['per_cell'].pop('submodules', None)
    record['per_cell'].pop('ot_fwd_clk_inv', None)
    count = int(re.search(r'^\s*(\d+)\s+\S+\s+cells\s*$', table, re.M).group(1))
    assert sum(v['count'] for v in record['per_cell'].values()) == count
    record['chip_area_um2'] = float(re.search(
        r"Chip area for top module .*?: ([0-9.]+)", table).group(1))
    return record
driver.parse_stat = station_stat
(run / 'adapter.json').write_text(json.dumps(dict(
    source_driver_sha256=hashlib.sha256(original.encode()).hexdigest(),
    effective_driver_sha256=hashlib.sha256(code.encode()).hexdigest(),
    attrs_preserved=True, tie_mapping=tie_map,
    constant_PG_relabeling=False, functional_replay=False,
    source_manifest_sha256=hashlib.sha256((HERE / 'sources.json').read_bytes()).hexdigest()), indent=2)+'\n')
base = ROOT / 'physical/hbm_die_abstracts_20261006/links/station_physical_20261006'
sdc = run / 'source_local.sdc'
native_synth = driver.run_synthesis


def synth(*args, **kwargs):
    work = args[3]
    if a.reuse_map:
        cached = a.reuse_map.resolve()
        old = json.loads((cached.parent/'physical.json').read_text())
        assert old['design']['parameters'] == manifest['parameters']
        for source in old['design']['sources']:
            assert driver.sha256_file(ROOT/source['path']) == source['sha256'], 'cached source differs'
        for lib in old['corner']['liberty']:
            assert driver.sha256_file(Path(lib['path'])) == lib['sha256'], 'cached mapping library differs'
        assert tie_map in (cached/'synth.ys').read_text(), 'cached platform tie mapping differs'
        original_run = driver.run
        def consume(cmd, *aa, **kk):
            if cmd[:1] == [str(driver.YOSYS)]:
                for name in ('mapped.raw.v','stat.txt'):
                    shutil.copyfile(cached/name, work/name)
                return subprocess.CompletedProcess(cmd, 0, (cached/'yosys.log').read_text(), '')
            return original_run(cmd, *aa, **kk)
        driver.run = consume
        try:
            # Reconstruct the original inventory with the shared parser. The
            # newly emitted recipe is NOT executed; the source-pinned original
            # raw map, stats and tool log are consumed byte-for-byte.
            result = native_synth(*args, **kwargs)
        finally:
            driver.run = original_run
        assert driver.sha256_file(result['netlist']) == driver.sha256_file(cached/'mapped.v')
        result['record']['reused_completed_map'] = dict(directory=str(cached),
            mapped_sha256=driver.sha256_file(cached/'mapped.v'),
            original_synth_script_sha256=driver.sha256_file(cached/'synth.ys'),
            original_tool_log_sha256=driver.sha256_file(cached/'yosys.log'),
            yosys_or_ABC_relaunched=False)
    else:
        result = native_synth(*args, **kwargs)
    (run/'mapped_slot_budget.json').write_text(json.dumps(dict(
        actual_map_area_um2=result['record']['chip_area_um2'],
        actual_map_FF=result['record']['sequential_cell_count'],
        requested_core_area_um2=core_area,
        bare_map_utilization_percent=100*result['record']['chip_area_um2']/core_area,
        target_buffered_utilization_percent=[55,60],
        max_cell_area_at_60pct_um2=core_area*.60,
        mapped_body_is_not_buffered_fit=True,physical_qualified=False),indent=2)+'\n')
    mapped = result['netlist']
    text = mapped.read_text()
    if hi[0] not in text:
        raise driver.FlowError('actual high constant tie mapping missing')
    # This full CURRENT map needs a high tie only. A low tie may be absent
    # because every constant-zero sink was optimized away or uses its inverse.
    # Do not reject a correctly mapped netlist for an unused cell type.
    (run/'mapped_inventory.json').write_text(json.dumps(result['record'], indent=2)+'\n')
    loads = run / 'receiver'
    subprocess.run(['python3', str(base/'measure_receiver.py'), '--mapped', str(mapped),
                    '--out', str(loads), '--src', str(ROOT)], check=True, cwd=ROOT)
    subprocess.run(['python3', str(base/'make_component_sdc.py'), '--loads', str(loads),
                    '--NO', '2', '--out', str(sdc)], check=True, cwd=ROOT)
    return result


def endpoint(block, work, case):
    assert block['parameters'] == dict(ENABLE=1, NO=2, REGISTERED_CURRENT=1, REGISTERED_CHECK=1)
    shutil.copyfile(work/'mapped.v', case/'w11_endpoint_mapped.v')
    shutil.copyfile(sdc, case/'source_local.sdc')
    return dict(mapped_netlist_sha256=driver.sha256_file(work/'mapped.v'),
                basis='exact full CHECK station host map, attributes and physical tie cells retained; legacy filename only')


def pins(regions):
    patterns = {'^(clk_sm|por_n|in_.*|release_.*)$':'clk_sm por_n in_* release_*',
                '^(fclk_o|out_.*|ACK_.*)$':'fclk_o out_* ACK_*'}
    return '\n'.join('set_io_pin_constraint -region '+r['edge']+':* -pin_names {'+patterns[r['regex']]+'}' for r in regions)+'\n'


driver.run_synthesis = synth
driver.prepare_w11_orfs_endpoint_netlist = endpoint
driver.io_constraints_tcl = pins
rel = str(HERE.relative_to(ROOT))
argv = ['--view','asap7','--top','ot_hbm_native_frame_station']
for source in ('bank_legacy_static.sv','bank_current_static.sv','bank_check_static.sv','ot_hbm_native_station.sv','ot_hbm_native_frame_station.sv'):
    argv += ['--source', rel+'/'+source]
argv += ['--source','rtl/common/ot_fwd_link_stage.sv',
         '--source','physical/hbm_die_abstracts_20261006/links/ot_hbm_native_register_slice.sv',
         '--param','ENABLE=1','--param','NO=2','--param','REGISTERED_CURRENT=1','--param','REGISTERED_CHECK=1',
         '--clock-port','clk_sm','--clock-period-ns','0.833333333',
         '--clock-uncertainty-ns','0.06','--clock-uncertainty-hold-ns','0.025',
         '--orfs-corner','WC','--hold-corners','WC,BC','--hold-margin-ns','0.01',
         '--die-area','0','0',str(a.core_width+4.104),str(a.core_height+4.32),
         '--core-area','2.052','2.16',str(a.core_width+2.052),str(a.core_height+2.16),
         '--place-density',str(a.place_density),
         '--stages','synth,pnr','--keep-heavy-artifacts',
         '--orfs-var','NUM_CORES=16','--orfs-var','ADDER_MAP_FILE=',
         '--orfs-var','PLACE_PINS_ARGS=-min_distance 1 -min_distance_in_tracks',
         '--orfs-var','IO_PLACER_H=M4 M6','--orfs-var','IO_PLACER_V=M5 M7',
         '--orfs-var','CORE_ASPECT_RATIO=0.25','--orfs-var','SDC_FILE=/work/source_local.sdc',
         '--step-tcl','PRE_IO_PLACEMENT='+rel+'/pin_faces.tcl',
         '--step-tcl','PRE_CTS='+rel+'/forwarded_subtree.tcl',
         '--pin-region','^(clk_sm|por_n|in_.*|release_.*)$=bottom',
         '--pin-region','^(fclk_o|out_.*|ACK_.*)$=top',
         '--purpose','signoff_target','--nickname-tag',a.tag,
         '--output',str(run/'physical.json')]
(run/'argv.json').write_text(json.dumps(argv, indent=2)+'\n')
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
