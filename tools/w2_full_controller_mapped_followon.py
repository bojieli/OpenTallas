#!/usr/bin/env python3
"""One exact-netlist census and ideal-clock, zero-wire SS/FF internal screen.

Waits for the existing synthesis, never invokes synthesis/place/route/inference.
Admission is host capacity only; it imposes no running resource/time limits.
"""
import argparse, datetime, hashlib, json, math, os, subprocess, time
from pathlib import Path
from w2_full_controller_mapped_census import census, liberty_facts

ROOT = Path(__file__).resolve().parents[1]
PIN = '8af31e3a5e02aa20d6a62a9498a6a86d09960f9c'
IMAGE = 'sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
STA = '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta'
BASE = Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
RESULT = Path('results/asap7/w2_full219_pc7_ss/base')
TOP = 'ot_w2_nc6_protected_completion_reset_quarantine'
PARAMS = dict(OPT_EXACT=1, OPT_RESET_QUARANTINE=1, NC=6, MAX_OUT=16,
              AW=34, CTAGW=32, GENW=4, SIDW=3, PTAGW=35, PC_ID=7)
SCOPE = ('Exact mapped PC7 source census and internal cell-delay SS setup / FF hold screen only. '
         'Ideal zero-slew clock, zero wire RC, no parent I/O constraints, no CTS/skew/routes. '
         'No physical/function/service/token qualification or inference.')

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()

def put(p, obj):
    p.write_text(json.dumps(obj, sort_keys=True, indent=2) + '\n')

def enroll(terminal, sources):
    if terminal.get('exit_code') != 0 or terminal.get('status') != 'MAPPED_SOURCE_AVAILABLE_CENSUS_PENDING':
        raise ValueError('successful authoritative synthesis terminal required')
    if terminal.get('source_commit') != PIN or terminal.get('top') != TOP:
        raise ValueError('synthesis source/top mismatch')
    if terminal.get('parameters') != PARAMS or terminal.get('source_sha256') != sources:
        raise ValueError('full geometry/source closure mismatch')
    if not terminal.get('all_top_ports_exposed') or terminal.get('blackboxes') or terminal.get('pruned_proxy'):
        raise ValueError('tied/pruned/blackbox source is inadmissible')

def libraries(corner):
    if corner not in ('SS', 'FF'): raise ValueError('SS/FF only')
    return [BASE / f'asap7sc7p5t_{family}_RVT_{corner}_nldm_{date}.lib{ext}'
            for family, date, ext in [('AO', '211120', '.gz'), ('INVBUF', '220122', '.gz'),
                                     ('OA', '211120', '.gz'), ('SEQ', '220123', ''),
                                     ('SIMPLE', '211120', '.gz')]]

def script(corner):
    libs = '\n'.join(f'read_liberty {{{p}}}' for p in libraries(corner))
    mode = 'max' if corner == 'SS' else 'min'
    return f'''{libs}
set_cmd_units -time ps -capacitance fF
read_verilog /input/{RESULT}/1_2_yosys.v
link_design {TOP}
create_clock -name clk -period 833.3333333333334 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set from [all_registers -output_pins]
set to [all_registers -data_pins]
if {{[llength $from] == 0 || [llength $to] == 0}} {{error "missing register endpoints"}}
check_setup -verbose
report_checks -from $from -to $to -path_delay {mode} -group_path_count 10 -format full_clock_expanded -fields {{slew capacitance fanout}} -digits 6
set paths [find_timing_paths -from $from -to $to -path_delay {mode} -group_path_count 1]
if {{[llength $paths] != 1}} {{error "missing internal timing path"}}
puts "W2_INTERNAL_{corner}_SLACK_PS [get_property [lindex $paths 0] slack]"
exit
'''

def admission_model(sizes):
    # Capacity request, not a cap or a guarantee: measured live Yosys RSS17.6GiB,
    # doubled for serial follow-on; also reserve64x actual serialized artifact bytes
    # for Python objects and STA timing graph. Record actual peak after execution.
    if any(type(n) is not int or n <= 0 for n in sizes.values()): raise ValueError('artifact inventory missing')
    byte_reserve = max(math.ceil(17.6 * 2 * 1024**3), sum(sizes.values()) * 64)
    return dict(expected_peak_GiB=math.ceil(byte_reserve / 1024**3),
                shared_reserve_GiB=150, actual_artifact_bytes=sizes,
                method='2x observed synthesis RSS17.6GiB or64x exact input bytes, whichever larger; '
                       'conservative admission estimate, no runtime cap; census and corners serial',
                wall_limit=None, memory_limit=None, file_limit=None, AS_limit=None)

