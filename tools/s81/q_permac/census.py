import json,hashlib
mods=json.load(open('mapped.json'))['modules']; top='ot_v41_rom_elem_q_qxpq_w10'
def census(t):
    area=0.;sinks=0;macro={}
    for c in mods[t].get('cells',{}).values():
        k=c['type'];m=mods.get(k,{})
        if m and not m.get('attributes',{}).get('blackbox'):
            a,s,mm=census(k);area+=a;sinks+=s
            for n,v in mm.items(): macro[n]=macro.get(n,0)+v
        elif k.startswith('ot_rom_'): macro[k]=macro.get(k,0)+1
        else:
            area+=float(m.get('attributes',{}).get('area',0)); sinks+=int(k.startswith('DFF'))
    return area,sinks,macro
rows=[]
for name,c in mods[top]['cells'].items():
    t=c['type']
    if t in mods and not mods[t].get('attributes',{}).get('blackbox'):
        a,s,mac=census(t)
        rows.append(dict(instance=name,module=t,mapped_std_area_um2=round(a,3),sinks=s,macros=mac,
                         ports={n:dict(direction=v['direction'],width=len(v['bits'])) for n,v in mods[t]['ports'].items()}))
print(json.dumps(dict(schema='opentallas.s81.q_permac_mapped.v1',source_graph_sha256=hashlib.sha256(open('source_graph.json','rb').read()).hexdigest(),
  partitioned_sha256=hashlib.sha256(open('part/partitioned.json','rb').read()).hexdigest(),groups=rows,total=census(top)),indent=1))
