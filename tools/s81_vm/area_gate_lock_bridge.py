#!/usr/bin/env python3
"""Forward remote gate lock checks to the actual coordinator lock over job stdin.

Remote workers have no copy of the authoritative lock. Each explicit gate check
requests a fresh read by the local admitted-job launcher; no copied lease or
disabled check is substituted. ot-run preserves this stdin/stdout exchange.
"""
import argparse
import importlib
import json
from pathlib import Path
import subprocess
import sys

MARKER='__S81_AUTHORITATIVE_LOCK_READ__'
LOCK=Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')

class RemoteLock:
    def read_text(self):
        print(MARKER,flush=True)
        response=sys.stdin.readline()
        if not response:raise RuntimeError('authoritative coordinator lock channel closed')
        json.loads(response)
        return response

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--gate',required=True)
    ap.add_argument('--remote',action='store_true')
    ap.add_argument('--remote-dir',default='/srv/opentallas-scratch/codex/s81-vm-area-1417')
    ap.add_argument('--mem',default='10');ap.add_argument('--run',action='store_true')
    args=ap.parse_args()
    if args.remote:
        gate=importlib.import_module(args.gate)
        gate.LOCK=RemoteLock()
        sys.argv=[args.gate]+(['--run'] if args.run else [])
        gate.main();return
    actual=json.loads(LOCK.read_text())
    assert actual['owner'] in ('claude','codex'),'coordinator ownership changed'
    command=['ot-run','--mem',args.mem,'--threads','1','--dir',args.remote_dir,'--',
             'python3','tools/s81_vm/area_gate_lock_bridge.py','--remote','--gate',args.gate]
    if args.run:command+=['--run']
    child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                           text=True,bufsize=1)
    count=0
    for line in child.stdout:
        if line.strip()==MARKER:
            response=LOCK.read_text();json.loads(response)
            child.stdin.write(response.strip()+'\n');child.stdin.flush();count+=1
        else:
            print(line,end='',flush=True)
    rc=child.wait()
    print(f'authoritative_lock_checks={count} admitted_gate_exit={rc}',flush=True)
    raise SystemExit(rc)

if __name__=='__main__':main()
