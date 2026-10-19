#!/usr/bin/env python3
"""Generic flattened-netlist fanout/depth inventory; no mapped timing claim."""
import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path


def expand_hierarchy(design, top):
    """Expand kept soft cells with exact elaborated port-bit aliases."""
    modules=design['modules'];ids={};cells={};nets={};parents={}
    def canonical(b):
        if b not in parents:return b
        parents[b]=canonical(parents[b]);return parents[b]
    def alias(a,b):
        a,b=canonical(a),canonical(b)
        if a==b:return
        if isinstance(a,str) and isinstance(b,str):raise ValueError('conflicting constant output aliases')
        if isinstance(a,str):parents[b]=a
        else:parents[a]=b
    def bit(b,path,mapping):
        if isinstance(b,str):return b
        if b in mapping:return mapping[b]
        k=(path,b)
        if k not in ids:ids[k]=len(ids)+2
        return ids[k]
    def walk(name,path,mapping,stack):
        if name in stack:raise ValueError('recursive hierarchy '+name)
        m=modules[name]
        for n,v in m['netnames'].items():
            nets[(path+'.' if path else '')+n]=dict(v,bits=[bit(b,path,mapping) for b in v['bits']])
        for n,c in m['cells'].items():
            full=(path+'.' if path else '')+n
            con={p:[bit(b,path,mapping) for b in bs] for p,bs in c['connections'].items()}
            child=modules.get(c['type'])
            if child and not int(child.get('attributes',{}).get('blackbox','0'),2):
                cm={};input_maps={}
                for p,v in child['ports'].items():
                    if v['direction']=='output' and not con.get(p):continue
                    if p not in con or len(con[p])!=len(v['bits']):raise ValueError('port width '+full+'.'+p)
                    for b,outer in zip(v['bits'],con[p]):
                        if isinstance(b,str):
                            if v['direction']!='output' and outer!=b:raise ValueError('constant input alias '+full+'.'+p)
                            alias(outer,b);continue
                        if v['direction']=='input':
                            if b in input_maps and canonical(input_maps[b])!=canonical(outer):raise ValueError('port alias conflict '+full+'.'+p)
                            input_maps[b]=outer
                        if b in cm and canonical(cm[b])!=canonical(outer):
                            alias(cm[b],outer)
                        cm[b]=outer
                walk(c['type'],full,cm,stack+[name])
            else:cells[full]=dict(c,connections=con)
    walk(top,'',{},[])
    ports={p:dict(v,bits=[bit(b,'',{}) for b in v['bits']]) for p,v in modules[top]['ports'].items()}
    for c in cells.values():c['connections']={p:[canonical(b) for b in bs] for p,bs in c['connections'].items()}
    for n in nets.values():n['bits']=[canonical(b) for b in n['bits']]
    for p in ports.values():p['bits']=[canonical(b) for b in p['bits']]
    return dict(design,modules=dict(modules,**{top:dict(modules[top],cells=cells,netnames=nets,ports=ports)}))


