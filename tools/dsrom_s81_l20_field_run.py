#!/usr/bin/env python3
"""Prestart released I7/I8 word readers, then run the existing static field host.

Consumes produced I6 raw XN; the native caller establishes real VM publication.
This is a SIM_ONLY prefix/native-field component chain, not a full token.
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
    p.add_argument('--owner', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--controls', type=Path, required=True)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    manifest = json.loads((a.inputs/'native_field_inputs.json').read_text())
    if (manifest['source_node'], manifest['producer'], manifest['address'], manifest['count'],
        manifest['position'], manifest['token'], manifest['instructions_completed'],
        manifest['expected_outputs_used']) != ('L20.I6', 2476, 46464, 5120, 1048575, 16754, 7, False):
        raise ValueError('actual produced I6 source binding required')
    xn = a.inputs/'I6.XN_rank0.u32'
    if len(xn.read_bytes()) != 20480 or hashlib.sha256(xn.read_bytes()).hexdigest() != manifest['files'][xn.name]:
        raise ValueError('produced XN file differs from its retained output')
    a.output.mkdir(parents=True, exist_ok=False)
    readers, connections = [], []
    env = dict(os.environ, DSROM_S81_NATIVE_L20_FIELD='1',
               DSROM_S81_FIELD_XN=str(xn.resolve()),
               DSROM_S81_FIELD_CONTROLS=str(a.controls.resolve()),
               DSROM_S81_MINIMUM_SELECTED_DIR=str((a.controls/'I7').resolve()))
    env.setdefault('OPENBLAS_NUM_THREADS', '1')
    env.setdefault('OMP_NUM_THREADS', '1')
    started = time.monotonic()
    try:
        # All subprocess creation/checkpoint enrollment precedes native models.
        for pc, digest in [(7, '3ad9f39747a82b3115a4baac15528c5b1d34f1d74e4e44b3cd1ecbcac327ff21'),
                           (8, '551f69fe74da7ce321539ac115e34879ee736061a5107bbd9e8cfaf3fc6ca0a2')]:
            parent, child = socket.socketpair()
            connections.append(parent)
            cmd = [sys.executable, str(a.owner/'tools/dsrom_s81_l20_source_words.py'),
                   '--fd', str(child.fileno()), '--owner', str(a.owner),
                   '--checkpoint', str(a.checkpoint), '--kind', 'field',
                   '--node', f'L20.I{pc}', '--source-sha', digest, '--rank', '0']
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
        cmd = [str(a.binary.resolve()), 'pb', '37', '0', '11',
               str((a.controls/'I7/e11.cfg.hex').resolve()), str(a.output/'runtime'), '-',
               '/tmp/unused-native-field-fallback.sock']
        (a.output/'runtime.argv.json').write_text(json.dumps(cmd, indent=2)+'\n')
        with (a.output/'runtime.log').open('w') as log:
            runtime = subprocess.Popen(cmd, pass_fds=tuple(c.fileno() for c in connections),
                                       env=env, stdout=log, stderr=subprocess.STDOUT)
            (a.output/'runtime.pid').write_text(str(runtime.pid)+'\n')
            print(f'NATIVE_FIELD_PID={runtime.pid} log={a.output}/runtime.log', flush=True)
            rc = runtime.wait()
        (a.output/'terminal.json').write_text(json.dumps(dict(
            scope='SIM_ONLY I0..I6 -> native static stage37 I7/I8', exit_code=rc,
            elapsed_seconds=time.monotonic()-started, numerical_verdict=None,
            full_token=False, native_prefix_timing=False), indent=2)+'\n')
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
