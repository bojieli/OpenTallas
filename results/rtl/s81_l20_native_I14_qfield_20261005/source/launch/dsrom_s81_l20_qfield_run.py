#!/usr/bin/env python3
"""Prestart one released I14 fragment reader, then run its existing static field host.

Consumes completed native I13 QR; each imported word receives a real VM ACK.
The two fragment runs jointly produce I14, not a full token or physical timing.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rank', type=int, choices=range(4), default=0)
    p.add_argument('--owner', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--qnorm-run', type=Path, required=True)
    p.add_argument('--fragment', type=int, choices=(0,1), required=True)
    p.add_argument('--controls', type=Path, required=True)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    terminal = json.loads((a.qnorm_run/'terminal.json').read_text())
    exit_statuses = [terminal[key] for key in ('exit', 'exit_code') if key in terminal]
    if not exit_statuses or any(type(status) is not int or status != 0
                                for status in exit_statuses):
        raise ValueError('completed actual native I11..I13 caller required')
    if 'QNORM_COMPLETE' not in (a.qnorm_run/'runtime.log').read_text():
        raise ValueError('native qnorm control/publication did not complete')
    xn = a.qnorm_run/'runtime'/f'native_L20_I13_rank{a.rank}.u32'
    raw = xn.read_bytes()
    if len(raw) != 5120:
        raise ValueError('actual I13 QR must contain 1280 raw32 words')
    input_hash = hashlib.sha256(raw).hexdigest()
    controls = a.controls/f'rank{a.rank}'
    binding = json.loads((controls/'I14/binding.json').read_text())
    expected = (37,20,4608,55744) if a.fragment==0 else (37,21,3584,60352)
    if (binding['stage'],binding['phase'],binding['rows'],binding['output_base']) != expected or (
            binding['rank'],binding['node'],binding['fragment_index']) != (a.rank,'L20.I14',a.fragment):
        raise ValueError('exact selected I14 fragment controls required')
    pair = binding['pairs'][0]
    from dsrom_s81_execution_binding import CanonicalS81Execution
    execution = CanonicalS81Execution(a.owner)
    digest = execution.source.bindings['L20.I14']['source_node_semantic_sha256']
    a.output.mkdir(parents=True, exist_ok=False)
    readers, connections = [], []
    env = dict(os.environ, DSROM_S81_NATIVE_L20_QFIELD='1',
               DSROM_S81_FIELD_QR=str(xn.resolve()),
               DSROM_S81_FIELD_CONTROLS=str(a.controls.resolve()),
               DSROM_S81_MINIMUM_SELECTED_DIR=str((controls/'I14').resolve()))
    env.setdefault('OPENBLAS_NUM_THREADS', '1')
    env.setdefault('OMP_NUM_THREADS', '1')
    started = time.monotonic()
    try:
        # All subprocess creation/checkpoint enrollment precedes native models.
        for pc in (14,):
            parent, child = socket.socketpair()
            connections.append(parent)
            cmd = [sys.executable, str(a.owner/'tools/dsrom_s81_l20_source_words.py'),
                   '--fd', str(child.fileno()), '--owner', str(a.owner),
                   '--checkpoint', str(a.checkpoint), '--kind', 'field',
                   '--node', f'L20.I{pc}', '--source-sha', digest, '--rank', str(a.rank),
                   '--fragment', str(a.fragment)]
            log = (a.output/f'I{pc}.source.log').open('w')
            readers.append(subprocess.Popen(cmd, pass_fds=(child.fileno(),), env=env,
                                            stdout=log, stderr=subprocess.STDOUT))
            log.close()
            child.close()
            ready = bytearray()
            while len(ready) < 40:
                block = parent.recv(40-len(ready))
                if not block:
                    raise RuntimeError(f'I{pc} released word source closed before READY')
                ready.extend(block)
            if ready != struct.pack('<I', 0)+bytes.fromhex(digest)+struct.pack('<I', 1):
                raise ValueError(f'I{pc} released source READY mismatch')
            env[f'DSROM_S81_FIELD_I{pc}_FD'] = str(parent.fileno())
        pair_kind = 'pb' if pair in execution.stage_join.stage_map['BF_site_IDs'] else 'pq'
        cmd = [str(a.binary.resolve()), pair_kind, '37', str(a.rank), str(pair),
               str((controls/f'I14/e{pair}.cfg.hex').resolve()), str(a.output/'runtime'), '-',
               '/tmp/unused-native-field-fallback.sock']
        (a.output/'runtime.argv.json').write_text(json.dumps(cmd, indent=2)+'\n')
        with (a.output/'runtime.log').open('w') as log:
            runtime = subprocess.Popen(cmd, pass_fds=tuple(c.fileno() for c in connections),
                                       env=env, stdout=log, stderr=subprocess.STDOUT)
            (a.output/'runtime.pid').write_text(str(runtime.pid)+'\n')
            print(f'NATIVE_FIELD_PID={runtime.pid} log={a.output}/runtime.log', flush=True)
            rc = runtime.wait()
        if hashlib.sha256(xn.read_bytes()).hexdigest() != input_hash:
            raise ValueError('actual QR changed during execution')
        (a.output/'terminal.json').write_text(json.dumps(dict(
            scope='native I13 boundary import -> native I14 selected fragment', exit_code=rc,
            elapsed_seconds=time.monotonic()-started, numerical_verdict=None,
            full_token=False, native_prefix_timing=False, rank=a.rank,
            fragment=a.fragment, output_base=binding['output_base'], rows=binding['rows'],
            input_path=str(xn), input_sha256=input_hash), indent=2)+'\n')
        return rc
    except Exception as error:
        (a.output/'terminal.json').write_text(json.dumps(dict(
            scope='released field source prestart/native caller',
            disposition='LAUNCH_ERROR', error=str(error), numerical_verdict=None,
            elapsed_seconds=time.monotonic()-started), indent=2)+'\n')
        raise
    finally:
        for connection in connections:
            connection.close()
        for reader in readers:
            reader.wait()  # Existing source children drain on EOF; no restart.


if __name__ == '__main__':
    raise SystemExit(main())