def inventory(design, top):
    design=expand_hierarchy(design,top)
    m=design['modules'][top]
    aliases=defaultdict(list);loads=Counter();drivers={};regbits=set()
    depth={};comb=[];endpoints=[];issues=[]
    for name,net in m['netnames'].items():
        for i,b in enumerate(net['bits']):
            if isinstance(b,int):aliases[b].append(name+(f'[{i}]' if len(net['bits'])>1 else ''))
    def brief(b):
        return sorted(aliases[b],key=lambda s:(s.startswith('$'),len(s),s))[:5]
    for p in m['ports'].values():
        if p['direction']=='input':
            for b in p['bits']:depth[b]=0
    for name,c in m['cells'].items():
        con=c['connections'];dirs=c.get('port_directions',{})
        if set(con)!=set(dirs):raise ValueError('missing port directions: '+name)
        ins=[b for p,bs in con.items() if dirs[p]=='input' for b in bs]
        outs=[b for p,bs in con.items() if dirs[p]=='output' for b in bs]
        loads.update(b for b in ins if isinstance(b,int))
        for b in outs:
            if not isinstance(b,int):continue
            if b in drivers and drivers[b]['cell']!=name:issues.append('multiple drivers '+str(brief(b)))
            drivers[b]=dict(cell=name,type=c['type'])
        sequential=c['type'].startswith(('$_DFF','$_SDFF'))
        module=design['modules'].get(c['type'],{})
        blackbox=int(module.get('attributes',{}).get('blackbox','0'),2)
        if sequential or blackbox:
            for b in outs:
                depth[b]=0
                if sequential:regbits.add(b)
            for p,bs in con.items():
                if dirs[p]=='input' and p not in ('C','clk','ck','CLK'):
                    endpoints.extend((name,p,b) for b in bs)
        else:comb.append((name,ins,outs))
    readers=defaultdict(list);remaining=[]
    for i,(_,ins,_) in enumerate(comb):
        need={b for b in ins if isinstance(b,int) and b not in depth};remaining.append(need)
        for b in need:readers[b].append(i)
    q=deque(i for i,need in enumerate(remaining) if not need);seen=set();ordered=[]
    while q:
        i=q.popleft()
        if i in seen:continue
        seen.add(i);ordered.append(i);_,ins,outs=comb[i]
        level=1+max((depth.get(b,0) for b in ins),default=0)
        for b in outs:
            if not isinstance(b,int):continue
            depth[b]=level
            for j in readers[b]:
                remaining[j].discard(b)
                if not remaining[j]:q.append(j)
    if len(seen)!=len(comb):issues.append(f'{len(comb)-len(seen)} unresolved combinational cells (cycle/unknown input/hierarchy)')
    rows=[dict(bit=b,loads=n,names=brief(b),driver=drivers.get(b),register_output=b in regbits)
          for b,n in loads.most_common() if n>32]
    stages=sorted([dict(cell=n,pin=p,bit=b,generic_levels=depth.get(b),names=brief(b))
                   for n,p,b in endpoints if isinstance(b,int)],
                  key=lambda r:-(r['generic_levels'] if r['generic_levels'] is not None else -1))
    # Count real terminal pin bits through all combinational logic. Buffers and
    # aliases cannot hide the ultimate loads. Top outputs are explicit stops;
    # their actual parent consumers still require the composed audit.
    reach=defaultdict(int);terminal_id=0
    for _,_,b in endpoints:
        if isinstance(b,int):
            reach[b] |= 1 << terminal_id;terminal_id+=1
    for p,v in m['ports'].items():
        if v['direction']=='output':
            for b in v['bits']:
                if isinstance(b,int):
                    reach[b] |= 1 << terminal_id;terminal_id+=1
    for i in reversed(ordered):
        _,ins,outs=comb[i];value=0
        for b in outs:value |= reach[b]
        for b in ins:
            if isinstance(b,int):reach[b] |= value
    ultimate_regs=sorted([dict(bit=b,names=brief(b),terminal_pins=reach[b].bit_count(),
        groups_if_partitioning_terminal_influence_at32=(reach[b].bit_count()+31)//32) for b in regbits if reach[b].bit_count()>32],
        key=lambda r:-r['terminal_pins'])
    ultimate_inputs=[]
    for p,v in m['ports'].items():
        if v['direction']=='input' and p not in ('ck','clk','CLK'):
            for i,b in enumerate(v['bits']):
                n=reach[b].bit_count()
                if n>32:ultimate_inputs.append(dict(port=p,bit=i,terminal_pins=n,groups_if_partitioning_terminal_influence_at32=(n+31)//32))
    ultimate_inputs.sort(key=lambda r:-r['terminal_pins'])
    return dict(status='GENERIC_DIAGNOSTIC_NOT_MAPPED_TIMING_OR_FANOUT_QUALIFICATION',
        top=top,cells=len(m['cells']),issues=issues,
        register_outputs_over32=[r for r in rows if r['register_output']],
        driven_nets_over32_count=sum(bool(r['driver']) for r in rows),
        highest_fanout_nets=rows[:40],highest_generic_stage_depth=stages[:30],
        all_comb_terminal_influence_registers_over32=ultimate_regs,
        all_comb_terminal_influence_inputs_over32=ultimate_inputs,
        bit_namespace='Diagnostic flattened alias IDs; locate raw elaborated bits using names/source hash.',
        terminal_influence_scope='Conservative logical influence through ALL combinational gates to sequential/native input pin bits plus each top output bit as one boundary stop. This exceeds buffer-transparent electrical fanout and is not the native rule verdict or a mandatory replica count; early registered decodes can partition it. Parent consumers beyond outputs remain unproven.',
        scope='Generic synthesis before ABC/physical buffers. Primitive levels are not TT ps; native macro clk-to-Q/setup, mapped logic, placement/route and retained replicas require separate proof. Clock/reset boundary loads retained and labeled, not counted as data-fanout failures.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('netlist');ap.add_argument('--top',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    raw=Path(a.netlist).read_bytes();d=inventory(json.loads(raw),a.top)
    d['netlist_sha256']=hashlib.sha256(raw).hexdigest()
    Path(a.out).write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps({k:d[k] for k in ('top','cells','issues','register_outputs_over32','driven_nets_over32_count','highest_generic_stage_depth')},indent=2)[:4000])


if __name__=='__main__':main()
