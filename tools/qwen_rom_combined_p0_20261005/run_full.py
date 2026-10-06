#!/usr/bin/env python3
"""Execute the sole prepared full numerical join under Kant's admission guard.

No engine leaf rebuild, oracle generation or historical token replay. Failed
stage outputs are retained. The host uses genuine released 144 histories and
all36 sequential carries; numerical readback is compared to retained truth.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import threading
import time


def observe(output, phase, stop):
    peak = 0
    with (output/(phase+'_resources.jsonl')).open('x') as log:
        while not stop.is_set():
            processes = {}
            for p in Path('/proc').glob('[0-9]*'):
                try:
                    fields = (p/'stat').read_text().rsplit(')', 1)[1].split()
                    processes[int(p.name)] = (int(fields[1]), int(fields[21])*os.sysconf('SC_PAGE_SIZE'))
                except (OSError, ValueError, IndexError):
                    continue
            owned = {os.getpid()}
            while True:
                more = {pid for pid, (parent, rss) in processes.items() if parent in owned}-owned
                if not more:
                    break
                owned |= more
            rss = sum(processes.get(pid, (0, 0))[1] for pid in owned)
            peak = max(peak, rss)
            disk = os.statvfs(output)
            log.write(json.dumps(dict(time=time.time(), aggregate_RSS_bytes=rss,
                peak_aggregate_RSS_bytes=peak, descendants=len(owned),
                available_disk_bytes=disk.f_bavail*disk.f_frsize, load=os.getloadavg()[0]))+'\n')
            log.flush()
            stop.wait(5)
    (output/(phase+'_observed_peak.json')).write_text(json.dumps(dict(
        sampled_aggregate_RSS_bytes=peak, interval_seconds=5,
        scope='Observed runner and actual descendant RSS; estimate is not an address-space cap'))+'\n')


def fresh(output, stage, cpus):
    def ticks():
        return list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
    a = ticks(); time.sleep(1); b = ticks()
    delta = [y-x for x, y in zip(a, b)]
    idle = (delta[3]+delta[4])*os.cpu_count()/sum(delta[:8])
    memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    disk = os.statvfs(output)
    record = dict(load=os.getloadavg()[0], idle_CPUs=idle, required_CPUs=cpus,
        MemAvailable_bytes=int(memory['MemAvailable'].split()[0])*1024,
        available_disk_bytes=disk.f_bavail*disk.f_frsize)
    (output/(stage+'_post_guard.json')).write_text(json.dumps(record)+'\n')
    if record['load'] >= 128 or idle < cpus:
        raise RuntimeError('fresh E2 post-guard CPU/load fit unavailable')


def stage(output, name, command):
    (output/(name+'_once')).mkdir()
    (output/(name+'_command.json')).write_text(json.dumps(command, indent=2)+'\n')
    with (output/(name+'.log')).open('x') as log:
        rc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
    (output/(name+'.exit')).write_text(str(rc)+'\n')
    if rc:
        (output/(name+'_terminal.json')).write_text(json.dumps(dict(
            status='FAIL_'+name.upper(), exit=rc, full_token_pass=False,
            physical_qualified=False), indent=2)+'\n')
        raise RuntimeError(name+' failed; retained stage will not be replayed')


def dispatch(output, source, workers):
    """One changed candidate; wait for CPU fit before the unchanged RAM guard."""
    (output/'dispatch_once').mkdir()
    runner = source/'tools/qwen_rom_combined_p0_20261005/run_full.py'
    # Debug the changed join once at full layer shape, never automatically
    # start a multi-day full token. The final smoke remains an explicit stage.
    for phase, ram_gib, cpus in [('build', 128, workers), ('layer-runtime', 16, 16)]:
        while True:
            def ticks():
                return list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
            a = ticks(); time.sleep(1); b = ticks()
            delta = [y-x for x, y in zip(a, b)]
            idle = (delta[3]+delta[4])*os.cpu_count()/sum(delta[:8])
            memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
            available = int(memory['MemAvailable'].split()[0])*1024
            disk = os.statvfs(output)
            fit = dict(time=time.time(), load=os.getloadavg()[0], idle_CPUs=idle,
                MemAvailable_bytes=available, available_disk_bytes=disk.f_bavail*disk.f_frsize,
                required_CPUs=cpus, requested_guard_GiB=ram_gib)
            if fit['load'] < 128 and idle >= cpus and available >= ram_gib*1024**3 and fit['available_disk_bytes'] >= 32*1024**3:
                (output/(phase+'_pre_guard.json')).write_text(json.dumps(fit)+'\n')
                break
            print('WAIT_CPU_CAPACITY '+phase+' '+json.dumps(fit), flush=True)
            time.sleep(60)
        # Child repeats fresh CPU/load sampling after actual guard admission.
        # A failure stops this continuation; no model/leaf/runtime retry.
        command = ['/srv/opentallas-scratch/admit.sh', str(ram_gib), '--',
            'python3', str(runner), '--output', str(output), '--source', str(source),
            '--stage', phase, '--workers', str(workers)]
        (output/(phase+'_guard_command.json')).write_text(json.dumps(command, indent=2)+'\n')
        print('ADMIT '+phase, flush=True)
        with (output/(phase+'_supervisor.log')).open('x') as log:
            rc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
        (output/(phase+'_supervisor.exit')).write_text(str(rc)+'\n')
        if rc:
            raise RuntimeError(phase+' continuation failed; no automatic replay')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--stage', choices=['build', 'finish-build', 'relink-driver', 'runtime', 'layer-runtime', 'dispatch'], required=True)
    p.add_argument('--workers', type=int, default=4)
    a = p.parse_args()
    output = a.output
    r = json.loads((output/'prepared.json').read_text())
    if a.stage == 'dispatch':
        if not r.get('cdc_consumer_join') or r.get('landing_rsel') != 1:
            raise RuntimeError('dispatcher requires the actual changed protected r9 selection')
        dispatch(output, a.source, a.workers)
        return
    authority = Path('/srv/opentallas-scratch/jobs/laplace-qwen-plainar-stream4-P8191-r1')
    tools = a.source/'tools/qwen_rom_combined_p0_20261005'
    fresh(output, a.stage, 1 if a.stage == 'relink-driver' else
          (16 if a.stage in ('runtime', 'layer-runtime') else a.workers))
    if a.stage == 'relink-driver':
        if not (output/'reuse_completed_top').is_file():
            raise RuntimeError('explicit completed top reference required; no model build')
        stage(output, 'driver_link', r['link'])
        (output/'build_complete').write_text('corrected driver linked with genuine retained full top\n')
        return
    if a.stage == 'build':
        stage(output, 'frontend', r['frontend'])
        stage(output, 'access', ['python3', str(tools/'access.py'),
            '--die-header', str(output/'die/Vdie___024root.h'),
            '--tile-header', str(authority/'reuse/tile/Vtile___024root.h'),
            '--out', str(output/'host/rm_access.hpp'),
            '--consumer-prefix', r.get('consumer_prefix', r['top']+'__DOT__u_join__DOT__u_consumer__DOT__'),
            '--backing-member', r.get('backing_member', r['top']+'__DOT__u_numeric__DOT__mem'),
            '--nport', '48', '--scale-banks', '13', '--code-banks', '5',
            '--crom-words', '1048576', '--hbm-layers', '36', '--kv-ideal', '0', '--embed-rom', '1'])
        if not (output/'die/Vdie_hier.mk').is_file():
            stage(output, 'archive_bind', ['python3', str(tools/'bind_full_archives.py'),
                '--output', str(output), '--authority', str(authority)])
        stage(output, 'compile', r['compile_top']+['-j', str(a.workers), 'CXX=g++-15'])
        stage(output, 'link', r['link'])
        (output/'build_complete').write_text('canonical 5.050 top built with retained leaves\n')
        return
    if a.stage == 'finish-build':
        if (output/'frontend.exit').read_text().strip() != '0' or (output/'access.exit').read_text().strip() != '0':
            raise RuntimeError('retained frontend/access PASS required; no regeneration')
        if (output/'compile.exit').read_text().strip() != '2':
            raise RuntimeError('expected immutable missing-hier-make compile failure required')
        fragment = output/'die/Vdie_hier.mk'
        if not fragment.is_file():
            raise RuntimeError('fix actual generated archive-binding make fragment before compiling')
        stage(output, 'compile_r2', r['compile_top']+['-j', str(a.workers), 'CXX=g++-15'])
        stage(output, 'link_r2', r['link'])
        (output/'build_complete').write_text('canonical 5.050 retained top built with retained leaves\n')
        return
    if not (output/'build_complete').is_file():
        raise RuntimeError('one completed canonical top build required')
    if a.stage == 'layer-runtime':
        from emit import emit_layer
        layer_host = output/'host/layer.cpp'
        emit_layer(output/'host/fulltoken.cpp', layer_host)
        link = [str(layer_host) if x == str(output/'host/fulltoken.cpp') else
                str(output/'layer_test') if x == str(output/'fulltoken') else x
                for x in r['link']]
        stage(output, 'layer_driver_link', link)
        command = list(r['runtime'])
        command[0], command[3] = str(output/'layer_test'), str(output/'run_layer')
        stage(output, 'layer_runtime', command)
        log = (output/'layer_runtime.log').read_text()
        if 'QWEN_ROM_COMBINED_P0_FULLSHAPE_LAYER DONE stages=1' not in log or 'WRITEBACK drained=1' not in log:
            raise RuntimeError('actual L0 completion and protected drain required')
        comparisons, bad = [], []
        for rank in range(4):
            for suffix in ('x', 'kvP'):
                name = f'L0_die{rank}_{suffix}.hex'
                got, truth = output/'run_layer'/name, authority/'run'/name
                exact = got.is_file() and truth.is_file() and got.read_bytes() == truth.read_bytes()
                comparisons.append(dict(path=name, exact=exact,
                    sha256=hashlib.sha256(got.read_bytes()).hexdigest() if got.is_file() else None))
                if not exact:
                    bad.append(name)
        result = dict(status='FAIL_LAYER_NUMERICAL' if bad else 'PASS_FULLSHAPE_L0_P8191',
            output_comparisons=comparisons, failures=bad, full_token_pass=False,
            layers_executed=1, ranks=4, position=8191, physical_qualified=False,
            model_and_engine_archives_reused=True, next_layer_prefetch=False,
            scope='Cold full-shape L0 only; actual clocks, faults, finite transport, warm and validated ACK drain; no overlap/fullhead/all36 claim',
            core_final_visible=int(re.search(r'P0_FINAL_VISIBLE core_cycle=(\d+)', log)[1]),
            core_layer=int(re.search(r'token_cycle=(\d+)', log)[1]),
            controller_rises=int(re.search(r'P0_CLOCK controller_rises=(\d+)', log)[1]))
        (output/'layer_runtime_terminal.json').write_text(json.dumps(result, indent=2)+'\n')
        if bad:
            raise RuntimeError('actual L0 numerical comparison failed')
        return
    stage(output, 'runtime', r['runtime'])
    log = (output/'runtime.log').read_text()
    if 'QWEN_ROM_COMBINED_P0_SOURCE_JOIN DONE stages=37' not in log or 'WRITEBACK drained=1' not in log:
        raise RuntimeError('fullhead/all36/actualdrain terminal missing')
    names = [f'L{i}_die{d}_{suffix}.hex' for i in range(36) for d in range(4)
             for suffix in ('x', 'kvP')]
    names += [f'head_die{d}_{suffix}.hex' for d in range(4)
              for suffix in ('x', 'xnorm', 'result')]
    comparisons = []
    bad = []
    for name in names:
        got, expected = output/'run'/name, authority/'run'/name
        if not got.is_file() or not expected.is_file():
            bad.append(name+':missing'); continue
        data, truth = got.read_bytes(), expected.read_bytes()
        match = data == truth
        comparisons.append(dict(path=name, bytes=len(data), exact=match,
                                sha256=hashlib.sha256(data).hexdigest()))
        if not match:
            bad.append(name+':mismatch')
    result = dict(status='PASS_PROTECTED_FULL36_HEAD_P8191' if not bad else 'FAIL_NUMERICAL_OUTPUT',
        output_comparisons=comparisons, failures=bad, full_token_pass=not bad,
        position=8191, layers=36, ranks=4, released_history_images=144,
        canonical_runtime=r['version'], physical_qualified=False, adopted=False,
        numerical_truth=str(authority/'run'),
        cycles=dict(core_final_visible=int(re.search(r'P0_FINAL_VISIBLE core_cycle=(\d+)', log)[1]),
                    core_token=int(re.search(r'token_cycle=(\d+)', log)[1]),
                    controller_rises=int(re.search(r'P0_CLOCK controller_rises=(\d+)', log)[1]),
                    elapsed_fs=int(re.search(r'elapsed_fs=(\d+)', log)[1])),
        scope='Actual protected finite transport and timed numeric backing; physical qualification separate')
    (output/'runtime_terminal.json').write_text(json.dumps(result, indent=2)+'\n')
    if bad:
        raise RuntimeError('actual numerical output comparison failed')


if __name__ == '__main__':
    import sys
    out = Path(sys.argv[sys.argv.index('--output')+1])
    phase = sys.argv[sys.argv.index('--stage')+1]
    stop = threading.Event()
    observer = None if phase == 'dispatch' else threading.Thread(target=observe, args=(out, phase, stop))
    if observer:
        observer.start()
    try:
        main()
    finally:
        stop.set()
        if observer:
            observer.join()