def inside(out):
    started = time.monotonic()
    facts = liberty_facts(libraries('SS')); put(out / 'SS_liberty_facts.json', facts)
    ff = liberty_facts(libraries('FF')); put(out / 'FF_liberty_facts.json', ff)
    net = json.loads((Path('/input') / RESULT / 'full_mapped.json').read_text())
    result = census(net, facts); del net
    put(out / 'mapped_census.json', result)
    receipt = dict(scope=SCOPE, storage_census=result['full219_storage_census_PASS'],
                   representative_PC_ID=7, corners={}, physical_admission=False)
    if not result['full219_storage_census_PASS']:
        receipt['status'] = 'MAPPED_STORAGE_CENSUS_FAIL'; put(out / 'analysis_terminal.json', receipt); return 1
    receipt['STA_SHA256'] = sha(Path(STA))
    receipt['STA_version'] = subprocess.check_output([STA, '-version'], text=True).strip()
    for corner in ('SS', 'FF'):
        tcl = out / f'{corner}.tcl'; tcl.write_text(script(corner))
        log = out / f'{corner}.log'
        with log.open('w') as f:
            rc = subprocess.call([STA, '-no_init', '-exit', str(tcl)], stdout=f, stderr=subprocess.STDOUT)
        import re
        markers = re.findall(rf'^W2_INTERNAL_{corner}_SLACK_PS ([-+0-9.eE]+)$', log.read_text(), re.M)
        slack = float(markers[0]) if len(markers) == 1 else None
        # STA sometimes emits errors with a zero process exit: reject those too.
        errors = bool(re.search(r'^Error:', log.read_text(), re.M))
        receipt['corners'][corner] = dict(exit_code=rc, internal_slack_ps=slack,
                                         log_SHA256=sha(log), Tcl_SHA256=sha(tcl),
                                         library_SHA256=(facts if corner == 'SS' else ff)['libraries'])
        if rc or errors or slack is None or not math.isfinite(slack):
            receipt['status'] = 'INTERNAL_STA_EXECUTION_FAIL'; put(out / 'analysis_terminal.json', receipt); return 1
    receipt.update(status='INTERNAL_CELL_DELAY_SCREEN_COMPLETE_NOT_PHYSICAL_CLOSURE',
                   internal_setup_nonnegative=receipt['corners']['SS']['internal_slack_ps'] >= 0,
                   internal_hold_nonnegative=receipt['corners']['FF']['internal_slack_ps'] >= 0,
                   wall_s=time.monotonic() - started)
    put(out / 'analysis_terminal.json', receipt)
    return 0

def main():
    p = argparse.ArgumentParser(); p.add_argument('--input', type=Path); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--wait', action='store_true'); p.add_argument('--inside', action='store_true'); a = p.parse_args()
    if a.inside: return inside(a.out)
    if not a.input: p.error('--input required')
    inp = a.input.resolve(); out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise ValueError('analysis source tree must be clean')
    put(out / 'waiting.json', dict(supervisor_PID=os.getpid(), source_commit=commit,
         input=str(inp), scope=SCOPE, wait_for_existing_synthesis_only=True))
    terminal = inp / 'terminal.json'
    while not terminal.exists():
        if not a.wait: raise ValueError('synthesis is not terminal')
        time.sleep(30)
    original = json.loads(terminal.read_text())
    model = json.loads((ROOT / 'results/uarch/w2_full_controller_physical_context_20261003/model.json').read_text())
    try: enroll(original, model['source_sha256'])
    except ValueError as e:
        put(out / 'terminal.json', dict(status='PREREQUISITE_FAIL_NO_ANALYSIS', reason=str(e),
             synthesis_terminal_SHA256=sha(terminal))); return 1
    files = [inp / RESULT / n for n in ('full_mapped.json', '1_2_yosys.v')]
    inventory = {str(f.relative_to(inp)): dict(bytes=f.stat().st_size, SHA256=sha(f)) for f in files}
    price = admission_model({k:v['bytes'] for k,v in inventory.items()})
    cmd = ['/srv/opentallas-scratch/admit.sh', str(price['expected_peak_GiB']), '--',
           'docker', 'run', '--rm', '--user', f'{os.getuid()}:{os.getgid()}',
           '-v', f'{ROOT}:/src:ro', '-v', f'{inp}:/input:ro', '-v', f'{out}:/out',
           IMAGE, 'python3', '/src/tools/w2_full_controller_mapped_followon.py', '--inside', '--out', '/out']
    receipt = dict(source_commit=commit, synthesis_source_commit=PIN, inventory=inventory,
          synthesis_terminal_SHA256=sha(terminal), capacity_price=price, command=cmd,
          scope=SCOPE, started_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
    put(out / 'start.json', receipt)
    with (out / 'followon.log').open('w') as f: rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
    after = {str(f.relative_to(inp)): sha(f) for f in files}
    receipt.update(exit_code=rc, input_postcheck=all(after[k] == v['SHA256'] for k,v in inventory.items()),
                   status='FOLLOWON_TERMINAL', physical_admission=False)
    put(out / 'terminal.json', receipt)
    return rc if receipt['input_postcheck'] else 1

if __name__ == '__main__': raise SystemExit(main())
