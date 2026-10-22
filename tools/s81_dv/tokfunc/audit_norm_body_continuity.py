#!/usr/bin/env python3
"""Compare existing producer's conservative module cones to selected PB bodies.

All parameter branches are included. Equality over that superset proves the
configured active subset without inferring optimization from module names.
No compile, simulation, body replacement, or numerical replay is performed.
"""
import argparse
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['lane','shipping-root','kit','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();sys.path.insert(0,str(a.shipping_root/'src/tools'))
    import die_port_bind as D
    kit=json.loads((a.kit/'kit.json').read_text());assert not kit['problems']
    def modules(paths,defines):
        result={}
        for path,rel,h in paths:
            assert sha(path)==h
            text=D.preprocess(D.strip_comments(path.read_text()),dict(defines))
            for m in re.finditer(r'\bmodule\s+(\w+)\b.*?\bendmodule\b',text,re.S):
                name=m[1];full=re.sub(r'\s+',' ',m[0]).strip()
                # Full preprocessed definition includes ports/default params
                # and procedural expressions, not only a declaration census.
                item=dict(source=rel,file_sha256=h,preprocessed_full_module_sha256=digest(full),text=m[0])
                if name in result:
                    assert result[name]['preprocessed_full_module_sha256']==item['preprocessed_full_module_sha256'],('differing compile definitions',name)
                else:result[name]=item
        return result
    selected=modules([(a.kit/'src'/f['path'],f['path'],f['sha256']) for f in kit['files']],{d:'' for d in kit['defines']})
    cases={}
    for directory,top in [('norm_leaf_partials_r1','tb_norm_leaf_source'),('norm_xfin_r1','tb_norm_xfin_source')]:
        run=a.lane/directory;rec=json.loads((run/'receipt.json').read_text());vf=run/'obj'/('V'+top+'__verFiles.dat')
        argv=shlex.split(next(l[3:-1] for l in vf.read_text().splitlines() if l.startswith('C "')))
        assert not any(x.startswith(('-D','+define+','-f')) for x in argv if x!='-fno-dfg')
        inputs=[];bench=None
        for arg in argv:
            if not arg.endswith(('.v','.sv')):continue
            path=Path(arg)
            if path.name==top+'.sv':bench=(path,str(path),rec['bench_sha256']);continue
            hits=[rel for rel in rec['source_sha256'] if str(path).endswith('/'+rel)];assert len(hits)==1
            rel,=hits;inputs.append((path,rel,rec['source_sha256'][rel]))
        assert len(inputs)==42 and bench
        original=modules(inputs+[bench],{})
        known=set(original)|set(selected)
        def kids(text):
            return {m[1] for m in re.finditer(r'\b([A-Za-z_]\w*)\s*(?=(?:`\w+\s*)?(?:#\s*\(|[A-Za-z_\\][\w\\]*\s*(?:\[[^\]]*\]\s*)?\())',text) if m[1] in known}
        reachable=set();todo=[top];edges={}
        while todo:
            name=todo.pop()
            if name in reachable:continue
            reachable.add(name);assert name in original,('original body missing',name)
            edges[name]=sorted(kids(original[name]['text'])-{name})
            todo+=edges[name]
        comparisons={};faults=[]
        for name in sorted(reachable-{top}):
            old=original[name];new=selected.get(name)
            equal=bool(new and old['preprocessed_full_module_sha256']==new['preprocessed_full_module_sha256'])
            comparisons[name]=dict(original={k:v for k,v in old.items() if k!='text'},
                selected={k:v for k,v in new.items() if k!='text'} if new else None,equal=equal)
            if not equal:faults.append(name)
        changed_unreachable={}
        for name in sorted((set(original)&set(selected))-reachable):
            old,new=original[name],selected[name]
            if old['preprocessed_full_module_sha256']!=new['preprocessed_full_module_sha256']:
                changed_unreachable[name]=dict(original={k:v for k,v in old.items() if k!='text'},selected={k:v for k,v in new.items() if k!='text'},
                    incoming_edges_from_conservative_cone=[n for n,cs in edges.items() if name in cs])
        cases[directory]=dict(receipt_sha256=sha(run/'receipt.json'),compiler_record_sha256=sha(vf),
            bench_sha256=bench[2],original_defines=[],selected_defines=kit['defines'],
            conservative_all_parameter_branch_module_edges=edges,body_comparisons=comparisons,
            differing_or_missing_reachable_bodies=faults,changed_unreachable_bodies=changed_unreachable,
            parameter_binding='full unchanged bench/receipt pins VP native payloads, VN G8/D64/N8/LM5/LA6, VQ AQ_XMEM2; XFIN NS16/NVL5/LM5/LA6. Comparison covers every parameter branch, defaults and overrides are not altered.')
    faults={n:c['differing_or_missing_reachable_bodies'] for n,c in cases.items() if c['differing_or_missing_reachable_bodies']}
    out=dict(schema='opentallas.s81.norm_selected_body_continuity.v1',status='CONSERVATIVE_FULL_BODY_CONTINUITY_PASS' if not faults else 'REACHABLE_BODY_CONTINUITY_GAP',
        selected_kit_sha256=sha(a.kit/'kit.json'),executed_bind_index=kit['executed_bind_index'],cases=cases,
        changed_master_bodies=False,new_compile=False,new_simulator_run=False,
        qualification='component module-body continuity only; actual shipping wrapper clocks/reset/transport/global epoch and whole programme remain UNVERIFIED')
    a.out.write_text(json.dumps(out,indent=1)+'\n');print(out['status'],faults)


if __name__=='__main__':main()
