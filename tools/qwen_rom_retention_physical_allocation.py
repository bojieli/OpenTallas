#!/usr/bin/env python3
"""Source-identified85cell constructive successor. No map/P&R/decode invocation.
Old map supplies unchanged hardware; replaced32controlFFs never survive as
phantom clock/reset loads. D-expression/data equivalence remains source-gated.
"""
import copy
import collections
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
import qwen_rom_current_reset_construction as R
import qwen_rom_mapped_root_pg_context as M

ROOT=R.ROOT
OUT=Path('results/uarch/qwen_rom_retention_physical_allocation_20261002')
INV='INVx1_ASAP7_75t_R'


def construct(net,base):
    net=copy.deepcopy(net);g=copy.deepcopy(base);cells=g['added_primitive_cells'];coords=g['nominal_node_coordinates_um'];edits=g['original_cell_pin_edits'];edges=g['wire_edges']
    original=net['cells'];metadata=R.obj(R.OUT/'inputs/euclid-graph-survival-r3.json')['endpoint_checks']
    masknames=[n for n in net['netnames'] if re.fullmatch(r'u_tile\.u_logic\.g_pair\[[01]\]\.g_bank\[[0-4]\]\.g_cap\.g_direct\.g_mask\[[0-7]\]\.local_sel',n)]
    if len(masknames)!=80:raise ValueError('logical80mask naming mismatch')
    maskowners=metadata['mask']['FF_endpoints'];bankowners=metadata['bank_strobe']['FF_endpoints']
    removed=set(maskowners+bankowners)
    if len(removed)!=32:raise ValueError('different old source control owners')
    # Preserve5 early-select source-attributed FFs and all other actual source.
    early={name for name,c in original.items() if c['type'].startswith('DFF') and c.get('attributes',{}).get('src','').endswith('ot_qwen_rom_tile_context_candidate_r2.sv:180.13-182.64')}
    if len(early)!=5:raise ValueError('actual early select5 missing')
    for name in removed:del original[name];edits.pop(name,None)
    edges[:]=[e for e in edges if e['sink'] not in removed and not(e['sink'] in early and e['pin']=='CLK')]
    # Retire only analytical dead branches dedicated to replaced pins. Original
    #mapped buffers stay reserved. Do not leave phantom loads on reset leaves.
    while True:
        drivers={e['driver'] for e in edges}
        dead={n for n,c in cells.items() if c['type']==R.BUF and n not in drivers}
        if not dead:break
        edges[:]=[e for e in edges if e['sink'] not in dead]
        for n in dead:del cells[n]

    maxbit=max(b for row in cells.values() for bits in row['connections'].values() for b in bits if isinstance(b,int))
    def fresh():
        nonlocal maxbit
        maxbit+=1;return maxbit
    new_buffers=[];source_rows=[]
    def setpin(name,pin,bit):
        if name in cells:cells[name]['connections'][pin]=[bit]
        else:edits.setdefault(name,{})[pin]=[bit]
    def buf(name,source,pos):
        bit=fresh();cells[name]=dict(type=R.BUF,connections=dict(A=[source],Y=[bit]));coords[name]=pos;new_buffers.append(name);return bit
    def wire(driver,output,sink,pin):
        a,b=coords[driver],coords[sink];distance=max(16,abs(a[0]-b[0])+abs(a[1]-b[1]));parts=math.ceil(distance/128)
        previous=driver;signal=output
        for i in range(1,parts):
            name=f'retention_segment_{len(new_buffers)}';signal=buf(name,signal,[a[d]+(b[d]-a[d])*i/parts for d in (0,1)])
            edges.append(dict(driver=previous,sink=name,pin='A',length_um=distance/parts));previous=name
        setpin(sink,pin,signal);edges.append(dict(driver=previous,sink=sink,pin=pin,length_um=distance/parts))
    # Existing12source leaves indexed exactly as metadata_reset_n[sink/8].
    leaves={i:f'u_tile.u_logic.g_distribution.u_tree.g_reset_leaf[{i}].u_buf' for i in range(12)}
    if any(n not in original for n in leaves.values()):raise ValueError('actual reset leaf topology missing')
    def resetnet(index):return original[leaves[index//8]]['connections']['Y'][0]
    clk=net['ports']['clk_stream']['bits'][0]
    entries=[]
    for i,logical in enumerate(masknames):
        p,b,ch=map(int,re.fullmatch(r'u_tile\.u_logic\.g_pair\[([01])\]\.g_bank\[([0-4])\]\.g_cap\.g_direct\.g_mask\[([0-7])\]\.local_sel',logical).groups())
        macro=f'u_tile.g_col[{p}].g_bank[{b}].u_rom';origin=coords[macro]
        name=logical.rsplit('.',1)[0]+'.g_retained.u_mask_ff'
        entries.append(dict(instance=name,role='mask',source_expression='local_next',macro=macro,reset_index=10+16*b+8*p+ch,
                            position_um=[origin[0]-2.16,origin[1]+8.64+ch*.54],old_alias_owner=maskowners[i]))
    for b in range(5):
        macro=f'u_tile.g_col[0].g_bank[{b}].u_rom';origin=coords[macro]
        entries.append(dict(instance=f'u_tile.u_logic.g_bank_control.g_bank[{b}].g_retained.u_read_ff',role='bank_strobe',
            source_expression='wrom_re',macro=macro,reset_index=5+b,position_um=[origin[0]-2.16,origin[1]+6.48],old_alias_owner=bankowners[b]))
    for row in entries:
        name=row['instance'];qn=fresh()
        ff=dict(type=R.ASR,connections=dict(CLK=[clk],RESETN=[resetnet(row['reset_index'])],SETN=['1'],
            D=['SOURCE_EXPR:'+row['source_expression']],QN=[qn]),attributes=dict(source_scope='fdbe8a5a7 retained source; control-load allocation only'))
        original[name]=ff;coords[name]=row['position_um'];source_rows.append(row)
        # A concrete INV restores QN polarity;85logical inversions are never
        #assumed free or inferred to have survived a map that has not run.
        invname=name+'.restore_INV';y=fresh();cells[invname]=dict(type=INV,connections=dict(A=[qn],Y=[y]));coords[invname]=[coords[name][0]+1.08,coords[name][1]]
        row.update(restoring_INV=invname,QN_wire_length_um=2,restoring_INV_input_cap_fF={c:R.library(c)[2][(INV,'A')]['cap_fF']+.165790*2 for c in ('ss','ff')})
        if row['role']=='mask':
            #32golden data mask consumers plus one local hold-feedback input.
            #Fixed fanout7 leaves. Real NAND2 input capacitances price the
            #specified source mapping; post-map equivalent gates requalify it.
            rootname=name+'.selector_driver';out=buf(rootname,y,coords[invname])
            edges.append(dict(driver=invname,sink=rootname,pin='A',length_um=2))
            for leaf in range(5):
                leafname=rootname+'.leaf'+str(leaf);leafout=buf(leafname,out,coords[name])
                edges.append(dict(driver=rootname,sink=leafname,pin='A',length_um=16))
                for k in range(min(7,33-leaf*7)):
                    consumer=leafname+'.consumer'+str(k)
                    cells[consumer]=dict(type='NAND2xp33_ASAP7_75t_R',connections=dict(A=[leafout]),
                        analytical_load_proxy_only=True)
                    coords[consumer]=[coords[name][0]+.1*(k%3),coords[name][1]+.1*(k//3)]
                    edges.append(dict(driver=leafname,sink=consumer,pin='A',length_um=16))
            row['selector_consumers']=33;row['selector_distribution_buffers']=6
    # All90metadata clock sinks are newly allocated as one source qualified
    #tree. Early-select5retain their actualD/reset ownership, not old timing.
    controlnames=sorted(early)+[r['instance'] for r in entries]
    center=coords['context_provider'];targets=[(n,'CLK') for n in controlnames];level=0
    while True:
        parents=[]
        for i in range(0,len(targets),8):
            children=targets[i:i+8];pos=[sum(coords[n][d] for n,p in children)/len(children) for d in (0,1)]
            name=f'retention_clock_L{level}_{i//8}';out=buf(name,clk,pos)
            for n,p in children:
                local=name+'.branch'+str(len(new_buffers));bit=buf(local,out,pos)
                edges.append(dict(driver=name,sink=local,pin='A',length_um=16));wire(local,bit,n,p)
            parents.append((name,'A'))
        if len(parents)==1:root=parents[0][0];break
        targets=parents;level+=1
    # Match the selected6logical stages before geometry-dependent segments;
    #this is NOT balanced CTS. Explicit skew gate below remains mandatory.
    for pad in range(6-(level+1)):
        name='retention_clock_pad'+str(pad);out=buf(name,clk,coords[root]);wire(name,out,root,'A');root=name
    hub='bind_clock_hub';hubout=cells[hub]['connections']['Y'][0]
    branch='retention_clock_source';out=buf(branch,hubout,center)
    edges.append(dict(driver=hub,sink=branch,pin='A',length_um=16));wire(branch,out,root,'A')
    # Remove stale early select clock/reset routes; all other actual sinks
    #remain source matched, with full propagation rerun, never reused timing.
    edges[:]=[e for e in edges if not(e['sink'] in early and e['pin']=='CLK' and not e['driver'].startswith('retention_'))]
    #Attach all85explicitsource reset pins to their exact existing12leaves.
    for row in entries:
        owner=leaves[row['reset_index']//8];out=original[owner]['connections']['Y'][0]
        branch='retention_reset_branch'+str(len(new_buffers));bit=buf(branch,out,coords[owner])
        edges.append(dict(driver=owner,sink=branch,pin='A',length_um=16));wire(branch,bit,row['instance'],'RESETN')
    # Delete obsolete r1 paths into the32old FFs (already removed). Their
    #upstream cells remain conservatively area-reserved, not timing credited.
    g.update(added_primitive_cells=cells,original_cell_pin_edits=edits,wire_edges=edges,
        nominal_node_coordinates_um=coords,source_control_cells=source_rows,removed_old_control_FFs=sorted(removed),
        successor_distribution_buffers=new_buffers,semantic_data_graph_qualified=False,
        synthetic_proxy_gates_are_load_reservations_not_new_mapped_hardware=True)
    return net,g


def preflight(net,g):
    reports={};root=R.obj(M.OUT/'model-r1.json')['timing_preflight'];rawrst=net['ports']['reset_stream_n']['bits'][0]
    ff={n:c for n,c in net['cells'].items() if c['type'].startswith('DFF')}
    clocks=[(n,'CLK') for n in ff]+[(n,'clk') for n,c in net['cells'].items() if c['type'] in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2')]
    if len(clocks)!=102352 or sum(c['type']==R.ASR for c in ff.values())!=56683:raise ValueError('successor endpoint conservation failed')
    for corner in ('ss','ff'):
        ck,_,cload=M.propagate(g,net,corner,{'bind_clock_entry':{t:[0,0,5,80] for t in ('rise','fall')}})
        provider=ck['context_provider:clk_stream']['rise']
        release=root[corner]['release_relative_provider_clock_minmax_ps']
        cap=3*R.library(corner)[2][(R.BUF,'A')]['cap_fF']+R.obj(R.OUT/'inputs/launch_join_cells_r1.json')[corner]['pin_caps_fF']['C']+.165790*80
        slew=R.envelope(R.library(corner)[1][R.BUF],'rise_transition',cap)
        rr,_,rload=M.propagate(g,net,corner,{'context_provider':{t:[provider[0]+release[0],provider[1]+release[1],*slew] for t in ('rise','fall')}})
        phases=[]
        for name,c in ff.items():
            if c['type']!=R.ASR:continue
            a=ck[name+':CLK']['rise'];b=rr[name+':RESETN']['rise'];phase=[b[0]-a[1],b[1]-a[0]]
            phases.append(dict(instance=name,phase_minmax_ps=phase,removal_margin_ps=phase[0]-50.049297,recovery_margin_ps=791.5025333333334-phase[1]))
        intervals=[ck[n+':'+p]['rise'] for n,p in clocks];span=max(r[1] for r in intervals)-min(r[0] for r in intervals)
        pin_clock=sum(M.pin_cap(ff[n]['type'],'CLK',corner) for n in ff)+sum(M.pin_cap(net['cells'][n]['type'],p,corner) for n,p in clocks if n not in ff)
        pin_reset=sum(M.pin_cap(c['type'],'RESETN',corner) for c in ff.values() if c['type']==R.ASR)
        reports[corner]=dict(clock_pin_cap_fF=pin_clock,reset_pin_cap_fF=pin_reset,clock_sinks=len(clocks),reset_sinks=len(phases),clock_minmax_ps=[min(r[0] for r in intervals),max(r[1] for r in intervals)],
            clock_span_ps=span,clock_skew_target_ps=20,balanced_CTS=False,
            clock_skew_demand_failed=span>20,skew_closure_not_relaxed=True,
            removal_worst=min(phases,key=lambda r:r['removal_margin_ps']),recovery_worst=min(phases,key=lambda r:r['recovery_margin_ps']),
            reset_bound_failures=sum(r['removal_margin_ps']<0 or r['recovery_margin_ps']<0 for r in phases),
            max_BUF_load_fF=max([*cload.values(),*rload.values()]),
            source_ff_reset_bounds_recomputed=True,baseline_timing_transferred=False,
            nominal_unextracted_allocation=True,contextual_SSFF=False)
    return reports


def main():
    out=ROOT/OUT;out.mkdir(parents=True,exist_ok=True)
    if (out/'model-r1.json').exists():raise ValueError('refuse overwrite verdict')
    path=R.LIVE/'mapped.json'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=M.MAP_SHA:raise ValueError('different map')
    net=json.loads(path.read_text())['modules']['ot_qwen_rom_fulltile_tp4_context_top']
    base=json.loads(gzip.decompress((ROOT/M.OUT/'root-bound-allocation-r1.json.gz').read_bytes()))
    net,g=construct(net,base);report=preflight(net,g)
    payload=gzip.compress(R.canon(g),mtime=0);(out/'successor-allocation-r1.json.gz').write_bytes(payload)
    source=R.obj(M.OUT/'inputs/retained-source-model-handoff.json')
    # Source/control initialization is a stated admission contract, not a
    #silently strengthened golden. Stored-Zfailure remains binding history.
    contract=dict(domain='driven binary controls at accepted transactions',
        inputs='clock/reset/go/owned-ready are0or1; all accepted ib/address/control fields stable and0or1 through acceptance',
        initialization='All90metadataRESETN pins see >=330ps low pulse and valid recovery/removal before owned parent_ready permits first accepted launch',
        data_state='Unreset ROM capture data is ignored until source read/capture tags are valid; no uninitialized payload becomes a control producer',
        stored_Z='FAIL_RETAINED; no full four-state equivalence/adoption claim',
        verified_literal_scope='Euclid01X literal fragments PASS; source-reachable binary/init proof and full data graph still prerequisites')
    result=dict(schema='QWEN_RETAINED85_ACTUAL_SOURCE_PHYSICAL_ALLOCATION_V1',status='FAIL_NOMINAL_CLOCK_BALANCE_NOT_BUILD_ADMITTED',
        actual_parent_mapped_sha256=M.MAP_SHA,retained_source_commit='fdbe8a5a7',retained_source_sha256=source['source_sha256'],
        selected_corridor_um=96.768,complete_cell_ceiling_um2=125000,
        removed_actual_control_FFs=32,explicit_successor_control_FFs=85,new_FFs=53,early_select_FFs=5,total_metadata_FFs=90,
        restoring_INV_cells=85,mask_selector_distribution_buffers=480,
        successor_distribution_buffers=len(g['successor_distribution_buffers']),
        nominal_retention_cell_area_um2=53*.37908+85*.04374,
        nominal_added_distribution_cell_area_um2=len(g['successor_distribution_buffers'])*.10206,
        conservative_reserved_area_um2=R.obj(M.OUT/'model-r1.json')['nominal_area_with_retention_inverters_and_source_binding_um2']+len(g['successor_distribution_buffers'])*.10206,
        source_cells=g['source_control_cells'],timing_preflight=report,driven_binary_initialization_contract=contract,
        data_connections='Source-expression identifiers only for newFF.D. Allocation qualifies pin loads/locations; functional mapped data graph is not invented.',
        balanced_clock_required_before_build_admission=True,
        startup='Two producer synchronization edges only; complete distribution/startup acceptance barrier must be repriced after clock balancing. No edge3guarantee transferred.',
        numerical_or_map_runs=0,PnR=False,source_map_admission=False,hardware_adoption=False,
        allocation_sha256=hashlib.sha256(payload).hexdigest(),
        prerequisites=[
          'Owned binary/init contract proven against actual source producers; storedZFAIL preserved.',
          'All85named FFs survive with source-matched D/reset/polarity and all85restoring inversions accounted by actual mapped drivers.',
          'Construct and price balanced clock feed, including macro/capture pair skew and data setup/hold;20ps target and60/25uncertainties unchanged.',
          'Recompute reset/launch phases and startup barrier over102352clock/56683reset endpoints after balancing; no prior timing transfer.',
          'Complete ROM/KV/address/data semantic graph gate; partial ROM capture connectivity is not completePASS.',
          'Legal cell/pin/via placement and macro PG access; directional M5/M7/M6/M8 plan requires DRC/IR/EM and all-cut capacity proof.',
          'Full constructed cells, wires and PG fit125000um2selected ceiling and96.768umcorridor before contextual SS/FF/P&R.'])
    M.write(out/'model-r1.json',result)
    sources=[Path(__file__).relative_to(ROOT),Path('tests/test_qwen_rom_retention_physical_allocation.py'),Path('tools/qwen_rom_mapped_root_pg_context.py'),Path('tools/uarch_model_qwen_mapped_context.py'),R.PROVIDER,
        M.OUT/'model-r1.json',M.OUT/'root-bound-allocation-r1.json.gz',M.OUT/'inputs/retained-r3.sv',M.OUT/'inputs/retained-source-model-handoff.json',M.OUT/'inputs/reset-control-liberty.json',R.OUT/'mapped-sink-census-r1.json.gz',Path('tools/qwen_rom_current_reset_construction.py'),R.OUT/'sourcepins-r1.json',M.OUT/'sourcepins-r1.json']
    M.write(out/'sourcepins-r1.json',dict(sha256={str(p):M.digest(p) for p in sources}))
    M.write(out/'artifact-sha256-r1.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='artifact-sha256-r1.json'})
    print(json.dumps({k:result[k] for k in ('status','successor_distribution_buffers','conservative_reserved_area_um2','timing_preflight')},indent=2))

if __name__=='__main__':main()
