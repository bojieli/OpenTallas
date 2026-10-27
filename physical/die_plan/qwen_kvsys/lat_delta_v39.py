#!/usr/bin/env python3
"""KV-P8-PLAN 10-23: lane cycle deltas of a plan against a reference plan (both through gen.py latency on the same
tools): changed-cycle lanes by id, plus lanes only in one plan (ctlv4 re-cut).
usage: lat_delta_v39.py REF_PLAN NEW_PLAN > delta.json   (latency recomputed in a temp dir for both)"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

T = os.environ.get('OT_DIE_PLAN_TOOLS', str(Path(__file__).resolve().parents[3] / 'tools/die_plan'))


def lat(plan):
    d = tempfile.mkdtemp(prefix='latd_')
    p = os.path.join(d, 'p.json')
    open(p, 'w').write(open(plan).read())
    subprocess.run([sys.executable, f'{T}/gen.py', 'latency', p, '--inplace', '--out', os.path.join(d, 'lat')],
                   check=True, stdout=subprocess.DEVNULL)
    P = json.load(open(p))
    return P, P['latency']['lanes']


A, la = lat(sys.argv[1])
B, lb = lat(sys.argv[2])
note = {l['id']: l.get('note', '') for l in B['lanes']}
note.update({l['id']: l.get('note', '') for l in A['lanes'] if l['id'] not in note})
changed = {i: dict(ref=la[i]['cycles'], new=lb[i]['cycles'], delta=lb[i]['cycles'] - la[i]['cycles'], note=note[i])
           for i in la if i in lb and la[i]['cycles'] != lb[i]['cycles']}
only_new = {i: dict(cycles=lb[i]['cycles'], note=note[i]) for i in lb if i not in la}
only_ref = {i: dict(cycles=la[i]['cycles'], note=note[i]) for i in la if i not in lb}
json.dump(dict(ref=sys.argv[1], new=sys.argv[2], lanes_ref=len(la), lanes_new=len(lb),
               same_cycles=sum(1 for i in la if i in lb and la[i]['cycles'] == lb[i]['cycles']),
               changed=changed, only_new=only_new, retired=only_ref), sys.stdout, indent=1)
sys.stdout.write('\n')
