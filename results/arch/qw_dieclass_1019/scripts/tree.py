import json,sys,collections
C=sys.argv[1]
s=json.load(open(C+'/spec_rA.json')); t=s['trees']; print(type(t), len(t))
items=t if isinstance(t,list) else [dict(name=k,**v) if isinstance(v,dict) else {'name':k,'v':v} for k,v in t.items()]
print(json.dumps(items[0])[:900])
want=sys.argv[2:]
for it in items:
    nm=json.dumps(it)
    for w in want:
        if f'pll_{w}[' in nm or it.get('name')==w or it.get('family')==w:
            sinks=it.get('sinks') or it.get('pins') or []
            print(w, {k:(v if not isinstance(v,list) else (len(v), v[:6])) for k,v in it.items()})
