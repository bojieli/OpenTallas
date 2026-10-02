#!/usr/bin/env python3
"""Strict successor: historical fallback requires proven local object absence.

The manifest and archived origins are authenticated before every input use.
An available commit with a missing/unreadable path never falls back. Original
generators, receipts, and the first portable wrapper remain unchanged.
"""
import argparse
import hashlib
import json
import os
import subprocess
import h4_hbm_service_source_closure as B

MANIFEST_SHA256='cb5e762e4b33406b74f43ced1e793e38b0b4002b92724e157cb9b943ab140292'
BASE_WRAPPER_SHA256='ddc5ad5d4727496a7115e0c01e3865ba740b225a5dfff186bdb617eae9a42dfa'

class ExactInputs(B.ExactInputs):
    def __init__(self,folder=B.ARCHIVE,*,archive_only=False):
        if hashlib.sha256(B.Path(B.__file__).read_bytes()).hexdigest()!=BASE_WRAPPER_SHA256:
            raise ValueError('portable wrapper helper source hash mismatch')
        if B.digest((B.Path(folder)/'manifest.json').read_bytes())!=MANIFEST_SHA256:
            raise ValueError('expected origin manifest hash mismatch')
        super().__init__(folder,archive_only=archive_only)
        self.probes=0
    def git(self,args,**kwargs):
        # 2.34 does not support --no-lazy-fetch. Disable every configured
        # promisor remote, including non-origin names, for each object probe.
        env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_TERMINAL_PROMPT':'0'}
        config=subprocess.run(['git','config','--local','--get-regexp',r'^remote\..*\.promisor$'],
            cwd=B.ROOT,capture_output=True,env=env)
        if config.returncode not in (0,1) or config.stderr or (config.returncode==1 and config.stdout):
            raise ValueError('Git promisor configuration probe failed')
        switches=['-c','remote.origin.promisor=false']
        for line in config.stdout.decode().splitlines():
            key,value=line.split(None,1)
            if not key.startswith('remote.') or not key.endswith('.promisor'):
                raise ValueError('invalid Git promisor configuration')
            switches+=['-c',key+'=false']
        return subprocess.run(['git',*switches,*args],cwd=B.ROOT,capture_output=True,env=env,**kwargs)
    def __call__(self,commit,path):
        key=(commit,path)
        if key not in self.index:raise ValueError('unarchived historical input '+repr(key))
        r=self.index[key];target=(self.folder/r['archive']).resolve()
        if not target.is_relative_to(self.folder.resolve()):raise ValueError('archive path escapes input root')
        origin=target.read_bytes()
        if len(origin)!=r['bytes'] or B.digest(origin)!=r['sha256']:
            raise ValueError('exact archived origin hash mismatch '+repr(key))
        if self.archive_only:self.archive_reads+=1;return origin
        full=r['full_commit'];probe=self.git(['rev-parse','--verify','--quiet',full+'^{commit}']);self.probes+=1
        if probe.returncode==0:
            if probe.stdout!=full.encode()+b'\n' or probe.stderr:raise ValueError('Git commit availability probe identity mismatch')
            read=self.git(['show',full+':'+path])
            if read.returncode!=0 or read.stderr:raise ValueError('available commit input read failed; fallback refused '+repr(key))
            if read.stdout!=origin:raise ValueError('available Git input differs from exact archived origin '+repr(key))
            self.git_reads+=1;return read.stdout
        if probe.returncode!=1 or probe.stdout or probe.stderr:
            raise ValueError('Git commit availability probe failed; fallback refused')
        # A failed commit peel is not sufficient: a present noncommit object
        # must reject too. Batch-check distinguishes absence from Git errors.
        absent=self.git(['cat-file','--batch-check'],input=full.encode()+b'\n')
        if absent.returncode!=0 or absent.stderr or absent.stdout!=full.encode()+b' missing\n':
            raise ValueError('true Git object absence not established; fallback refused')
        self.archive_reads+=1;return origin

def replay(target,*,archive_only=False,folder=B.ARCHIVE):
    original=B.ExactInputs
    try:
        B.ExactInputs=ExactInputs
        result=B.replay(target,archive_only=archive_only,folder=folder)
    finally:B.ExactInputs=original
    result['loader_contract']='STRICT_OBJECT_ABSENCE_ONLY'
    result['origin_manifest_sha256']=MANIFEST_SHA256
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',choices=['context','expanded','V1','physical'],required=True);p.add_argument('--archive-only',action='store_true');a=p.parse_args()
    print(json.dumps(replay(a.target,archive_only=a.archive_only),sort_keys=True))
