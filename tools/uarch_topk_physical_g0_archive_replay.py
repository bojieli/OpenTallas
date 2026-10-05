#!/usr/bin/env python3
"""Replay unchanged dd45 full-selector model with verified exact origin archive.

Default: git-preferred; fallback ONLY when the requested commit is unavailable.
Explicit archive-only mode removes historical git-object dependencies. Neither
mode bypasses current repository generator/inventory byte identity checks.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'results/uarch/topk_physical_g0_source_archive_20261002'
MANIFEST_SHA='b8caa84da075e8380cf9fec886e5de09ad2a19940ea4631b2dc85dd144c3488a'
BUILDER_SHA='77800eea381bb5c81d1a6da381c3714398d5b8fdc815d82514932caced8062a6'
MODEL_SHA='d2add26b19ab9161b22a559eb27bfa29760e950b0eb9df3db24098b0e6244c2a'
FULL='aa745a879e20e3db598f7be9345cb7ad3b1d5d2f'
INVENTORY='tools/uarch_topk_integer_tree_model.py'

def digest(data):return hashlib.sha256(data).hexdigest()

class SourceArchive:
    def __init__(self,repo,archive=ARCHIVE,mode='git-preferred'):
        self.repo=Path(repo).resolve();self.archive=Path(archive).resolve();self.mode=mode
        if mode not in {'git-preferred','archive-only'}:raise ValueError('explicit source mode required')
        raw=(self.archive/'source_manifest.json').read_bytes()
        if digest(raw)!=MANIFEST_SHA:raise ValueError('archive manifest pin mismatch')
        manifest=json.loads(raw)
        if manifest['baseline_generator_sha256']!=BUILDER_SHA or manifest['baseline_model_sha256']!=MODEL_SHA:
            raise ValueError('archive baseline mismatch')
        self.origins={};self.contents={};self.used={};self.availability={}
        for entry in manifest['origins']:
            key=entry['commit']+':'+entry['path']
            if key in self.origins:raise ValueError('duplicate origin')
            path=(self.archive/entry['archive_path']).resolve()
            if not path.is_relative_to(self.archive):raise ValueError('archive path escapes package')
            data=path.read_bytes()
            if len(data)!=entry['bytes'] or digest(data)!=entry['sha256']:
                raise ValueError('exact archived origin bytes changed: '+key)
            self.origins[key]=entry;self.contents[key]=data
        if mode=='git-preferred':
            subprocess.run(['git','rev-parse','--git-dir'],cwd=self.repo,check=True,capture_output=True)

    def commit_available(self,commit):
        if commit not in self.availability:
            result=subprocess.run(['git','rev-parse','--verify','--quiet',commit+'^{commit}'],cwd=self.repo,capture_output=True)
            if result.returncode not in {0,1}:raise RuntimeError('git commit availability probe failed; archive fallback forbidden')
            self.availability[commit]=result.returncode==0
        return self.availability[commit]

    def read(self,commit,path):
        key=commit+':'+path
        if key not in self.origins:raise ValueError('unarchived origin refused: '+key)
        entry=self.origins[key]
        if self.mode=='archive-only':
            data=self.contents[key];basis='explicit_verified_archive_only'
        elif not self.commit_available(commit):
            data=self.contents[key];basis='verified_archive_commit_unavailable'
        else:
            # Missing path/read error/corruption in an AVAILABLE commit must
            # fail; it is never grounds for an archive fallback.
            data=subprocess.check_output(['git','show',key],cwd=self.repo,stderr=subprocess.PIPE)
            if len(data)!=entry['bytes'] or digest(data)!=entry['sha256']:
                raise ValueError('available git origin differs from authoritative pin: '+key)
            basis='available_git_origin_verified'
        self.used[key]=basis
        return data

    def check_output(self,args,*,cwd):
        # Adapter is local to the imported original module, not a global
        # subprocess patch. Only its exact pinned git-show reads are accepted.
        if args[:2]!=['git','show'] or len(args)!=3 or Path(cwd).resolve()!=self.repo:
            raise ValueError('unsupported baseline source read')
        commit,path=args[2].split(':',1)
        return self.read(commit,path)

def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def replay(repo,archive=ARCHIVE,mode='git-preferred'):
    sources=SourceArchive(repo,archive,mode)
    repo=sources.repo
    inventory=repo/INVENTORY
    # Actual current-main bytes remain mandatory, even in archive-only mode.
    if inventory.read_bytes()!=sources.contents[FULL+':'+INVENTORY]:
        raise ValueError('actual repository inventory T bytehash changed')
    builder_path=repo/'tools/uarch_topk_physical_g0_inputs.py'
    if digest(builder_path.read_bytes())!=BUILDER_SHA:raise ValueError('actual baseline generator bytehash changed')
    imported_inventory=load_module(inventory,'verified_current_inventory_T')
    old=sys.modules.get('uarch_topk_integer_tree_model')
    try:
        sys.modules['uarch_topk_integer_tree_model']=imported_inventory
        builder=load_module(builder_path,'verified_dd45_physical_builder')
    finally:
        if old is None:sys.modules.pop('uarch_topk_integer_tree_model',None)
        else:sys.modules['uarch_topk_integer_tree_model']=old
    if Path(builder.T.__file__).resolve()!=inventory.resolve():raise ValueError('inventory import did not bind actual repository source')
    builder.subprocess=SimpleNamespace(check_output=sources.check_output)
    model=builder.build(repo)
    if inventory.read_bytes()!=sources.contents[FULL+':'+INVENTORY] or digest(builder_path.read_bytes())!=BUILDER_SHA:
        raise ValueError('actual repository source changed during replay')
    data=(json.dumps(model,indent=2,sort_keys=True)+'\n').encode()
    if digest(data)!=MODEL_SHA:raise ValueError('replay differs from preserved full physical model')
    if set(sources.used)!=set(sources.origins):raise ValueError('archive origin census differs from baseline reads')
    return data,{'schema':'TOPK_EXACT_ORIGIN_ARCHIVE_REPLAY_RECEIPT_V1','source_mode':mode,
        'manifest_sha256':MANIFEST_SHA,'origin_modes':sources.used,'origins_verified':len(sources.origins),
        'archive_bytes_verified':sum(e['bytes'] for e in sources.origins.values()),
        'baseline_generator_sha256':BUILDER_SHA,'actual_repository_inventory_sha256':digest(inventory.read_bytes()),
        'actual_repository_inventory_checked':True,'regenerated_model_sha256':digest(data),
        'byte_exact_preserved_model':True,'RTL_admitted':False,'PR_admitted':False,'jobs_launched':0}

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=ROOT)
    p.add_argument('--archive',type=Path,default=ARCHIVE)
    p.add_argument('--source-mode',choices=['git-preferred','archive-only'],default='git-preferred')
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(exist_ok=False)
    try:
        data,receipt=replay(a.repo,a.archive,a.source_mode)
        (a.out/'model.json').write_bytes(data)
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    except Exception as error:
        (a.out/'failure.json').write_text(json.dumps({'exception_type':type(error).__name__,'exception':str(error)},indent=2,sort_keys=True)+'\n')
        raise
    print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__':main()
