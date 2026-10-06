#!/usr/bin/env python3
"""Prepare/run cached full32 TREE minimum-context P&R; never qualify the outer die.

Preparation is light and does not invoke synthesis, OpenROAD, or admission.
The finite child bounds the minimum vehicle. Its 32 real caller register banks
remain in the netlist. Distributed die placements are a separate qualification.
"""
import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import time

import run_abi3_physical as D


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def prepare(src, out, utilization):
    repo = Path(__file__).resolve().parents[1]
    evidence = repo / 'results/rtl/hbm_item9_closure_20261005'
    r = json.loads((src / 'result.json').read_text())
    assert r['exit'] == 0 and r['shape']['NSM'] == 32 and r['shape']['TREE'] == 1
    for name, digest in r['sources_sha256'].items():
        assert sha(repo / name) == digest, name
    gate = json.loads((evidence / 'context32_tree_exact_r1/result.json').read_text())
    assert gate['verdict'] == 'PASS_TREE_ACTUAL32_GATHER'
    mapped = next(src.glob('work/orfs/results/asap7/*/base/1_2_yosys.v'))
    digest = sha(mapped)
    assert digest == r['artifacts'][str(mapped.relative_to(src))]['sha256']
    binding = json.loads((evidence / 'loaded32_tree_physical_binding_r1/summary.json').read_text())
    assert digest == binding['source_mapped_sha256']
    allocation = json.loads((evidence / 'finite_allocation_r1.json').read_text())
    x0, y0, x1, y1 = allocation['baseline_endpoint_mux']['proposed_child_bbox_um']
    # This is a minimum loaded context inside the finite child, NOT compression
    # credit for the distributed callers or replacement of the invalid outer.
    width = x1 - x0
    height = math.ceil(binding['actual_total_cell_area_um2'] / (utilization / 100 * width) / .27) * .27
    assert height <= y1 - y0
    out.mkdir(parents=True, exist_ok=False)
    work = out / 'work/orfs'
    work.mkdir(parents=True)
    shutil.copy2(mapped, work / 'mapped.v')
    shutil.copy2(src / 'work/orfs/constraint.sdc', work / 'constraint.sdc')
    nickname = f'opentallas_item9_min32_tree_u{utilization}'
    config = (src / 'work/orfs/config.mk').read_text().splitlines()
    removed = ('export DESIGN_NICKNAME', 'export CORE_UTILIZATION', 'export PLACE_DENSITY',
               'export DIE_AREA', 'export CORE_AREA', 'export SYNTH_NETLIST_FILES')
    config = [line for line in config if not line.startswith(removed)]
    config += [f'export DESIGN_NICKNAME = {nickname}',
               'export SYNTH_NETLIST_FILES = /work/mapped.v',
               f'export DIE_AREA = 0 0 {width + 4:.6f} {height + 4:.6f}',
               f'export CORE_AREA = 2 2 {width + 2:.6f} {height + 2:.6f}',
               f'export PLACE_DENSITY = {utilization / 100:.2f}',
               # Pin projections are source-local interior terminals, not a
               # fictitious 262144-bit external perimeter/channel allowance.
               'export FOOTPRINT_TCL = /work/pins.tcl']
    (work / 'config.mk').write_text('\n'.join(config) + '\n')
    pins = ['# Minimum caller-local pin projections; preserve all source IO constraints.']
    # The source vector cuts remain individually represented, with legal metal
    # shapes. No pin deletion, tied-ready inputs, lumped loads, or false paths.
    stride = {'issue': 1, 'issue_mode': 1, 'issue_count': 8, 'issue_va': 4096,
              'caller_idle': 1, 'caller_done': 1, 'caller_vr': 4096}
    for port, count in stride.items():
        for bit in range(32 * count):
            caller, lane = divmod(bit, count)
            column, row = caller % 8, caller // 8
            # Separate input/output pin planes. Cell banks are real; this
            # geometry gives no credit for canonical parent distances.
            layer = 'M4' if port.startswith('caller_') else 'M3'
            index = lane + {'issue': 0, 'issue_mode': 1, 'issue_count': 2,
                            'issue_va': 10, 'caller_idle': 0, 'caller_done': 1,
                            'caller_vr': 2}[port]
            px = 3 + column * width / 8 + (index % 64) * .144
            py = 3 + row * height / 4 + (index // 64) * .144
            pins.append(f'place_pin -pin_name {{{port}[{bit}]}} -layer {layer} -location {{{px:.6f} {py:.6f}}} -pin_size {{0.032 0.032}} -placed_status')
    rest = ['por_n', 'clk_sm', 'clk_link', 'clk_mem', 'clk_host', 'switch_rx_v',
            'switch_tx_v', 'fault']
    rest += [f'{p}[{b}]' for p in ('switch_rx_rec', 'switch_tx_rec') for b in range(546)]
    for i, name in enumerate(rest):
        pins.append(f'place_pin -pin_name {{{name}}} -layer M4 -location {{{width / 2 + (i % 64) * .144:.6f} {height / 2 + (i // 64) * .144:.6f}}} -pin_size {{0.032 0.032}} -placed_status')
    (work / 'pins.tcl').write_text('\n'.join(pins) + '\n')
    record = dict(source_mapped_sha256=digest, source_commit=r['source_commit'],
                  shape=r['shape'], exact_gate_reused=True, new_RTL_cycles=0,
                  utilization_percent=utilization, finite_child_bbox_um=[x0, y0, x1, y1],
                  minimum_context_core_um=[2, 2, width + 2, height + 2],
                  all_32_caller_register_banks_retained=True,
                  root_clocks=r['constraints']['clock_roots'], period_ps=833,
                  setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                  PG='native ASAP7 M1/M2/M5/M6', CTS='native all source roots',
                  IO_budget_is_not_measured_parent_delay=True,
                  distributed_outer_placement_qualified=False, adopted=False,
                  phase='PREPARED_NOT_ADMITTED', NUM_CORES=16,
                  memory_guard_GiB=64, guard_unchanged=True,
                  driver_sha256=sha(Path(__file__).resolve()),
                  config_sha256=sha(work / 'config.mk'), pins_sha256=sha(work / 'pins.tcl'))
    (out / 'launch.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def run(out):
    record = json.loads((out / 'launch.json').read_text())
    assert record['phase'] == 'PREPARED_NOT_ADMITTED'
    assert os.uname().nodename not in ('ubuntu',) and Path('/srv/opentallas-scratch/admit.sh').is_file()
    work = out / 'work/orfs'
    assert sha(work / 'mapped.v') == record['source_mapped_sha256']
    assert sha(work / 'config.mk') == record['config_sha256']
    assert sha(work / 'pins.tcl') == record['pins_sha256']
    assert sha(Path(__file__).resolve()) == record['driver_sha256']
    image = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', D.ORFS_IMAGE], text=True).strip()
    # CPU fit precedes the unchanged memory guard; RAM alone never admits this.
    # No timeout and no alteration to queued/live fleet jobs or guard policy.
    while not cpu_fit(record['NUM_CORES']):
        time.sleep(10)
    sample = dict(load=os.getloadavg(), CPUs=os.cpu_count(),
                  meminfo=Path('/proc/meminfo').read_text(),
                  disk_free_bytes=shutil.disk_usage(out).free)
    (out / 'preadmission.json').write_text(json.dumps(sample, indent=2) + '\n')
    command = ['docker', 'run', '--rm', '-v', f'{Path(__file__).resolve().parents[1]}:/src:ro',
               '-v', f'{work}:/work', '-w', '/OpenROAD-flow-scripts/flow', image,
               'bash', '-lc', 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '
               'make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 finish']
    # Recheck after the memory guard's potentially long wait, before any heavy
    # child exists. A lost CPU slot releases the guard and retries admission.
    internal = ['python3', str(Path(__file__).resolve()), str(out), str(out),
                '--utilization', str(record['utilization_percent']), '--admitted-execute']
    (out / 'command.json').write_text(json.dumps(command) + '\n')
    (out / 'image_id.txt').write_text(image + '\n')
    with (out / 'run.log').open('a') as log:
        while True:
            rc = subprocess.run(['/srv/opentallas-scratch/admit.sh', '64', '--', *internal],
                                stdout=log, stderr=subprocess.STDOUT).returncode
            if rc != 75:
                break
            while not cpu_fit(record['NUM_CORES']):
                time.sleep(10)
    record.update(phase='FLOW_TERMINAL', exit=rc, physical_signoff=False)
    if rc == 0:
        record['routed_corner_reports'] = json.loads((out / 'routed_corners.json').read_text())
        record['physical_signoff'] = False  # IO budgets still require parent binding.
    record['post_run_load'] = os.getloadavg()
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    raise SystemExit(rc)


def cpu_fit(cores):
    def ticks():
        values = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
        return sum(values), values[3] + values[4]
    before = ticks()
    time.sleep(1)
    after = ticks()
    available = min(os.cpu_count(), len(os.sched_getaffinity(0)))
    idle_cores = available * (after[1] - before[1]) / max(1, after[0] - before[0])
    return os.getloadavg()[0] + cores <= available and idle_cores >= cores


def routed_reports(work):
    odb = next(work.glob('results/asap7/*/base/6_final.odb'))
    sdc = odb.with_suffix('.sdc')
    spefs = list(odb.parent.glob('6_final.spef*'))
    assert len(spefs) == 1 and sdc.is_file()
    reports = []
    for corner in ('SS', 'FF'):
        relative = lambda path: '/work/' + str(path.relative_to(work))
        script = work / f'routed_{corner}.tcl'
        script.write_text(f'''foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_{corner}_*.lib*] {{read_liberty $f}}
read_db {relative(odb)}
read_sdc {relative(sdc)}
set_propagated_clock [all_clocks]
read_spef {relative(spefs[0])}
puts "OT_CLOCK_COUNT [llength [all_clocks]]"
puts "OT_SETUP [sta::worst_slack_cmd max]"
puts "OT_HOLD [sta::worst_slack_cmd min]"
check_setup -verbose
report_clock_properties [all_clocks]
report_checks -path_delay max -group_path_count 20 -format full_clock_expanded
report_checks -path_delay min -group_path_count 20 -format full_clock_expanded
report_check_types -max_slew -max_capacitance -max_fanout -violators
exit
''')
        image = (work.parents[1] / 'image_id.txt').read_text().strip()
        command = ['docker', 'run', '--rm', '-v', f'{work}:/work', image,
                   'bash', '-lc', 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '
                   f'openroad -no_init -exit -threads 16 /work/{script.name}']
        with (work / f'routed_{corner}.log').open('w') as log:
            rc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
        content = (work / f'routed_{corner}.log').read_text()
        values = {key: re.search(rf'^OT_{key} (\S+)', content, re.M) for key in ('SETUP', 'HOLD', 'CLOCK_COUNT')}
        reports.append(dict(corner=corner, exit=rc, ODB_sha256=sha(odb), SPEF_sha256=sha(spefs[0]),
                            metrics={key: m[1] if m else None for key, m in values.items()},
                            log_sha256=sha(work / f'routed_{corner}.log'),
                            outer_die_qualified=False))
        if rc:
            break
    return reports


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source_synth', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--utilization', type=int, choices=(55, 60), required=True)
    p.add_argument('--run-prepared', action='store_true')
    p.add_argument('--admitted-execute', action='store_true', help=argparse.SUPPRESS)
    a = p.parse_args()
    assert a.source_synth.is_absolute() and a.output.is_absolute()
    if a.admitted_execute:
        if not cpu_fit(16):
            raise SystemExit(75)
        command = json.loads((a.output / 'command.json').read_text())
        # Route AND same-object SS/FF extraction stay inside this reservation.
        rc = subprocess.run(command).returncode
        if rc == 0:
            reports = routed_reports(a.output / 'work/orfs')
            (a.output / 'routed_corners.json').write_text(json.dumps(reports, indent=2) + '\n')
            if any(r['exit'] for r in reports) or len(reports) != 2:
                rc = 1
        raise SystemExit(rc)
    elif a.run_prepared:
        run(a.output)
    else:
        print(json.dumps(prepare(a.source_synth, a.output, a.utilization)))
