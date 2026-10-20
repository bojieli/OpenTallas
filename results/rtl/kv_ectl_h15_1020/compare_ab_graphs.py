"""ROOT-approved strict complete source graph comparison; no proof admission."""
from pathlib import Path
import hashlib,json,sys

def canonical(js,top,hxk):
    js=json.loads(json.dumps(js))
    topmod=js['modules'][top]
    actual=topmod.get('parameter_default_values',{}).get('HXK')
    if actual is None or int(actual,2)!=hxk:raise ValueError('wrong elaborated HXK profile')
    del topmod['parameter_default_values']['HXK']
    for modname,mod in js['modules'].items():
        refs={}
        def add(bits,label):
            for i,b in enumerate(bits):
                if isinstance(b,int):refs.setdefault(b,[]).append([*label,i])
        for n,x in mod.get('netnames',{}).items():add(x['bits'],['wire',n])
        for n,x in mod.get('ports',{}).items():add(x['bits'],['port',n])
        for cell,x in mod.get('cells',{}).items():
            for pin,bits in x.get('connections',{}).items():add(bits,['cell',cell,pin])
        labels={b:json.dumps(sorted(v),separators=(',',':')) for b,v in refs.items()}
        def mapped(bits):return [{'net_alpha':labels[b]} if isinstance(b,int) else b for b in bits]
        for x in mod.get('netnames',{}).values():x['bits']=mapped(x['bits'])
        for x in mod.get('ports',{}).values():x['bits']=mapped(x['bits'])
        for x in mod.get('cells',{}).values():
            for pin,bits in x.get('connections',{}).items():x['connections'][pin]=mapped(bits)
    return js

def diff(a,b,path='',rows=None):
    if rows is None:rows=[]
    if len(rows)>=40:return rows
    if type(a)!=type(b):rows.append(dict(path=path,left_type=type(a).__name__,right_type=type(b).__name__));return rows
    if isinstance(a,dict):
        for k in sorted(set(a)|set(b)):
            if k not in a or k not in b:rows.append(dict(path=path+'/'+k,missing='left' if k not in a else 'right'))
            else:diff(a[k],b[k],path+'/'+k,rows)
            if len(rows)>=40:break
    elif isinstance(a,list):
        if len(a)!=len(b):rows.append(dict(path=path,lengths=[len(a),len(b)]))
        else:
            for i,(x,y) in enumerate(zip(a,b)):
                diff(x,y,path+'/'+str(i),rows)
                if len(rows)>=40:break
    elif a!=b:rows.append(dict(path=path,left=str(a)[:200],right=str(b)[:200]))
    return rows

def main():
    top=sys.argv[1];paths=list(map(Path,sys.argv[2:4]));out=Path(sys.argv[4]);js=[json.loads(p.read_text()) for p in paths]
    cs=[canonical(x,top,h) for x,h in zip(js,[13,15])]
    hashes=[hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest() for x in cs]
    macros=[]
    for name,m in js[0]['modules'].items():
        for inst,c in m.get('cells',{}).items():
            if 'sram' in c['type'].lower():macros.append(dict(module=name,instance=inst,master=c['type'],parameters=c['parameters'],connections=c['connections'],port_directions=c.get('port_directions')))
    r=dict(scope='COMPLETE_SOURCE_GRAPH_ONLY_REQUIRES_SAME_STATEFUL_MACRO_LEMMA_NO_COLD_PHYSICAL_ADMISSION',top=top,status='IDENTICAL' if cs[0]==cs[1] else 'FAIL_DIFFERENT_GRAPH',allowed_exclusions=['numeric net IDs alpha-renamed by ALL named-wire/port/cell-pin occurrences, preserving multiplicity','top HXK profile metadata13vs15 only; unusedness conditional on ALL remaining graph identical'],source_json_sha256=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],canonical_sha256=hashes,complete_macro_instances=macros,differences=diff(*cs))
    out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['top','status','canonical_sha256','differences']}))
    return 0 if cs[0]==cs[1] else 1
if __name__=='__main__':raise SystemExit(main())
