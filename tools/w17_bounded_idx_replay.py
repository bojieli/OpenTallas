#!/usr/bin/env python3
"""Bounded direct unchanged idx_hbm vs unchanged scalar; timing only, no payload qualification."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RTL = 'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'
SCALAR = 'tools/w17_L0_window_service_expectation.py'
BENCH = 'rtl/test/w17_bounded_idx_replay/tb.sv'
PINS = {RTL: '92dc584e3caa00f2a66750d8092b4ae6c8fa9741dc645935d02705f4273a1543',
        SCALAR: '00960b3f28c7e2a168f4251ecfc8d10d68da397152d6a54574c63c7889d6ef35'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scalar_trace(start):
    spec = importlib.util.spec_from_file_location('expectation', ROOT / SCALAR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    trace = []
    # Observe locals at the existing gaps.append line; never alter scalar arithmetic.
    line = next(i for i, s in enumerate((ROOT / SCALAR).read_text().splitlines(), 1)
                if 'gaps.append(nxt-cyc)' in s)
    def observer(frame, event, arg):
        if frame.f_code is module.replay.__code__ and event == 'line' and frame.f_lineno == line:
            v = frame.f_locals
            trace.append(dict(index=len(trace), request_cycle=v['cyc'], pc=v['p'],
                              address=v['addr'], tag=len(trace), tcol_ps=v['tcol'],
                              refreshes=v['refreshes'], activations=v['misses'],
                              response_cycle=v['nxt']-2))
        return observer
    old = sys.gettrace()
    sys.settrace(observer)
    try:
        summary = module.replay(start, row_overhead=3, edge_overhead=2)
    finally:
        sys.settrace(old)
    assert len(trace) == 2176
    return summary, trace


def compare(log, expected, summary):
    req, rsp, pcs, totals = [], [], [], []
    for line in log.splitlines():
        words = line.split()
        if words and words[0] in ('R', 'S', 'PC', 'SUMMARY'):
            values = list(map(int, words[1:]))
            {'R': req, 'S': rsp, 'PC': pcs, 'SUMMARY': totals}[words[0]].append(values)
    errors = []
    def check(label, actual, want):
        if actual != want:
            errors.append(dict(field=label, actual=actual, expected=want))
    check('request_count', len(req), 2176)
    check('response_count', len(rsp), 2176)
    for i, e in enumerate(expected):
        if i < len(req):
            check(f'request[{i}]', req[i], [i, e['request_cycle'], e['pc'], e['address'],
                  e['tag'], e['tcol_ps'], e['refreshes'], e['activations']])
        if i < len(rsp):
            check(f'response[{i}]', rsp[i], [i, e['response_cycle'], e['pc'], e['tag'], 0])
    check('summary_count', len(totals), 1)
    if totals:
        check('summary', totals[0][:7], [summary['start_cycle'], summary['end_cycle']-2,
              summary['end_cycle'], 2176, 2176, summary['refresh_events_all_channels'], summary['activations']])
    check('pc_count', len(pcs), 32)
    for p, row in enumerate(pcs):
        check(f'pc[{p}]', row[:4], [p, 68, 68, 68])
    return dict(verdict='PASS_BOUNDED_TIMING_EQUIVALENCE' if not errors else 'FAIL_MODEL_VS_SOURCE',
                mismatch_count=len(errors), mismatches=errors, rtl_summary=totals, per_channel=pcs)


def limits():
    os.nice(10)
    cpus = os.sched_getaffinity(0)
    os.sched_setaffinity(0, {max(cpus)})
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32*1024**2, 32*1024**2))


def run(command, logfile, timeout):
    begin = time.monotonic()
    with logfile.open('w') as stream:
        try:
            proc = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                  timeout=timeout, preexec_fn=limits)
            status = proc.returncode
        except subprocess.TimeoutExpired:
            status = 'WALL_TIMEOUT'
    return dict(command=command, status=status, wall_seconds=time.monotonic()-begin,
                log=str(logfile.relative_to(ROOT)), log_sha256=sha(logfile))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, help='new evidence directory, never overwrite')
    parser.add_argument('--start', type=int, default=12300)
    args = parser.parse_args()
    out = (ROOT / args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    summary, expected = scalar_trace(args.start)
    (out / 'scalar_trace.json').write_text(json.dumps(dict(summary=summary, sectors=expected), indent=2)+'\n')
    record = dict(scope='SIMULATION_ONLY_DIRECT_BACKEND_MODEL_VS_SOURCE_PREREQUISITE',
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        source_status=subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT, text=True),
        source_sha256={p: sha(ROOT/p) for p in (RTL, SCALAR, BENCH, 'tools/w17_bounded_idx_replay.py')},
        source_pins_match=all(sha(ROOT/p)==h for p,h in PINS.items()),
        tool_versions={},
        scenario=dict(start_cycle=args.start, rows=128, reads=2176, cold_closed_banks=True,
                      queues_initially_empty=True, competitors=0, credits=1, row_overhead=3,
                      response_to_next_request_cycles=2, NPC=32, AW=30, LENW=4, MEM_WORDS=1,
                      MEM_MODE=1, QD=64, RQD=32, REFPB=3, CLK_PS=1000),
        edge_alignment='cyc is sampled before posedge; request accepted at cyc; registered response valid is sampled before posedge at ceil((tcol+23524)/1000). Next request at response+2, plus3 on each new row. Scalar end_cycle is next-request boundary after final response, not final response edge.',
        limitations=['Timing-only pattern data is NOT payload qualification.',
                     'Direct backend excludes muxes, arbiters, row controller and full die.',
                     'Cold/empty is constructed in this bench, NOT proved for protected live state.',
                     'No live completion, hardware rate, exhaustive bound, SS/FF or numerical claim.'],
        caps=dict(cpu_affinity='one local CPU, highest allowed index', nice=10,
                  address_space_bytes=2*1024**3, cpu_seconds_per_process=120,
                  compile_wall_seconds=60, runtime_wall_seconds=120, cycles=200000,
                  output_file_bytes=32*1024**2), scalar_summary=summary)
    for name in ('iverilog', 'vvp'):
        version = subprocess.run([name, '-V'], capture_output=True, text=True)
        record['tool_versions'][name] = (version.stdout + version.stderr).splitlines()[0]
    if not record['source_pins_match'] or record['source_status']:
        record['verdict']='FAIL_SOURCE_PIN_OR_DIRTY'
    else:
        record['compile'] = run(['iverilog', '-g2012', '-s', 'tb', '-o', str(out/'sim.vvp'),
                                 RTL, BENCH], out/'compile.log', 60)
        if record['compile']['status'] == 0:
            record['binary_sha256'] = sha(out/'sim.vvp')
            record['runtime'] = run(['vvp', str(out/'sim.vvp'), f'+START={args.start}'], out/'runtime.log', 120)
            record.update(compare((out/'runtime.log').read_text(), expected, summary))
            if record['runtime']['status'] != 0:
                record['verdict']='FAIL_BOUNDED_RUNTIME'
        else:
            record['verdict']='FAIL_BOUNDED_COMPILE'
    record['reproduce']=f'python3 tools/w17_bounded_idx_replay.py --start {args.start} --out results/rtl/w17_bounded_idx_replay_rerun_NEW'
    (out/'record.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('verdict','scalar_summary')}, indent=2))
    return 0 if record['verdict']=='PASS_BOUNDED_TIMING_EQUIVALENCE' else 1


if __name__ == '__main__':
    sys.exit(main())
