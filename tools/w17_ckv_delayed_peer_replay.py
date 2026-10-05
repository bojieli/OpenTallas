#!/usr/bin/env python3
"""Replay the archived real-service delayed-peer failure, without a long job."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = 'd2c28c279c4b8df731f9c4937e790831529a954b'
COMPANION = '3c109848ccb97a11d1caf48cf23be9c99f20c3e7'
REVIEW = 'd583af75d838c5fb93be368d08833dd6f2874e50'
BENCH = 'results/rtl/w17_collector_clear_delayed_old_20261001_r1.sv'
COMPANION_PATH = 'rtl/w17_runtime/chip/ckv_count_clear/ot_chip_v41x_ckv_die_service.sv'
DEPENDENCIES = [
    'rtl/chip/' + name + '.sv' for name in (
        'ot_chip_v41x_ckv_row_encoder', 'ot_chip_v41x_ckv_sel_ids',
        'ot_chip_v41x_ckv_sel_fetch', 'ot_chip_v41x_ckv_selected_dma',
        'ot_chip_v41x_ckv_fp4_decode', 'ot_chip_v41x_ckv_stream_merge',
    )
]


def blob(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)


def replay():
    archived = json.loads(blob(REVIEW, 'results/rtl/w17_collector_clear_3c109_review_20261001_r1.json'))
    pins = {}
    with tempfile.TemporaryDirectory(prefix='w17-delayed-peer-') as directory:
        scratch = Path(directory)
        files = []
        for index, (commit, path) in enumerate(
            [(REVIEW, BENCH), (COMPANION, COMPANION_PATH)]
            + [(ORIGINAL, path) for path in DEPENDENCIES]
        ):
            raw = blob(commit, path)
            digest = hashlib.sha256(raw).hexdigest()
            pins[path] = {'commit': commit, 'sha256': digest}
            file = scratch / f'source{index}.sv'
            file.write_bytes(raw)
            files.append(str(file))
        assert pins[BENCH]['sha256'] == archived['delayed_case']['bench_sha256']
        assert pins[COMPANION_PATH]['sha256'] == archived['companion_sha256']
        executable = scratch / 'gate'
        compile_result = subprocess.run(
            ['iverilog', '-g2012', '-s', 'tb', '-o', str(executable), *files],
            capture_output=True, text=True, timeout=30,
        )
        if compile_result.returncode:
            raise RuntimeError(compile_result.stderr)
        run = subprocess.run(['vvp', str(executable)], capture_output=True, text=True, timeout=30)
        log = run.stdout + run.stderr
        reproduced = (
            run.returncode == 1
            and 'DELAYED_OBSERVATION fault=0 code=0 count=1 present16=1 remote_stats=1' in log
            and log.count('FATAL:') == 1
            and 'delayed old response mutated new collector state' in log
            and 'Time: 2120000 Scope: tb' in log
            and 'DELAYED_OLD_RESPONSE_REJECT_PASS' not in log
        )
    return {
        'schema': 'opentallas.w17.delayed-peer-counterexample-replay.v1',
        'status': 'REPRODUCED_DELAYED_OLD_PEER_FAILURE' if reproduced else 'FAIL_REPLAY_EXPECTATION',
        'source_pins': pins, 'compile_returncode': compile_result.returncode,
        'run_returncode': run.returncode, 'compile_log': compile_result.stderr, 'log': log,
        'expected_DUT_failure_reproduced': reproduced,
        'counterexample_commit': REVIEW, 'local_priority_gate_superseded': False,
        'physical_admission': False, 'full_token_qualified': False,
        'scope': 'One archived external delayed-peer stimulus on the actual K512/NSLOT64 service. '
                 'No forces, source edits, scientific token rerun or synthetic event-provider substitution. '
                 'Exit 0 of this replay tool means the archived DUT failure was reproduced.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('refuse to overwrite retained evidence; choose a fresh output')
    result = replay()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(result['status'])
    raise SystemExit(0 if result['expected_DUT_failure_reproduced'] else 1)
