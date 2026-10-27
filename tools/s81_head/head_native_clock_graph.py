#!/usr/bin/env python3
"""Derive active HEAD clock source wiring from the actual placed bank topology.

This emits a SOURCE COPY with all unclassified hard-core FT pins still unbound.
It never invents inactive input ties, an all-ports waiver, or a physical PASS.
"""
import argparse,copy,hashlib,json,re,sys
from collections import defaultdict
from pathlib import Path
IDENT=re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')
MASTER='BUFx24_ASAP7_75t_R'

def topology(tree):
    banks=defaultdict(list)
    for name,site in tree['cell_sites'].items():
        if not IDENT.fullmatch(name) or site['master']!=MASTER:raise ValueError('unexpected actual clock cell')
        banks[int(site['group'])].append(name)
    parent={};children=defaultdict(list)
    for edge in tree['nets']:
        a,b=(int(edge[k][1:]) for k in ('drv','load'))
        if a not in banks or b not in banks or b in parent or a==b:raise ValueError('invalid/duplicate clock bank edge')
        parent[b]=a;children[a].append(b)
    roots=set(banks)-set(parent);leaves=sorted(set(banks)-set(children))
    if len(roots)!=1:raise ValueError('actual bank graph must have one root')
    root=next(iter(roots));seen=set();todo=[root]
    while todo:
        n=todo.pop()
        if n in seen:raise ValueError('clock bank cycle')
        seen.add(n);todo.extend(children[n])
    if seen!=set(banks):raise ValueError('disconnected clock bank graph')
    for n,cells in banks.items():
        kinds={tree['cell_sites'][c]['kind'] for c in cells}
        if (n in leaves)!=(kinds=={'mesh_driver'}):raise ValueError('leaf bank is not an actual mesh driver')
    if (len(banks),sum(map(len,banks.values())),len(leaves))!=(1418,3362,264):raise ValueError('current HEAD clock topology shape changed')
    return banks,parent,root,leaves

def provider(tree):
    banks,parent,root,leaves=topology(tree)
    ports=['input wire root_i']+['output wire leaf_g'+str(n) for n in leaves]
    text=['// Actual physical bank topology; zero-delay cell models are separate native views.',
          'module ot_s81hd_native_clock_tree ('+',\n'.join(ports)+');']
    text += ['wire g'+str(n)+';' for n in sorted(banks)]
    for n in sorted(banks):
        inp='root_i' if n==root else 'g'+str(parent[n])
        for cell in sorted(banks[n]):text.append(MASTER+' '+cell+' (.A('+inp+'), .Y(g'+str(n)+'));')
    text += ['assign leaf_g'+str(n)+' = g'+str(n)+';' for n in leaves]
    text.append('endmodule')
    return '\n'.join(text)+'\n',leaves

def clock_endpoints(raw):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
    import schema as S
    P=S.Plan(raw); rows=[]; grids={tn:S.tap_grid(P,tn) for tn in P.types}
    for part,p in P.parts.items():
        t=P.types[p['type']]
        for port,x,y in grids[p['type']]:
            rows.append(dict(part=part,type=p['type'],port=port,kind='published_grid_clock',type_xy_um=[x,y],die_xy_um=list(P.to_die(part,(x,y))),source='schema.tap_grid; same exports as gen_phys/clock_taps.tcl',physical_attachment_required=True))
        ip={v['name']:v for v in t.get('infra_ports',[])}
        for port,x,y,tap in S.core_taps(P,p['type']):
            inst=tap['name'].rsplit('.',1)[0];index=4 if 'g_cvb' in inst else int(inst[-1]);base=f'hci{index}_mesh'
            pins={f:ip[base+'_'+f] for f in ('i','o')}
            rows.append(dict(part=part,type=p['type'],port=port,kind='native_core_clock',type_xy_um=[x,y],die_xy_um=list(P.to_die(part,(x,y))),core_pin=tap['name'],
                mesh_input=dict(port=base+'_i',type_xy_um=pins['i']['xy_um'],die_xy_um=list(P.to_die(part,pins['i']['xy_um']))),
                mesh_output=dict(port=base+'_o',type_xy_um=pins['o']['xy_um'],die_xy_um=list(P.to_die(part,pins['o']['xy_um']))),
                insertion_tt_ps=tap['insertion_ps'],insertion_ff_ps=tap['insertion_ff_ps'],ft_buffer_arc_separate=True,physical_attachment_required=True))
    return rows

