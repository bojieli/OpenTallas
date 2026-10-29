#!/usr/bin/env python3
"""Check assembled native leaf connections against the exact source-branch headers."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
import gen_rtl as G


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('assembly');a.add_argument('--repo',required=True);a.add_argument('--out',required=True);a=a.parse_args();root=Path(a.assembly);plan=json.load(open(root/'source_plan.json'));cache={};errors=[];checked=[]
    sha=subprocess.check_output(['git','-C',a.repo,'rev-parse','HEAD'],text=True).strip()
    for tn,t in sorted(plan['partition_types'].items()):
        if t.get('hard'):continue
        chunks=[]
        for src in t.get('sources',[]):
            if src not in cache:
                r=subprocess.run(['git','-C',a.repo,'show','HEAD:'+src],capture_output=True,text=True)
                if r.returncode:errors.append(dict(type=tn,source=src,error='source path absent from selected commit'));cache[src]=''
                else:cache[src]=r.stdout
            chunks.append(cache[src])
        headers='\n'.join(chunks);text=(root/(t['module']+'.sv')).read_text()
        for c in t.get('contents',[]):
            module=c['module'];inst=c['inst'];ports=G.parse_leaf_ports(headers,module)
            if ports is None:errors.append(dict(type=tn,module=module,inst=inst,error='module absent from exact listed sources'));continue
            pattern=r'\b'+re.escape(module)+r'(?:\s*#\s*\(.*?\))?\s+'+re.escape(inst)+r'\s*\((.*?)\n    \);'
            matches=list(re.finditer(pattern,text,re.S))
            if len(matches)!=1:errors.append(dict(type=tn,module=module,inst=inst,error='not one emitted native instance'));continue
            bound=re.findall(r'\.([A-Za-z_]\w*)\s*\(',matches[0][1]);names=set(bound)
            missing=sorted(set(ports)-names);extra=sorted(names-set(ports));duplicate=sorted({n for n in bound if bound.count(n)>1})
            checked.append(dict(type=tn,module=module,instance=inst,ports=len(ports)))
            if missing or extra or duplicate:errors.append(dict(type=tn,module=module,inst=inst,missing=missing,extra=extra,duplicate=duplicate))
    report=dict(verdict='FAIL' if errors else 'PASS',source_commit=sha,checked_instances=len(checked),checked=checked,errors=errors,
        source_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in cache.items()},scope='native listed-source leaf headers vs emitted instance names/ports; width/formal equivalence not claimed')
    Path(a.out).write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('checked','source_sha256')}));return bool(errors)
if __name__=='__main__':raise SystemExit(main())
