#!/usr/bin/env python3
"""ONE route of the REGISTERED_BOUNDARY W2 station (NO2 or NO3).

Routed against make_sdc.py at --period-ps (770 by default: over-constrained),
signed off separately at 833.333 ps with the measured insertion. Host map
keeps attributes and kept hierarchy (copies are never merged); physical tie
cells as the installed platform resolves them; placement density is explicit
(PLACE_DENSITY_LB_ADDON disabled so the requested density is the one used).
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'tools'))
import run_abi3_physical_persistent as persistent

p = argparse.ArgumentParser()
p.add_argument('--run', type=Path, required=True)
p.add_argument('--no', type=int, choices=(2, 3), required=True)
p.add_argument('--core-width', type=float, required=True)
p.add_argument('--core-height', type=float, required=True)
p.add_argument('--place-density', type=float, default=0.50)
p.add_argument('--period-ps', type=float, default=770.0)
p.add_argument('--l-max', type=float, default=510.0)
p.add_argument('--l-min', type=float, default=440.0)
p.add_argument('--l-ff-min', type=float, default=280.0)
p.add_argument('--l-ff-max', type=float, default=330.0)
p.add_argument('--min-ff', type=int, default=20000)
p.add_argument('--threads', type=int, default=16)
p.add_argument('--tag', default='tk_W2_rb')
p.add_argument('--safe', action='store_true', help='SAFE=1 station (registered permission decision)')
p.add_argument('--post-route-ff-hold', action='store_true',
               help='SS-only setup optimization at CTS/GRT; strict FF hold repair/signoff remains required after route')
p.add_argument('--hold-margin-ns', type=float, default=0.01)
a, passthrough = p.parse_known_args()
for k, e in (('l_max', 'CK_SS_MAX'), ('l_min', 'CK_SS_MIN'), ('l_ff_min', 'CK_FF_MIN'), ('l_ff_max', 'CK_FF_MAX')):
    if os.environ.get(e):
        setattr(a, k, float(os.environ[e]))  # measured insertion from the closure-loop calibrate stage
run = a.run.resolve(); run.mkdir(parents=True, exist_ok=False)
image = os.environ.get('OPENTALLAS_ORFS_IMAGE', 'openroad/orfs:asap7lock')
os.environ.update(OT_ORFS_NUM_CORES=str(a.threads), OPENTALLAS_ORFS_IMAGE=image)
query = 'print-ties:;@printf "%s\\n" "$(TIEHI_CELL_AND_PORT)" "$(TIELO_CELL_AND_PORT)"'
tie_command = ['docker', 'run', '--rm', '--entrypoint', 'make', image, '--no-print-directory', '-s',
               '-f', '/OpenROAD-flow-scripts/flow/platforms/asap7/config.mk',
               'PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7', '--eval='+query, 'print-ties']
hi, lo = [l.split() for l in subprocess.check_output(tie_command, text=True).strip().splitlines()]
tie_map = f'hilomap -singleton -hicell {hi[0]} {hi[1]} -locell {lo[0]} {lo[1]}'
manifest = json.loads((HERE/'sources.json').read_text())
for path, digest in manifest['generated_pins'].items():
    assert hashlib.sha256((HERE/path).read_bytes()).hexdigest() == digest, path
shared = ROOT/'tools/run_abi3_physical.py'
original = shared.read_text()
old = 'f"write_verilog -noattr {raw_netlist}"'
assert original.count(old) == 1
code = original.replace(old, 'f"write_verilog {raw_netlist}"')
needle = '                "splitnets -ports",'
assert code.count(needle) == 1
code = code.replace(needle, '                '+repr(tie_map)+',\n'+needle)
guard = 'if endpoint_netlist and metrics.get("sequential_cell_count", 0) < 270418:'
assert code.count(guard) == 1
code = code.replace(guard, f'if endpoint_netlist and metrics.get("sequential_cell_count", 0) < {a.min_ff}:')
driver = types.ModuleType('tk_w2_rb_driver'); driver.__file__ = str(shared)
sys.modules[driver.__name__] = driver
exec(compile(code, str(shared), 'exec'), driver.__dict__)
native_parse_stat = driver.parse_stat


def station_stat(text):
    # Kept hierarchy: use the final expanded table (count including submodules).
    if '=== design hierarchy ===' not in text:
        return native_parse_stat(text)
    hierarchy = text.split('=== design hierarchy ===', 1)[1]
    marker = '+----------Count including submodules.'
    table = hierarchy[hierarchy.rindex(marker):] if marker in hierarchy else hierarchy
    record = native_parse_stat(table)
    for k in [k for k in record['per_cell'] if k.startswith(('ot_', 'submodules', '$paramod'))]:
        record['per_cell'].pop(k)
    m = re.search(r"Chip area for top module .*?: ([0-9.]+)", table)
    if m:
        record['chip_area_um2'] = float(m.group(1))
    return record


driver.parse_stat = station_stat
sdc = run/'station.sdc'
cal = os.environ.get('CL_PHASE') == 'calibrate'  # CTS-only insertion measurement: no hold repair load
if cal:
    a.hold_margin_ns = 0.0
subprocess.run([sys.executable, str(HERE/'make_sdc.py'), '--period-ps', str(a.period_ps),
                '--l-max', str(a.l_max), '--l-min', str(a.l_min), '--l-ff-min', str(a.l_ff_min), '--l-ff-max', str(a.l_ff_max),
                '--io-ref-period-ps', '833.333'] + (['--hold-relax'] if cal else []) + [
                '--out', str(sdc)], check=True)
native_synth = driver.run_synthesis


def synth(*args, **kwargs):
    result = native_synth(*args, **kwargs)
    if hi[0] not in result['netlist'].read_text():
        raise driver.FlowError('actual high constant tie mapping missing')
    (run/'mapped_inventory.json').write_text(json.dumps(result['record'], indent=2)+'\n')
    return result


def endpoint(block, work, case):
    shutil.copyfile(work/'mapped.v', case/'w11_endpoint_mapped.v')
    shutil.copyfile(sdc, case/'station.sdc')
    return dict(mapped_netlist_sha256=driver.sha256_file(work/'mapped.v'),
                basis='exact rb station host map, attributes/kept hierarchy and physical ties retained')


def pins(regions):
    pat = {'^(clk_sm|por_n|release_held|in_.*|release_.*)$': 'clk_sm por_n release_held in_* release_*',
           '^(fclk_o|out_.*|ACK_.*|fault|drained|paused)$': 'fclk_o out_* ACK_* fault drained paused'}
    return '\n'.join('set_io_pin_constraint -region '+r['edge']+':* -pin_names {'+pat[r['regex']]+'}' for r in regions)+'\n'


driver.run_synthesis = synth
driver.prepare_w11_orfs_endpoint_netlist = endpoint
driver.io_constraints_tcl = pins
rel = str(HERE.relative_to(ROOT))
argv = ['--view', 'asap7', '--top', 'ot_hbm_native_frame_station_rb',
        '--source', rel+'/bank_veto_static.sv', '--source', 'rtl/common/ot_fwd_link_stage.sv',
        '--source', rel+'/station_rb_static.sv',
        '--param', 'ENABLE=1', '--param', f'NO={a.no}', '--param', 'REL_REG=1', '--param', f'SAFE={int(a.safe)}',
        '--clock-port', 'clk_sm', '--clock-period-ns', f'{a.period_ps/1000:.6f}',
        '--clock-uncertainty-ns', '0.06', '--clock-uncertainty-hold-ns', '0.025',
        '--orfs-corner', 'WC', '--hold-corners', ('WC' if a.post_route_ff_hold else 'WC,BC'), '--hold-margin-ns', str(a.hold_margin_ns),
        '--die-area', '0', '0', str(a.core_width+4.104), str(a.core_height+4.32),
        '--core-area', '2.052', '2.16', str(a.core_width+2.052), str(a.core_height+2.16),
        '--place-density', str(a.place_density),
        '--stages', 'synth,pnr', '--keep-heavy-artifacts',
        '--orfs-var', f'NUM_CORES={a.threads}', '--orfs-var', 'ADDER_MAP_FILE=',
        '--orfs-var', 'CTS_SNAPSHOTS=1',  # retain pre-repair ODB/SDC if RSZ-0060 aborts
        '--orfs-var', 'PLACE_DENSITY_LB_ADDON=',
        '--orfs-var', 'PLACE_PINS_ARGS=-min_distance 1 -min_distance_in_tracks',
        '--orfs-var', 'IO_PLACER_H=M4 M6', '--orfs-var', 'IO_PLACER_V=M5 M7',
        '--orfs-var', 'SDC_FILE=/work/station.sdc',
        '--step-tcl', 'PRE_IO_PLACEMENT='+rel+'/pin_faces.tcl',
        '--step-tcl', 'PRE_CTS='+rel+('/cts_setup_only.tcl' if a.post_route_ff_hold else '/forwarded_subtree.tcl'),
        '--pin-region', '^(clk_sm|por_n|release_held|in_.*|release_.*)$=bottom',
        '--pin-region', '^(fclk_o|out_.*|ACK_.*|fault|drained|paused)$=top',
        '--purpose', 'signoff_target', '--nickname-tag', f'{a.tag}_NO{a.no}',
        '--output', str(run/'physical.json')]
if a.post_route_ff_hold:
    argv += ['--step-tcl', 'PRE_GLOBAL_ROUTE='+rel+'/setup_only.tcl']
argv += passthrough
(run/'argv.json').write_text(json.dumps(dict(argv=argv, period_ps=a.period_ps, insertion=[a.l_min, a.l_max, a.l_ff_min],
    optimization_schedule='SS_setup_then_postroute_FF_hold' if a.post_route_ff_hold else 'legacy_multicorner',
    acceptance='strict measured-insertion SS setup >=15 ps and FF hold >=15 ps after route/ECO; DRC0',
    density=a.place_density, core=[a.core_width, a.core_height], tie_map=tie_map,
    effective_driver_sha256=hashlib.sha256(code.encode()).hexdigest()), indent=2)+'\n')
try:
    rc = persistent.launch(driver, argv, workdir=run/'work', receipt=run/'launch.json')
except BaseException as exc:
    (run/'terminal.json').write_text(json.dumps(dict(status='FAILED_WORK_PRESERVED', reason=str(exc)), indent=2)+'\n')
    raise
else:
    (run/'terminal.json').write_text(json.dumps(dict(status='DRIVER_RETURNED', exit_code=rc), indent=2)+'\n')
    raise SystemExit(rc)
