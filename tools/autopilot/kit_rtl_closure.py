#!/usr/bin/env python3
"""Localize producer RTL before native preparation, then seal its output for roaming."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


OMIT_SIDECARS=('bind_sinks.json',)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _files(kd):
    return [Path(s) for s in (kd/'kit_rtl.f').read_text().splitlines() if s.strip()]


def relocate(directory):
    """Only runtime package prefixes change; original roots/origins remain immutable."""
    kd=Path(directory).absolute(); mf=kd/'kit_rtl.json'
    if not mf.is_file():return {}
    meta=json.loads(mf.read_text());c=meta.get('input_closure')
    if not c:return {}
    old=c['runtime_directory'];new=str(kd)
    if old==new:return {}
    oldroot=str(Path(old).parent);newroot=str(kd.parent)
    def rewrite(x):
        if isinstance(x,dict):
            return {k:(dict(v,runtime_directory=new) if k=='input_closure' else rewrite(v)) for k,v in x.items()}
        if isinstance(x,list):return [rewrite(v) for v in x]
        if isinstance(x,str) and x.startswith(oldroot+'/'):return newroot+x[len(oldroot):]
        return x
    for p in (mf,kd/'kit_topology.json',kd/'kit_topology_prepared.json'):
        if p.is_file():p.write_text(json.dumps(rewrite(json.loads(p.read_text())),indent=1)+'\n')
    for p in kd.glob('kit_rtl*.f'):
        p.write_text('\n'.join(str(rewrite(s)) for s in p.read_text().splitlines())+'\n')
    for p in (kd.parent/'gen').glob('*/kit_rtl_paths.json'):
        p.write_text(json.dumps(rewrite(json.loads(p.read_text())),indent=1)+'\n')
    return dict(old_runtime_directory=old,runtime_directory=new)


def inputs(directory, source):
    kd=Path(directory).absolute();actual=kd.resolve();mf=kd/'kit_rtl.json'
    meta=json.loads(mf.read_text()) if mf.is_file() else {}
    if meta.get('input_closure'):raise ValueError('KIT_RTL_CLOSURE inputs already localized; regenerate a fresh attempt')
    roots=[Path(source).resolve(),actual]
    bo=Path(meta['bind_out']).resolve() if meta.get('bind_out') else None
    if bo:roots.append(bo)
    fs=[p.resolve() for p in _files(kd)]
    if len({p.name for p in fs})!=len(fs):raise ValueError('KIT_RTL_CLOSURE duplicate source basename')
    for p in fs:
        if not p.is_file() or not any(p.is_relative_to(r) for r in roots):
            raise ValueError(f'KIT_RTL_CLOSURE invalid source {p}; allowed roots {roots}')
    origins={};new=[]
    for p in fs:
        if p.is_relative_to(actual):target=kd/p.relative_to(actual)
        elif p.stem==meta.get('bound_module'):target=kd/p.name
        else:target=kd/'closure'/'root'/str(p).lstrip('/')
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.resolve()!=p:
            if target.exists() and target.read_bytes()!=p.read_bytes():raise ValueError(f'KIT_RTL_CLOSURE different existing source {target}')
            shutil.copyfile(p,target)
        origins[str(target.relative_to(kd))]=dict(original=str(p),sha256=digest(target))
        new.append(str(target))
    if mf.is_file():shutil.copyfile(mf,kd/'kit_rtl.producer.json')
    meta['files']=new
    meta['input_closure']=dict(schema='opentallas.kit_rtl_closure.v1',roots=list(map(str,roots)),producer_directory=str(kd),runtime_directory=str(kd),producer_bind_out=str(bo) if bo else None,files=origins,sealed=False)
    # Native preparation still verifies the complete original bind on its producer.
    (kd/'kit_rtl.f').write_text('\n'.join(new)+'\n')
    sim=kd/'kit_rtl_sim.f'
    if sim.is_file():
        mp={str(a):b for a,b in zip(fs,new)}
        sim.write_text('\n'.join(mp.get(str(Path(s).resolve()),s) if s.strip() else s for s in sim.read_text().splitlines())+'\n')
    mf.write_text(json.dumps(meta,indent=1)+'\n')
    return dict(files=len(new),phase='INPUTS_LOCALIZED')


def seal(directory):
    kd=Path(directory).absolute();relocate(kd);mf=kd/'kit_rtl.json';meta=json.loads(mf.read_text());c=meta['input_closure'];origins=c['files']
    topo=kd/'kit_topology.json';stamp=kd/'kit_topology_prepared.json';prepared=None
    if topo.is_file() or stamp.is_file():
        t=json.loads(topo.read_text());s=json.loads(stamp.read_text());bound=kd/(meta['bound_module']+'.sv')
        if t.get('problems') or t.get('source_sha256')!=digest(bound) or s.get('source_sha256')!=digest(bound):
            raise ValueError('KIT_RTL_CLOSURE canonical preparation source receipt mismatch')
        prepared=dict(topology_sha256=digest(topo),prepared_sha256=digest(stamp))
    for p in _files(kd):
        rel=str(p.relative_to(kd));old=origins.get(rel)
        if old is None:raise ValueError(f'KIT_RTL_CLOSURE unrecorded preparation input {p}')
        sha=digest(p)
        if sha!=old['sha256']:
            allowed=p.stem==meta.get('bound_module') or bool(meta.get('kit_native_source_banks',{}).get('banks'))
            if c.get('sealed') or not prepared or not allowed:raise ValueError(f'KIT_RTL_CLOSURE source changed without canonical preparation: {p}')
            old['input_sha256']=old['sha256'];old['sha256']=sha;old['canonical_preparation']=prepared
    if c.get('sealed'):return dict(files=len(_files(kd)),phase='ALREADY_SEALED')
    def stage(p):
        p=Path(p).resolve();actual=kd.resolve()
        target=kd/p.relative_to(actual) if p.is_relative_to(actual) else kd/'closure'/'root'/str(p).lstrip('/')
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.resolve()!=p:shutil.copyfile(p,target)
        rel=str(target.relative_to(kd))
        if rel not in origins:origins[rel]=dict(original=str(p),sha256=digest(target))
        return str(target)
    def walk(x):
        if isinstance(x,dict):return {k:(v if k=='input_closure' else walk(v)) for k,v in x.items()}
        if isinstance(x,list):return [walk(v) for v in x]
        if isinstance(x,str) and x.startswith('/') and Path(x).is_file():return stage(x)
        return x
    meta=walk(meta)
    sim=kd/'kit_rtl_sim.f'
    if sim.is_file():
        sim.write_text('\n'.join(stage(Path(v)) if v.strip() else v for v in sim.read_text().splitlines())+'\n')
    bo=kd/'closure'/'bind';bo.mkdir(parents=True,exist_ok=True)
    original=Path(c['producer_bind_out']) if c.get('producer_bind_out') else None
    if original:
        # All small bind sidecars include native topology, ties, IDs and source
        # preparation proofs. The full asbuilt netlist is not a GEN input.
        for p in original.glob('*.json'):
            if p.name=='asbuilt.json':continue
            if p.name in OMIT_SIDECARS:
                # KIT-SLIM-1118 (COORD): the die-wide sinks file (2.36 GB, copied into EVERY attempt = 60% of the live kit disk) is read by no kit step
                # (GEN, preflight, kit lint, LEC read bind_report / native_topology / parent_id_straps; bind_verify and type_split read the die bind out).
                # It stays at its read-only die-level origin; no copy and no origin entry (the lint hashes every entry).
                (bo/(p.stem+'.omitted.json')).write_text(json.dumps(dict(original=str(p),size=p.stat().st_size,reason='die-level, read-only; no kit step reads it'))+'\n')
                continue
            shutil.copyfile(p,bo/p.name)
            origins[str((bo/p.name).relative_to(kd))]=dict(original=str(p),sha256=digest(bo/p.name))
    meta['bind_out']=str(bo);meta['input_closure']['sealed']=True
    meta['input_closure']['canonical_preparation']=prepared
    mf.write_text(json.dumps(meta,indent=1)+'\n')
    return dict(files=len(_files(kd)),closure_files=len(origins),phase='SEALED_AFTER_PREPARATION')


def package(directory,source):
    inputs(directory,source)
    return seal(directory)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('directory');ap.add_argument('--source');ap.add_argument('--mode',choices=('package','inputs','seal','relocate'),default='package');a=ap.parse_args()
    if a.mode in ('package','inputs') and not a.source:ap.error('--source required for input localization')
    result=package(a.directory,a.source) if a.mode=='package' else inputs(a.directory,a.source) if a.mode=='inputs' else seal(a.directory) if a.mode=='seal' else relocate(a.directory)
    print('KIT_RTL_CLOSURE '+json.dumps(result))