def compose(raw,tree,stubs,sources):
    out=copy.deepcopy(raw);parts={p['name']:p for p in out['partitions']};tiles=[p for p in out['partitions'] if p['type']=='hd_tile']
    if len(tiles)!=264:raise ValueError('actual264 HEAD tiles required')
    _,_,_,leaves=topology(tree)
    centre={(s['part'],s['inst']) for s in stubs if s['kind']=='core_centre_entry'}
    if len(centre)!=1320:raise ValueError('actual1320 native core-centre stubs required')
    nets=[dict(name='ck_mesh',kind='clock_mesh')];bindings=[];taps=[]
    for part in tiles:
        ty=out['partition_types'][part['type']];ct=[t for t in ty['clock']['taps'] if t.get('kind')=='core']
        if ty['clock'].get('core_taps')!='early' or len(ct)!=5:raise ValueError('five explicit functional clock entries required')
        for k,tap in enumerate(ct):
            inst,pin=tap['name'].rsplit('.',1)
            if pin!='ft_mstrap_i' or (part['name'],tap['name']) not in centre:raise ValueError('core clock entry lacks actual planned stub')
            index=4 if 'g_cvb' in inst else int(inst[-1]);port=f'hci{index}_mesh'
            n='core_mesh_'+part['name']+'_'+str(index)
            nets.append(dict(name=n,kind='clock'))
            bindings.extend([dict(part=part['name'],port=port+'_i',net='ck_mesh'),dict(part=part['name'],port=port+'_o',net=n)])
            taps.append(dict(part=part['name'],port='clk_c'+str(k),net=n))
    inst=dict(module='ot_s81hd_native_clock_tree',inst='u_native_clock_tree',bind={'root_i':dict(signal='root:clk',dir='in')})
    inst['bind'].update({'leaf_g'+str(n):dict(signal='ck_mesh',dir='out') for n in leaves})
    bound={(b['part'],b['port']) for b in bindings};missing=[]
    for part in tiles:
        for pin in out['partition_types'][part['type']].get('infra_ports',[]):
            if (part['name'],pin['name']) not in bound:missing.append(dict(part=part['name'],port=pin['name'],kind=pin['kind'],reason='actual-use classification and real local source missing'))
    out['infrastructure']=dict(nets=nets,instances=[inst],bindings=bindings,clock_tap_bindings=taps,sources=sources,
        simulation_substitutions={sources[1]:sources[2]},qualification='SOURCE COPY: unclassified FT pins remain unbound; physical geometry FAIL retained')
    # Functional sources must not enter the physical synthesis closure.
    out['infrastructure']['sources']=sources[:2]
    endpoints=clock_endpoints(out)
    # Every published soft root gets its own explicit endpoint/mesh connection.
    # The physical owner must attach each recorded anchor, not infer a stub.
    taps.extend(dict(part=e['part'],port=e['port'],net='ck_mesh') for e in endpoints if e['kind']=='published_grid_clock')
    out['clock_endpoint_requirements']=dict(status='SOURCE_ENDPOINTS_PHYSICAL_ATTACHMENT_PENDING',endpoints=endpoints)
    return out,dict(grid_clock_endpoints=sum(e['kind']=='published_grid_clock' for e in endpoints), schema='opentallas.head.active_clock_source.v1',status='BLOCKED_UNCLASSIFIED_FT_PINS',bank_groups=1418,buffer_cells=3362,leaf_driver_banks=264,core_mesh_pairs=1320,core_functional_entries=1320,unbound_ports=len(missing),missing=missing,added_data_cycles=0,physical_pass=False,whole_die_bind_pass=False,global_clk_alias=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','physical-tree','stubs','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=Path.cwd().resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    rel=str(out.relative_to(root));raw=json.loads(a.plan.read_text());tree=json.loads(a.physical_tree.read_text());stubs=json.loads(a.stubs.read_text())
    rtl,_=provider(tree);(out/'provider.sv').write_text(rtl)
    (out/'clock_cells_bb.v').write_text('(* blackbox *) module '+MASTER+'(input A,output Y); endmodule\n')
    (out/'clock_cells.v').write_text('// Functional truth table of the actual ASAP7 non-inverting clock buffer; no delay/STA model.\nmodule '+MASTER+'(input wire A,output wire Y); assign Y=A; endmodule\n')
    sources=[rel+'/'+n for n in ('provider.sv','clock_cells_bb.v','clock_cells.v')]
    plan,report=compose(raw,tree,stubs,sources)
    report['input_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.plan,a.physical_tree,a.stubs)}
    (out/'clock_endpoints.json').write_text(json.dumps(plan.pop('clock_endpoint_requirements'),indent=1)+'\n')
    (out/'plan_active_copy.json').write_text(json.dumps(plan,indent=1)+'\n');(out/'requirements.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='missing'},indent=1))
if __name__=='__main__':main()
