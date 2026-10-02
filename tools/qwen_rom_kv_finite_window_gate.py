#!/usr/bin/env python3
"""Bounded existing-RTL read transport/window diagnostic, with corruption control."""
import argparse
import hashlib
import json
import resource
import shutil
import subprocess
import time
from pathlib import Path
from run_qwen_kv_system_bridge_campaign import INPUTS
from qwen_rom_integration_preflight import MAPPING

ROOT = Path(__file__).resolve().parents[1]
TOP = 'tb_qwen_rom_kv_finite_window'
BENCH = 'rtl/test/' + TOP + '.sv'
SOURCES = [p for p in INPUTS[:16] if p.parts[-2] != 'test'] + [ROOT / BENCH]


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    resource.setrlimit(resource.RLIMIT_FSIZE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))


def disk_guard(workdir, aggregate_limit=256 * 1024**2, free_reserve=2 * 1024**3):
    used=sum(p.stat().st_size for p in workdir.rglob('*') if p.is_file())
    free=shutil.disk_usage(workdir).free
    if used>aggregate_limit:
        return 'aggregate workdir disk guard exceeded'
    if free<free_reserve:
        return 'filesystem free-space reserve exhausted'
    return None


def guarded_process(command, workdir, logfile):
    problem=disk_guard(workdir)
    if problem:return 125, 'FAIL '+problem
    with logfile.open('w') as log:
        with subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits) as proc:
            while proc.poll() is None:
                problem=disk_guard(workdir)
                if problem:
                    proc.terminate()
                    proc.wait()
                    break
                time.sleep(0.1)  # Resource sampling only; no elapsed-time deadline.
            problem=problem or disk_guard(workdir)
            rc=125 if problem else proc.returncode
    output=logfile.read_text()
    if problem:output+='\nFAIL '+problem+'; build artifacts retained\n'
    return rc,output


def run(workdir, result, main_root):
    if workdir.exists() or result.exists():
        raise ValueError('Refusing to reuse build path or overwrite verdict')
    paths = SOURCES + [Path(__file__).resolve()] + [ROOT / p for p in MAPPING.values()]
    raw = {str(p.relative_to(ROOT)): p.read_bytes() for p in paths}
    pins = {p: hashlib.sha256(b).hexdigest() for p, b in raw.items()}
    ref = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=main_root, text=True).strip()
    currency = {p: hashlib.sha256(subprocess.check_output(['git', 'show', ref + ':' + p], cwd=main_root)).hexdigest() == pins[p]
                for p in MAPPING.values()}
    workdir.mkdir(parents=True)
    steps = []
    for name, mutant in [('read_window', 0), ('corrupt_return', 1)]:
        binary = workdir / name
        cmd = ['iverilog', '-g2012', '-s', TOP, '-P' + TOP + '.CORRUPT_RETURN=' + str(mutant),
               '-o', str(binary), *map(str, SOURCES)]
        for phase, command in [('build', cmd), ('simulation', ['vvp', str(binary)])]:
            started = time.monotonic()
            rc,output=guarded_process(command,workdir,workdir / (name + '_' + phase + '.log'))
            (workdir / (name + '_' + phase + '.log')).write_text(output)
            steps.append(dict(case=name, phase=phase, returncode=rc, seconds=round(time.monotonic()-started, 3), output=output))
            if phase == 'build' and rc:
                break
    positive = next((s for s in steps if s['case']=='read_window' and s['phase']=='simulation'), {})
    negative = next((s for s in steps if s['case']=='corrupt_return' and s['phase']=='simulation'), {})
    stable = all((ROOT / path).read_bytes() == b for path, b in raw.items())
    rejected = negative.get('returncode', 0) != 0 and 'KV physical read mismatch' in negative.get('output', '')
    passed = positive.get('returncode') == 0 and 'PASS QWEN_ROM_FINITE_WINDOW' in positive.get('output', '')
    rec = dict(schema='opentallas.qwen-rom-finite-window-diagnostic.v1',
               status='PASS' if passed and rejected and stable and all(currency.values()) else 'FAIL',
               source_sha256=pins, source_stable=stable, parent_ref=ref, seven_runtime_source_matches=currency,
               steps=steps, negative_control_rejected=rejected,
               fixture=dict(groups=4, sw=16, sector_bytes=32, read_service_cycles=41, request_backpressure='one edge in seven',
                            window_word_bits=256, tile_fill_word_bits=512, connected_to_tile_macro=False,
                            r14_provider_connected=False, external_writes_qualified=False, second_token=False),
               missing_actual_join=['BF16 streamer window -> FP8 masked 512-bit tile SRAM fill codec/ownership adapter',
                                    'r14 tags, TP4 identity, backing write completion and reverse credit retirement',
                                    'macro visibility/collision and layer-window lifetime bound to reader drain',
                                    'unified finite-service price and source-matched SS/FF fit'],
               resource_caps=dict(memory_MiB=2048, cpu_seconds_per_process=None, wall_seconds_per_process=None,
                                  RLIMIT_FSIZE='unlimited',aggregate_workdir_disk_MiB=256,minimum_free_disk_MiB=2048,
                                  build_artifacts_retained=True),
               claim_boundary='Existing connected subsystem RTL read diagnostic with a delayed behavioral sector endpoint and behavioral window/tail memories. No engine build, actual r14 transport, SRAM macro, second token, full-token, rate or physical credit.')
    result.parent.mkdir(parents=True, exist_ok=True)
    with result.open('x') as f:
        json.dump(rec, f, indent=2, sort_keys=True); f.write('\n')
    print(json.dumps({k: rec[k] for k in ('status', 'negative_control_rejected', 'source_stable', 'seven_runtime_source_matches')}, indent=2))
    return 0 if rec['status']=='PASS' else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workdir', type=Path, required=True)
    ap.add_argument('--result', type=Path, required=True)
    ap.add_argument('--main-root', type=Path, required=True)
    a = ap.parse_args()
    return run(a.workdir.resolve(), a.result, a.main_root)


if __name__ == '__main__':
    raise SystemExit(main())
