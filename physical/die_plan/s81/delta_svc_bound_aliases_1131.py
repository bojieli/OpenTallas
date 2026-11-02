#!/usr/bin/env python3
"""Declare SVC kit-only physical identities from the canonical bound name map.
No source/core geometry, public pins, clock schedule or cycles are changed.
"""
import argparse,copy,json,re,sys
from pathlib import Path

def one(values,what):
    assert len(values)==1,(what,len(values),[str(v)[:160] for v in values[:3]])
    return values[0]

def instance_type(body,name):
    pattern=r'(?m)^\s*(\w+)\s*(?:#\([^;]*?\)\s*)?'+re.escape(name)+r'\s*\('
    return one(re.findall(pattern,body),"literal instance "+name)

def prepare(raw,bind,source,spec):
    sys.path.insert(0,str(source/'tools/die_plan'))
    import bind_elab as E
    names=json.load(open(bind/'bind_names.json'));report=json.load(open(bind/'bind_report.json'))
    mapping=json.load(open(spec['map_file']));dissolved=set(spec['dissolve'])
    pref=[source/str(p) for p in spec['prefer']]
    bodies={};lef_masters={}
    def body(mod):
        if mod not in bodies:
            candidates=[(str(p),E.module_body(p,mod)) for p in pref if p.is_file()]
            bodies[mod]=one([v for _,v in candidates if v],"preferred module "+mod)
        return bodies[mod]
    netlist_names={Path(n).name for n in spec['netlist']}
    tops=[p for p in (bind/'structural_tops').glob('*') if p.is_file() and any(p.name.endswith('_'+n) or p.name==n for n in netlist_names)]
    top=one([E.module_body(p,spec['top']) for p in tops if E.module_body(p,spec['top'])],"canonical structural top from netlist manifest")
    sx=body('dsdv_svc_sx')
    assert re.search(r'for\s*\(r\s*=\s*0;\s*r\s*<\s*4;.*?begin\s*:\s*g_r',sx,re.S)
    assert re.search(r'for\s*\(b\s*=\s*0;\s*b\s*<\s*2;.*?begin\s*:\s*g_h',sx,re.S)
    assert re.search(r'\bdsdv_svc_sx_hrow\b[^;]*\bu_hrow\s*\(',sx,re.S)
    result=dict(raw);result['partition_types']=dict(raw['partition_types']);rows=[]
    parts={}
    for p in raw['partitions']:parts.setdefault(p['type'],[]).append(p['name'])
    targets=[]
    for tn,t in raw['partition_types'].items():
        cores=t.get('hard_cores',[])
        if any(c['module']=='ot_s81c_attn_hcore' and c['inst'].startswith('u_rsv.') for c in cores):
            assert len(cores)==72 and sum(c['module']=='ot_s81c_attn_hcore' for c in cores)==64
            assert sum(c['module']=='dsdv_svc_sx_hrow' for c in cores)==8
            targets.append(tn)
    assert targets,'no SVC class found'
    for tn in targets:
        old=raw['partition_types'][tn];bmod=report['types'][tn]['module']
        text=(bind/'rtl'/f'{bmod}.sv').read_text()
        pattern=r'(?m)^\s*// as-built ([^\n]+)\n\s*(\w+)(?:\s*#\([^;]*?\))?\s+(\w+)\s*\('
        actual={inst:(src.strip(),mod) for src,mod,inst in re.findall(pattern,text)}
        candidates=[]
        for part in parts[tn]:
            roots=[k for k,v in mapping['parts'].items() if v==part and re.fullmatch(r'u_rsv_\d+',k)]
            for root in roots:
                module=instance_type(top,root);prefix=root;chain=[]
                while module!='dsdv_svc_rs_c':
                    assert module in dissolved,(tn,root,module,'not manifest-dissolved')
                    child=instance_type(body(module),'u');chain.append((module,'u',child));prefix+='.u';module=child
                    assert len(chain)<=3,(tn,chain)
                assert module in dissolved
                scope={v:k[len(part)+1:] for k,v in names.items() if k.startswith(part+'.')}
                resolved=[]
                for core in old['hard_cores']:
                    assert core['inst'].startswith('u_rsv.')
                    rest=core['inst'][len('u_rsv.'):];full=prefix+'.'+rest
                    if core['module']=='ot_s81c_attn_hcore':
                        flat=scope.get(full)
                        if flat not in actual or actual[flat]!=(full,core['module']):break
                        physical='u_bound.'+flat
                    else:
                        m=re.fullmatch(r'u_sx\.(g_r\[[0-3]\]\.g_h\[[01]\]\.u_hrow)',rest);assert m,(tn,rest)
                        parent=prefix+'.u_sx';flat=scope.get(parent)
                        if flat not in actual or actual[flat]!=(parent,'dsdv_svc_sx'):break
                        physical='u_bound.'+flat+'.'+m.group(1)
                    lef=source/core['lef']
                    if str(lef) not in lef_masters:lef_masters[str(lef)]=re.findall(r'^MACRO\s+(\S+)',lef.read_text(),re.M)
                    masters=lef_masters[str(lef)]
                    assert masters==[core['module']],(tn,core['inst'],masters)
                    resolved.append(dict(inst=core['inst'],physical_inst=physical,physical_master=core['module'],source=full))
                if len(resolved)==72:candidates.append((part,chain,resolved))
        part,chain,resolved=one(candidates,'canonical bound reference '+tn)
        t=copy.deepcopy(old);result['partition_types'][tn]=t
        for core,r in zip(t['hard_cores'],resolved):
            assert core['inst']==r['inst'];core['physical_inst']=r['physical_inst'];core['physical_master']=r['physical_master']
        check=copy.deepcopy(t)
        for c in check['hard_cores']:c.pop('physical_inst',None);c.pop('physical_master',None)
        assert check==old,(tn,'non-identity changes')
        assert len({r['physical_inst'] for r in resolved})==72
        rows.append(dict(type=tn,part=part,wrapper_chain=chain,cores=resolved))
    assert all(result[k] is raw[k] for k in raw if k!='partition_types')
    return result,dict(status='PREPARED: actual kit clock wiring and GEN still required',types=len(rows),cores=sum(len(r['cores']) for r in rows),geometry_or_public_pin_or_schedule_changes=0,rows=rows)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan',type=Path);p.add_argument('--bind',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--asbuilt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    raw=json.load(open(a.plan));new,report=prepare(raw,a.bind,a.source,json.load(open(a.asbuilt)))
    sys.path.insert(0,str(Path(__file__).resolve().parent));import compact_plan as CP
    a.out.write_text(CP.dumps(new));a.report.write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
