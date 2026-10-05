#!/usr/bin/env python3
"""Replay unchanged HBM G0 generators with exact archived historical inputs.

The original V1 tools remain source-pinned and byte-identical. This adapter
supplies their Git-input ABI, checks every helper/input hash, and never admits
hardware. Archive-only replay deliberately needs no historical Git objects.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import h4_v1_g0_model as V
import h4_v1_expanded_service as E
import h4_v1_physical_join as P
import h4_hbm_service_context_g0 as C

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'results/uarch/h4_hbm_service_source_closure_20261002'

def digest(b):return hashlib.sha256(b).hexdigest()

class ExactInputs:
    def __init__(self,folder=ARCHIVE,*,archive_only=False):
        self.folder=Path(folder);self.archive_only=archive_only;self.git_reads=0;self.archive_reads=0
        self.manifest=json.loads((self.folder/'manifest.json').read_text())
        self.index={(r['commit'],r['path']):r for r in self.manifest['inputs']}
        if len(self.index)!=len(self.manifest['inputs']):raise ValueError('duplicate source identity')
    def __call__(self,commit,path):
        key=(commit,path)
        if key not in self.index:raise ValueError('unarchived historical input '+repr(key))
        r=self.index[key];b=None
        if not self.archive_only:
            # Missing historical objects must not trigger a promisor fetch.
            p=subprocess.run(['git','-c','remote.origin.promisor=false','show',commit+':'+path],cwd=ROOT,capture_output=True,
                env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_TERMINAL_PROMPT':'0'})
            if p.returncode==0:b=p.stdout;self.git_reads+=1
        if b is None:
            target=(self.folder/r['archive']).resolve()
            if not target.is_relative_to(self.folder.resolve()):raise ValueError('archive path escapes input root')
            b=target.read_bytes();self.archive_reads+=1
        if len(b)!=r['bytes'] or digest(b)!=r['sha256']:raise ValueError('historical input hash mismatch '+repr(key))
        return b
    def validate(self):
        for p,sha in self.manifest['helper_pins'].items():
            if digest((ROOT/p).read_bytes())!=sha:raise ValueError('source helper mismatch '+p)
        for key in self.index:self(*key)

def replay(target,*,archive_only=False,folder=ARCHIVE):
    if target not in ('context','expanded','V1','physical'):raise ValueError('unsupported G0 generator')
    inputs=ExactInputs(folder,archive_only=archive_only);inputs.validate()
    original=V.pinned
    try:
        V.pinned=inputs
        model={'context':C.build,'expanded':E.build,'V1':V.build,'physical':P.build}[target]()
    finally:V.pinned=original
    record=ROOT/{'context':'results/uarch/h4_hbm_service_context_g0_20261002/final/model.json',
        'expanded':'results/uarch/h4_v1_expanded_service_20261002/private_routes_r4/model.json',
        'V1':'results/uarch/h4_v1_g0_model_20261002/intake/run/model.json',
        'physical':'results/uarch/h4_v1_g0_model_20261002/physical_join_r1/final/model.json'}[target]
    b=(json.dumps(model,indent=2,sort_keys=True)+'\n').encode()
    if record.read_bytes()!=b:raise ValueError('exact G0 generator replay mismatch')
    return dict(status='PASS_EXACT_ARCHIVED_G0_GENERATOR_REPLAY',target=target,archive_only=archive_only,git_reads=inputs.git_reads,archive_reads=inputs.archive_reads,model_sha256=digest(b),hardware_admitted=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',choices=['context','expanded','V1','physical'],required=True);p.add_argument('--archive-only',action='store_true');a=p.parse_args()
    print(json.dumps(replay(a.target,archive_only=a.archive_only),sort_keys=True))
