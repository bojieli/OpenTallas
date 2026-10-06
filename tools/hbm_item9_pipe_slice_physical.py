#!/usr/bin/env python3
"""Prepare the minimum owned timing mechanism using Turing's real binding.

No launch, admission waiter, fake IO budget, or parent qualification here.
Kant may launch the prepared command only after fresh fleet/unchanged guard fit.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
import run_abi3_physical as D


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('binding', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--admitted-execute', action='store_true')
    parser.add_argument('--utilization', type=int, choices=(55, 60), default=55)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    assert args.out.is_absolute()
    if args.admitted_execute:
        # Caller must already hold the host's unchanged admission guard. Recheck
        # actual CPU fit after any guard wait, before starting a heavy child.
        from hbm_item9_context32_route import cpu_fit, routed_reports
        if not Path('/srv/opentallas-scratch/admit.sh').is_file() or not cpu_fit(16):
            raise SystemExit(75)
        record = json.loads((args.out / 'launch.json').read_text())
        assert record['phase'] == 'PREPARED_ONLY'
        assert sha(Path(__file__)) == record['driver_sha256']
        for f, digest in record['source_sha256'].items():
            assert sha(repo / f) == digest, f
        command = json.loads((args.out / 'command.json').read_text())
        record['image_id'] = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', D.ORFS_IMAGE], text=True).strip()
        (args.out / 'image_id.txt').write_text(record['image_id'] + '\n')
        with (args.out / 'run.log').open('w') as log:
            rc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
        record.update(phase='FLOW_TERMINAL', exit=rc)
        if rc == 0:
            reports = routed_reports(args.out / 'work/orfs')
            record['routed_corner_reports'] = reports
            record['minimum_slice_closed'] = len(reports) == 2 and all(
                r['exit'] == 0 and r['metrics']['CLOCK_COUNT'] == '4' and
                all(float(r['metrics'][k]) >= 0 for k in ('SETUP', 'HOLD'))
                for r in reports)
        (args.out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
        raise SystemExit(rc)
    assert not args.out.exists()
    b = json.loads(args.binding.read_text())
    assert b['top'] == 'ot_gpu_coll_item9_pipe_slice'
    assert b['payload_slice_bits'] == 64 and b['caller_count'] == 32
    assert b['clock_period_ps'] == 833 and b['setup_uncertainty_ps'] == 60 and b['hold_uncertainty_ps'] == 25
    assert set(b['clock_roots']) == {'clk_sm', 'clk_link', 'clk_mem', 'clk_host'}
    # Literal source/receiver tuples include their hierarchy, clock, actual pin,
    # min/max arrivals and installed SS/FF load. Flags cannot replace these.
    for name in ('producer_tuples', 'receiver_tuples', 'clock_pin_tuples', 'corridor_segments'):
        assert b[name], name
    assert b['PG_and_clock_tracks_excluded_from_capacity'] is True
    assert b['canonical_r14_geometry_used'] is False
    sources = ['rtl/gpu_sys/ot_gpu_reset_ctrl.sv', 'rtl/link/ot_link_afifo.sv',
               'rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv', 'rtl/gpu_sys/ot_gpu_coll_mux_f12.sv',
               'rtl/gpu_sys/ot_gpu_coll_mux_item9_tree.sv',
               'rtl/gpu_sys/ot_gpu_coll_mux_item9_pipe.sv',
               'rtl/gpu_sys/ot_gpu_coll_item9_pipe_slice.sv']
    for f in sources:
        assert sha(repo / f) == b['source_sha256'][f], f
    gate = json.loads((repo / 'results/rtl/hbm_item9_closure_20261005/pipe_exact_r1/result.json').read_text())
    assert gate['verdict'] == 'PASS_PIPE_ACTUAL32_GATHER' and gate['new_cycles'] == 64
    assert sha(repo / sources[5]) == gate['source_sha256'][sources[5]]
    sdc = Path(b['SDC']['path']); pins = Path(b['pins_Tcl']['path'])
    assert sha(sdc) == b['SDC']['sha256'] and sha(pins) == b['pins_Tcl']['sha256']
    text = sdc.read_text()
    assert not re.search(r'\b(set_false_path|set_multicycle_path|set_disable_timing)\b', text)
    assert all(c in text for c in b['clock_roots'])
    assert 'set_input_delay' in text and 'set_output_delay' in text and 'set_load' in text
    model = __import__('uarch_model').hbm_item9_mux_owner_model(32, 2, 1)['registered_request_boundary']
    nickname = f'opentallas_item9_pipe_slice_u{args.utilization}'
    block = dict(top=b['top'], sources=sources,
                 parameters=dict(ENABLE=1, NSM=32, NL=2, PIPE=1, TREE=1), clock_port='clk_sm')
    view = D.VIEWS['asap7']; pnr = {**view['pnr'], 'corner_env': 'WC'}
    config = D.orfs_config_lines(nickname, block, 'asap7', pnr, args.utilization,
                                 args.utilization / 100, constraints={'hold_corners': ['WC', 'BC']}, memory_max_bits=None)
    die = b['die_bbox_um']; core = b['core_bbox_um']
    config = [x for x in config if not x.startswith(('export DIE_AREA', 'export CORE_AREA'))]
    config += ['export ADDER_MAP_FILE =', 'export DIE_AREA = ' + ' '.join(map(str, die)),
               'export CORE_AREA = ' + ' '.join(map(str, core)),
               'export FOOTPRINT_TCL = /work/pins.tcl']
    work = args.out / 'work/orfs'; work.mkdir(parents=True)
    (work / 'constraint.sdc').write_bytes(sdc.read_bytes())
    (work / 'pins.tcl').write_bytes(pins.read_bytes())
    (work / 'config.mk').write_text('\n'.join(config) + '\n')
    record = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
                  source_sha256={f: sha(repo / f) for f in sources}, binding_sha256=sha(args.binding),
                  exact_gate_reused=True, measured_new_cycles_per_collective=2,
                  model=model, source_bound_binding=b, utilization=args.utilization,
                  physical_signoff=False, full_parent_qualified=False, adopted=False,
                  phase='PREPARED_ONLY', NUM_CORES=16, unchanged_memory_guard_GiB=16, driver_sha256=sha(Path(__file__)),
                  view_purpose='one physical 64-bit slice of full4096 request banks/root with actual32 caller and response receivers')
    (args.out / 'launch.json').write_text(json.dumps(record, indent=2) + '\n')
    command = ['docker', 'run', '--rm', '-v', f'{repo}:/src:ro', '-v', f'{work}:/work',
               '-w', '/OpenROAD-flow-scripts/flow', D.ORFS_IMAGE, 'bash', '-lc',
               'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '
               'make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 finish']
    (args.out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
