#!/usr/bin/env python3
"""Expand exact SV preprocessor context, then select canonical module definitions.

Parameter generate guards remain intact for actual elaboration. No missing-module
stubs, parameter changes, native tieoffs or warning waivers are introduced.
"""
import argparse,bisect,collections,hashlib,json,re,shutil,subprocess
from pathlib import Path
from stage_bound_die import INST,KW
from bound_module_closure import masked
BLOCK=re.compile(r'\bmodule\s+(?:automatic\s+)?(\w+)\b.*?\bendmodule\b',re.S)
LINE=re.compile(r'^\s*`line\s+\d+\s+"([^"]+)"\s+\d+',re.M)

def prepare(stage,manifest,repo,out,module_sources=None):
    module_sources=module_sources or {}
    if out.exists():raise ValueError('Fresh output required; failed stages are immutable')
    out.mkdir(parents=True);shutil.copytree(stage/'bound',out/'bound');shutil.copy2(stage/'bind_report.json',out/'bind_report.json')
    meta=json.loads((stage/'staging.json').read_text());ab=json.loads(manifest.read_text())
    paths=[];flags=[]
    for line in(stage/'sim.f').read_text().splitlines():
        if line.startswith('+'):flags.append(line)
        elif line:paths.append(Path(line[3:]if line.startswith('-v ')else line))
    preferred=[]
    for name in ab.get('prefer',[]):
        p=(repo/name).resolve()
        if not p.is_file():raise ValueError('Authoritative prefer source missing: '+str(p))
        snapshot=stage/'readset'/str(p).lstrip('/')
        if snapshot.is_file():
            if snapshot.read_bytes()!=p.read_bytes():raise ValueError('Canonical source changed since frozen stage: '+str(p))
            p=snapshot
        preferred.append(p)
    inputs=list(dict.fromkeys(paths+preferred+list(module_sources.values())))
    # Read existing order first, canonical preferred definitions last, as in the
    # as-built source readset. Preprocessing has no hierarchy/parameter lowering.
    (out/'preprocess_inputs.f').write_text('\n'.join(flags+[str(p)for p in inputs])+'\n')
    with(out/'all_preprocessed.sv').open('w')as stdout,(out/'preprocess.err').open('w')as stderr:
        rc=subprocess.run([str(Path.home()/'.local/opentallas-tools/bin/verilator'),'-E','-f',str(out/'preprocess_inputs.f')],stdout=stdout,stderr=stderr).returncode
    (out/'preprocess.rc').write_text(str(rc)+'\n')
    if rc:raise ValueError('Real Verilator preprocessing failed; see preprocess.err')
    raw=(out/'all_preprocessed.sv').read_text();mask=masked(raw)
    if re.search(r'^\s*`(?:ifdef|ifndef|elsif|else|endif|define|undef|include)\b',mask,re.M):
        raise ValueError('Preprocessor left unresolved conditional/macro/include directives')
    origins=list(LINE.finditer(raw));positions=[m.start()for m in origins]
    records=[];defs=collections.defaultdict(list)
    for m in BLOCK.finditer(mask):
        start=m.start()
        # Attributes belong to the following module, never to its successor.
        while True:
            before=mask[:start].rstrip()
            if not before.endswith('*)'):break
            attr=before.rfind('(*')
            if attr<0:raise ValueError('Unmatched module attribute')
            start=attr
        index=bisect.bisect_right(positions,m.start())-1
        origin=Path(origins[index][1])if index>=0 else None
        rec=dict(name=m[1],start=start,end=m.end(),origin=origin)
        records.append(rec);defs[m[1]].append(rec)
    pref_rank={p:i for i,p in enumerate(preferred)}
    model_names=meta.get('macro_model_map',{})
    selected={}
    for name,choices in defs.items():
        scoped=[r for r in choices if name in module_sources and r['origin']==module_sources[name]]
        if name in module_sources and not scoped:raise ValueError('Explicit module source not found after preprocessing: '+name)
        models=[r for r in choices if name in model_names and r['origin']and r['origin'].name==Path(model_names[name]).name]
        canon=[r for r in choices if r['origin']in pref_rank]
        selected[name]=(scoped[-1]if scoped else models[-1]if models else max(canon,key=lambda r:pref_rank[r['origin']])if canon else choices[0])
    topfile=next((stage/'bound').glob('*_bound_top.sv'))
    topmatch=BLOCK.search(masked(topfile.read_text()));top=topmatch[1]
    todo=[top];chosen={};unknown=set();refs=collections.defaultdict(list)
    while todo:
        name=todo.pop()
        if name in chosen or name in unknown:continue
        if name not in selected:unknown.add(name);continue
        rec=selected[name];chosen[name]=rec
        for dep,inst in INST.findall(mask[rec['start']:rec['end']]):
            if dep not in KW and inst not in KW:
                todo.append(dep);refs[dep].append(dict(parent=name,instance=inst,origin=str(rec['origin'])))
    output=[];last=0;checks=[];removed=[]
    for rec in records:
        output.append(raw[last:rec['start']]);body=raw[rec['start']:rec['end']]
        if chosen.get(rec['name'])is rec:
            output.append(body);checks.append(dict(module=rec['name'],origin=str(rec['origin']),sha256=hashlib.sha256(body.encode()).hexdigest()))
        else:
            # Macro/include/conditional effects are already resolved by -E.
            # Keep compiler directives (timescale/nettype/etc.) in original order.
            output.extend(line+'\n'for line in body.splitlines()if line.lstrip().startswith('`'))
            removed.append(dict(module=rec['name'],origin=str(rec['origin'])))
        last=rec['end']
    output.append(raw[last:]);result=''.join(output)
    actual={m[1]:result[m.start():m.end()]for m in BLOCK.finditer(masked(result))}
    for name,rec in chosen.items():
        # Attribute prefix is checked independently; module text must be identical
        # to its real-preprocessed source before filtering.
        before=BLOCK.search(mask[rec['start']:rec['end']]);expected=raw[rec['start']+before.start():rec['end']]
        if actual.get(name)!=expected:raise ValueError('Changed preprocessed used module: '+name)
    (out/'selected_preprocessed.sv').write_text(result)
    (out/'sim.f').write_text(str(out/'selected_preprocessed.sv')+'\n')
    unresolved=[dict(module=n,references=refs[n])for n in sorted(unknown)]
    receipt=dict(status='REQUIRES_ACTUAL_PARAMETER_ELABORATION',scope='Source selection, not numeric G5',
        top=top,verilator_preprocessor_rc=rc,declared_defines=ab.get('defines',[]),
        input_files=len(inputs),canonical_prefer_files=len(preferred),selected_modules=len(chosen),
        unchanged_preprocessed_module_bodies=checks,removed_modules=removed,
        unresolved_constructors=unresolved,active_unknown_modules_remain_errors=True,
        macro_model_overrides_only=list(model_names),explicit_module_sources={k:str(v)for k,v in module_sources.items()},native_required_ports_preserved=True,bind_verdict_preserved=True)
    (out/'module_closure.json').write_text(json.dumps(receipt,indent=1)+'\n')
    meta.update(files=1,top=str(out/'bound'/topfile.name),portable=True,
        parameter_elaboration_status=receipt['status'],unresolved_constructors=unresolved,
        module_closure='module_closure.json',blackboxes=['DECLARED IN SELECTED PREPROCESSED SOURCE']if re.search(r'\(\*\s*blackbox\b',masked(result))else{})
    (out/'staging.json').write_text(json.dumps(meta,indent=1)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()if k not in ['unchanged_preprocessed_module_bodies','removed_modules']}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['stage','manifest','repo','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--module-source-map',type=Path)
    a=p.parse_args();sources={}if a.module_source_map is None else{k:Path(v).resolve()for k,v in json.loads(a.module_source_map.read_text()).items()}
    prepare(a.stage.resolve(),a.manifest.resolve(),a.repo.resolve(),a.out.resolve(),sources)
