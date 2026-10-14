"""Re-port the per-mac containers by face (die lead 10-14): mac0 | ctl | mac1.
Port names: w_i/w_o (W face), e_i/e_o (E face), s_i/s_o (die face of the element, toward the banks / return), plus
clock_0.  The ctl's 566-b broadcast to both macs leaves on w_o AND e_o (one driver net, two output ports).
Writes containers.json (yosys json, every module of the partition, the three containers re-ported) + faces.json."""
import json,collections,copy
d=json.load(open('part/partitioned.json')); M=d['modules']
TOPN='ot_v41_rom_elem_q_qxpq_w10'; top=M[TOPN]
inst={'u_ctl':'ot_s81_q_ctl_native_graph','u_mac0':'ot_s81_q_mac0_native_graph','u_mac1':'ot_s81_q_mac1_native_graph'}
cname={c['type']:n for n,c in top['cells'].items()}
drv={}; loads=collections.defaultdict(set)
for n,c in top['cells'].items():
    for p,bits in c['connections'].items():
        for i,b in enumerate(bits):
            if isinstance(b,int):
                (drv.__setitem__(b,n) if c['port_directions'][p]=='output' else loads[b].add(n))
for p,v in top['ports'].items():
    for b in v['bits']:
        if isinstance(b,int): (drv.__setitem__(b,'TOP') if v['direction']=='input' else loads[b].add('TOP'))
side={'u_mac0':'W','u_mac1':'E'}
faces={}; NETS={}
for n,mod in inst.items():
    m=M[mod]; c=top['cells'][n]
    newp=collections.OrderedDict(); newp['clock_0']=m['ports']['clock_0']
    groups=collections.defaultdict(list); gnets=collections.defaultdict(list)
    for i,b in enumerate(c['connections']['in_bus']):
        src=drv.get(b,'TOP')
        f={'u_mac0':'w','u_mac1':'e','u_ctl':('e' if n=='u_mac0' else 'w')}.get(src,'s') if src!='TOP' else 's'
        if n!='u_ctl' and src=='u_ctl': f='e' if n=='u_mac0' else 'w'
        groups[f+'_i'].append(m['ports']['in_bus']['bits'][i]); gnets[f+'_i'].append(b)
    for i,b in enumerate(c['connections']['out_bus']):
        ls=loads.get(b,set())
        mb=m['ports']['out_bus']['bits'][i]
        fs=[]
        if n=='u_ctl':
            if 'u_mac0' in ls: fs.append('w_o')
            if 'u_mac1' in ls: fs.append('e_o')
            if 'TOP' in ls or not fs: fs.append('s_o')
        else:
            if 'u_ctl' in ls: fs.append(('e' if n=='u_mac0' else 'w')+'_o')
            if 'TOP' in ls or not fs: fs.append('s_o')
        for f in fs: groups[f].append(mb); gnets[f].append(b)
    for g in sorted(groups):
        newp[g]=dict(direction='input' if g.endswith('_i') else 'output',bits=groups[g])
    m['ports']=newp
    faces[mod]={g:len(v['bits']) for g,v in newp.items()}
    NETS[mod]=dict(gnets)
# the top keeps its cells but its connections no longer match: write only the containers
out=dict(creator=d.get('creator',''),modules={k:v for k,v in M.items() if k!=TOPN})
json.dump(out,open('containers.json','w'))
json.dump(faces,open('faces.json','w'),indent=1)
json.dump(NETS,open('port_nets.json','w'))
print(json.dumps(faces))
