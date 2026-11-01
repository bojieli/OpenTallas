#!/usr/bin/env python3
"""Select actual as-built preferred definitions and omit unreachable library modules.

Used module bodies remain byte-identical. No native ports, clocks, parameters or
RTL expressions are modified. Removed module-local macros fail closed.
"""
import argparse,collections,hashlib,json,re,shutil
from pathlib import Path
from stage_bound_die import INST,KW,portable_sources
BLOCK=re.compile(r'\bmodule\s+(?:automatic\s+)?(\w+)\b.*?\bendmodule\b',re.S)

def masked(s):
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',lambda m:re.sub(r'[^\n]',' ',m[0]),s,flags=re.S)

def blocks(p):
    raw=p.read_text(errors='replace');return raw,list(BLOCK.finditer(masked(raw)))

def prepare(stage,manifest,repo,out):
    if out.exists():raise ValueError('New output required; preserve failed source stage')
    shutil.copytree(stage,out)
    lines=[s.replace(str(stage),str(out))for s in (stage/'sim.f').read_text().splitlines()]
    inputs=[Path(s[3:]if s.startswith('-v ')else s)for s in lines if s and not s.startswith('+')]
    directives=[s for s in lines if s.startswith('+define+')]
    allblocks={};defs=collections.defaultdict(list)
    for p in inputs:
        raw,mods=blocks(p);allblocks[p]=(raw,mods)
        for m in mods:defs[m[1]].append(p)
    ab=json.loads(manifest.read_text());preferred={};missing_prefer=[]
    for item in ab.get('prefer',[]):
        p=(repo/item).resolve()
        if not p.is_file():missing_prefer.append(str(p));continue
        raw,mods=blocks(p)
        snapshot=out/'readset'/str(p).lstrip('/')
        if snapshot in allblocks:
            if allblocks[snapshot][0]!=raw:raise ValueError('Authoritative source changed since snapshot: '+str(p))
            p=snapshot
        allblocks[p]=(raw,mods)
        for m in mods:preferred[m[1]]=p
    if missing_prefer:raise ValueError('Missing authoritative prefer files: '+str(missing_prefer))
    # External PHY models explicitly replace only the four named macro definitions.
    model_names=json.loads((stage/'staging.json').read_text()).get('macro_model_map',{})
    overrides={m:next(p for p in inputs if p.name==Path(v).name and any(b[1]==m for b in allblocks[p][1]))for m,v in model_names.items()}
    top=next((out/'bound').glob('*_bound_top.sv'));topname=blocks(top)[1][0][1]
    todo=[topname];chosen={};missing=set();references=collections.defaultdict(list)
    while todo:
        module=todo.pop()
        if module in chosen or module in missing:continue
        p=overrides.get(module,preferred.get(module,defs.get(module,[None])[0]))
        if p is None:missing.add(module);continue
        raw,mods=allblocks[p];m=next((m for m in mods if m[1]==module),None)
        if m is None:raise ValueError('Preferred source does not define '+module)
        chosen[module]=p
        body=masked(raw[m.start():m.end()])
        for ref in INST.finditer(body):
            dep,inst=ref.groups()
            if dep not in KW and inst not in KW:
                todo.append(dep)
                references[dep].append(dict(parent=module,instance=inst,source=str(p),
                    line=raw.count('\n',0,m.start()+ref.start())+1))
    # Constructors in inactive generate branches intentionally have no definition.
    # Keep every guard byte intact and defer activity to real parameter elaboration.
    # ACTIVE unknown constructors still fail Verilator: no stub or warning waiver.
    unresolved=[dict(module=n,references=references[n])for n in sorted(missing)]
    files=list(dict.fromkeys(chosen.values()))
    copied,incs,missing_inc=portable_sources(files,out)
    if missing_inc:raise ValueError('Missing selected includes: '+str(missing_inc))
    checks=[];removed=[]
    for original,target in zip(files,copied):
        raw,mods=allblocks[original];parts=[];last=0;kept=[]
        for m in mods:
            parts.append(raw[last:m.start()]);body=raw[m.start():m.end()]
            if chosen.get(m[1])==original:
                parts.append(body);kept.append((m[1],body))
            else:
                if re.search(r'`(?:define|undef|include)\b',masked(body)):
                    raise ValueError('Cannot remove module-local preprocessor side effect: '+m[1])
                removed.append(dict(module=m[1],source=str(original)))
            last=m.end()
        parts.append(raw[last:]);target.write_text(''.join(parts))
        new,newmods=blocks(target);actual={m[1]:new[m.start():m.end()]for m in newmods}
        for name,body in kept:
            if actual.get(name)!=body:raise ValueError('Changed used module body: '+name)
            checks.append(dict(module=name,source=str(original),sha256=hashlib.sha256(body.encode()).hexdigest()))
    # Definitions are now unique. Directives/includes retain original text and closure.
    (out/'sim.f').write_text('\n'.join(directives+['-v '+str(p)for p in copied]+['+incdir+'+str(p)for p in incs])+'\n')
    receipt=dict(scope='Source selection only; real parameter elaboration required, no numeric G5',
        status='REQUIRES_PARAMETER_AWARE_ELABORATION',unresolved_constructors=unresolved,
        unknown_active_modules_are_errors=True,top=topname,lexically_referenced_modules=len(chosen),
        selected_files=len(copied),unchanged_module_bodies=checks,removed_unreachable_or_shadowed=removed,
        authoritative_prefer_files=len(ab.get('prefer',[])),models_override_only=list(model_names),
        native_required_ports_preserved=True,bind_verdict_preserved=True)
    (out/'module_closure.json').write_text(json.dumps(receipt,indent=1)+'\n')
    base=json.loads((out/'staging.json').read_text())
    (out/'staging_original.json').write_text(json.dumps(base,indent=1)+'\n')
    base.update(files=len(copied),top=str(top),parameter_elaboration_status=receipt['status'],
        unresolved_constructors=unresolved,module_closure='module_closure.json',
        blackboxes={str(p):[b[1]for b in blocks(p)[1]]for p in copied
            if re.search(r'\(\*\s*blackbox\b',masked(p.read_text()))or p.name.endswith('_bb.v')})
    (out/'staging.json').write_text(json.dumps(base,indent=1)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()if k not in ['unchanged_module_bodies','removed_unreachable_or_shadowed']}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for x in ['stage','manifest','repo','out']:p.add_argument('--'+x,type=Path,required=True)
    a=p.parse_args();prepare(a.stage.resolve(),a.manifest.resolve(),a.repo.resolve(),a.out.resolve())
