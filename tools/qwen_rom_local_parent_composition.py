#!/usr/bin/env python3
"""Compose local source loads with actual launch, finite root input and field.
No RTL/map/P&R. Preserves every previous failed verdict.
"""
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
import qwen_rom_local_subtree_context as N
R=N.R;M=N.M;L=N.L;S=N.S
OUT=Path('results/uarch/qwen_rom_local_parent_composition_20261002')


def net_for(g,old):
    cells={r['instance']:dict(type=r['cell'],connections={}) for r in g['source_clock_sinks']}
    for n in old['legacy_reset_BUFFERS']:cells[n]=dict(type=R.BUF,connections={})
    for r in old['reset_combinational_controls']:cells[r['instance']]=dict(type=r['cell'],connections={})
    return dict(cells=cells)


def launch_and_root(g,net):
    p=R.price();result={};sink=g['launch_route']['actual_sink'];joins=R.obj(R.OUT/'inputs/launch_join_cells_r1.json')
    for corner in ('ss','ff'):
        _,lib,caps=R.library(corner);scenarios=[]
        joincap=caps[(R.BUF,'A')]['cap_fF']+2*N.C
        outcap=caps[(R.BUF,'A')]['cap_fF']+16*N.C
        seeds={}
        for t in ('rise','fall'):
            jd=R.envelope(joins[corner]['cell_definition'],'cell_'+t,joincap)
            js=R.envelope(joins[corner]['cell_definition'],t+'_transition',joincap)
            bd=R.envelope(lib[R.BUF],'cell_'+t,outcap,*js);bs=R.envelope(lib[R.BUF],t+'_transition',outcap,*js)
            # Charge both nonzero local wires inside the actual provider.
            rc=.0265684*(2*(2*N.C/2+caps[(R.BUF,'A')]['cap_fF'])+16*(16*N.C/2+caps[(R.BUF,'A')]['cap_fF']))/1000
            seeds[t]=[jd[0]+bd[0]+rc,jd[1]+bd[1]+rc,*bs]
        waves,_,loads=M.propagate(g,net,corner,{'retained_launch_segment0':seeds})
        ext,_,_=M.propagate(g,net,corner,{'bind_reset_entry':{t:[0,0,5,80] for t in ('rise','fall')}})
        reset=ext['context_provider:external_reset_n']
        for slew in (5,80):
            ck,_,clockloads=M.propagate(g,net,corner,{g['root_driver']:{t:[0,0,slew,slew] for t in ('rise','fall')}})
            producer=ck['context_provider:clk_stream']['rise'];capture=ck[sink+':CLK']['rise'];constraints={}
            for t in ('rise','fall'):
                w=waves[sink+':D'][t]
                setup=L.constraint(lib[R.ASR],'setup',t,w[2:],capture[2:])
                hold=L.constraint(lib[R.ASR],'hold',t,w[2:],capture[2:])
                lower=capture[1]-producer[0]+hold+25-w[0]
                upper=833.3333333333334+capture[0]-producer[1]-setup-60-w[1]
                constraints[t]=dict(delay_minmax_ps=w[:2],sink_slew_ps=w[2:],setup_constraint_ps=setup,hold_constraint_ps=hold,
                    required_go_and_owned_ready_after_provider_clock_ps=[lower,upper])
            pulse=330+max(reset['rise'][1]-reset['fall'][0],reset['fall'][1]-reset['rise'][0],0)
            vdd=float(re.search(r'nom_voltage\s*:\s*([\d.]+)',R.library(corner)[0])[1])
            scenarios.append(dict(clock_total_pin_plus_wire_load_fF=sum(clockloads.values()),clock_voltage_V=vdd,
                clock_dynamic_capacitance_power_W_lower_bound=sum(clockloads.values())*1e-15*vdd*vdd*1.2e9,
                primary_clock_slew_ps=slew,provider_clock_ps=producer,actual_capture_clock_ps=capture,
                launch=constraints,root_external_RESETN_deassert_after_primary_clock_ps=[100+producer[1]-reset['rise'][0],780+producer[0]-reset['rise'][1]],
                root_external_RESETN_low_pulse_min_ps=pulse,actual_parent_arrivals_observed=False))
        result[corner]=dict(scenarios=scenarios,max_launch_buffer_load_fF=max(loads.values()))
    intervals=[s['launch'][t]['required_go_and_owned_ready_after_provider_clock_ps'] for r in result.values() for s in r['scenarios'] for t in ('rise','fall')]
    common=[max(i[0] for i in intervals),min(i[1] for i in intervals)]
    return dict(corners=result,common_numeric_launch_pin_requirement_ps=common,
        proposed_source_contract_ps=[max(50,math.ceil(common[0])),math.floor(common[1])],
        source_contract_proven=False,external_paths_not_assumed_zero_delay=True,old_launch_window_transferred=False)


def field_model(tile):
    # Four congruent384tile panels, not a long1536tile strip. R90 is allowed
    #by both selected macro LEFs. Rotated route/PG accesses remain requalified.
    w,h=357.696,1360.8;a=32*w;b=12*h;outer=a+b;hole=b-a
    placements=[]
    for panel in range(4):
        for row in range(12):
            for col in range(32):
                x,y=col*w,row*h
                if panel==0:pos=[x,y];orient='R0'
                elif panel==1:pos=[a+y,x];orient='R90'
                elif panel==2:pos=[outer-x-w,outer-y-h];orient='R180'
                else:pos=[b-y-h,outer-x-w];orient='R270'
                placements.append(dict(tile=len(placements),panel=panel,origin_um=pos,orientation=orient))
    allowed={}
    for macro in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2'):
        text=R.read(Path('physical/asap7_memory_macros')/macro/(macro+'.lef'))
        allowed[macro]='R90' in text.split('SYMMETRY',1)[1].split(';',1)[0]
    if not all(allowed.values()):raise ValueError('selected macro does not permit rotation')
    # Finite field clock input spine: at most8branches per parent, isolating
    #and segmenting every real geometric route. This is a priced clock load,
    #not a transferred die-level skew/signoff claim.
    port_offsets=dict(R0=(178.848,393.12),R90=(h-393.12,178.848),R180=(w-178.848,h-393.12),R270=(393.12,w-178.848))
    centers=[tuple(p['origin_um'][d]+port_offsets[p['orientation']][d] for d in (0,1)) for p in placements]
    count=0;length=0;levels=[];targets=centers;field_edges=[]
    while len(targets)>1:
        parents=[];local_count=0
        # Preserve panel/row adjacency supplied by actual field placement.
        for i in range(0,len(targets),8):
            cs=targets[i:i+8];center=tuple(sum(p[d] for p in cs)/len(cs) for d in (0,1));parents.append(center)
            count+=1;local_count+=1
            for child in cs:
                distance=max(16,sum(abs(a-b) for a,b in zip(center,child)));segments=math.ceil(distance/128)
                count+=segments;local_count+=segments;length+=distance+16
                field_edges.append(dict(start_um=list(center),end_um=list(child),length_um=distance+16,segments=segments))
        levels.append(dict(parent_nodes=len(parents),paid_buffer_nodes=local_count));targets=parents
    # One final low-load16um clock branch at every tile input preserves80ps.
    count+=1536;length+=1536*16
    terminal_slew={c:R.envelope(R.library(c)[1][R.BUF],'rise_transition',R.library(c)[2][(R.BUF,'A')]['cap_fF']+16*N.C,5,320) for c in ('ss','ff')}
    input_distance=max(16,sum(abs(v-(outer/2 if d==0 else 0)) for d,v in enumerate(targets[0])))
    count+=math.ceil(input_distance/128);length+=input_distance
    field_cuts={str((axis,line)):sum(min(e['start_um'][axis],e['end_um'][axis])<line<=max(e['start_um'][axis],e['end_um'][axis]) for e in field_edges) for axis in (0,1) for line in (a,b,outer/2)}
    return dict(tiles=1536,panels=4,tiles_per_panel=384,panel_grid=[32,12],outer_square_um=outer,
        central_hole_um=hole,outer_envelope_area_mm2=outer**2/1e6,selected_tile_slot_area_mm2=1536*w*h/1e6,
        central_hole_area_mm2=hole**2/1e6,placements=placements,macro_R90_allowed=allowed,
        tile_cell_area_mm2=tile['complete_cell_area_um2']*1536/1e6,
        tile_macro_area_mm2=tile['tile_macro_area_um2']*1536/1e6,
        field_input_clock_buffers=count,field_input_clock_buffer_area_mm2=count*.10206/1e6,
        field_input_clock_wire_um=length,field_input_clock_geometric_cut_lower_bounds=field_cuts,field_spine_edges=field_edges,field_input_clock_levels=levels,field_clock_terminal_slew_ps=terminal_slew,field_clock_terminal80ps_pass=all(v[1]<=80 for v in terminal_slew.values()),
        field_clock_ports=102352*1536,field_reset_pins=56683*1536,provider_FFs_clock_and_reset=3072,
        die_other_area_reservation_mm2=67.347827,
        rotated_global_directional_routes_and_PG_access_proven=False,field_spine_ssff_and_cuts_qualified=False,
        no_additional_per_layer_or_per_token_reset=True)


def main():
    out=R.ROOT/OUT;out.mkdir(parents=True,exist_ok=True)
    if (out/'model-r1.json').exists():raise ValueError('preserve failed verdict')
    tile=R.obj(N.OUT/'model-r1.json');old,_,_=N.inventory()
    g=json.loads(gzip.decompress((R.ROOT/N.OUT/'local-subtree-allocation-r1.json.gz').read_bytes()))
    net=net_for(g,old);g=L.launch_graph(g);launch=launch_and_root(g,net);field=field_model(tile)
    field['tile_cell_plus_field_clock_buffer_area_mm2']=field['tile_cell_area_mm2']+field['field_input_clock_buffer_area_mm2']
    field['clock_dynamic_pin_wire_W_lower_bound']={c:max(s['clock_dynamic_capacitance_power_W_lower_bound'] for s in r['scenarios'])*1536 for c,r in launch['corners'].items()}
    field['actual_PG_total_power_budget_and_current_limits_supplied']=False
    service=R.obj(R.OUT/'inputs/ampere_contract_receipt_r1.json')['physical_service_slot']
    result=dict(schema='QWEN_LOCAL_PARENT_FULL_FIELD_COMPOSITION_V1',status='SOURCE_AND_PHYSICAL_ADMISSION_OPEN',
        selected_map_sha256=M.MAP_SHA,retained_source_sha256=tile['retained_source_sha256'],local_tile_model=tile,
        numeric_parent_root_launch=launch,launch_geometry=g['launch_route'],field=field,
        persistent_KV_service_slot=service,service_512macro_clock_loads_per_rank_separate_from_1536tiles=True,
        KV_rank_service_macro_area_mm2=4.569720064,KV_TP4_service_macro_area_mm2=4*4.569720064,
        KV_cold_calendar_selected_production=False,
        steady_added_cycles=0,steady_rate_claim=False,
        startup_edges_nominal_demand=max(s['proposed_first_accept_edge_after_provider_edge0'] for r in tile['timing'].values() for s in r['scenarios']),
        startup_once_not_per_layer_token=True,startup_admitted=False,
        binary_init_contract=tile['binary_init_contract'],actual_source_reachable_binary_init_proven=False,
        actual_source_ready_requires='Registered serial/service release acknowledgment plus owned KV tag/read/fill/credit retirement; actual accepted ib/address/control0or1 held through launch; unreset ROM data ignored until valid capture tags',
        stored_Z='FAIL_RETAINED',historical_global157385_fit='FAIL_RETAINED',
        source_map_admission=False,PnR=False,additional_maps=0,numerical_runs=0,
        contextual_SS_setup_FF_hold_qualified=False,
        remaining_gates=['Local SS/FF skew20ps and reset phase bounds at every endpoint; pin-slew bounds unchanged.',
            'Real parent launch/root arrivals and owned initialized binary source proof; no bench phase substitute.',
            'Full clock/reset cuts including meanders, field root spine, rotated PG access, DRC/IR/EM and actual macro capture/data setup/hold.',
            'Actual selected persistent KV retirement/calendar and complete service/serial sink/CDC/PG area; cold calendar remains reference.'])
    if tile['status'].startswith('FAIL'):result['status']=tile['status']
    payload=gzip.compress(R.canon(g),mtime=0);(out/'local-composed-allocation-r1.json.gz').write_bytes(payload)
    result['allocation_sha256']=hashlib.sha256(payload).hexdigest();M.write(out/'model-r1.json',result)
    paths=[Path(__file__).relative_to(R.ROOT),Path('tests/test_qwen_rom_local_parent_composition.py'),Path('tools/uarch_model_qwen_local_parent.py'),
        N.OUT/'model-r1.json',N.OUT/'sourcepins-r1.json',N.OUT/'local-subtree-allocation-r1.json.gz',R.OUT/'inputs/ampere_contract_receipt_r1.json',
        M.OUT/'sourcepins-r1.json']
    M.write(out/'sourcepins-r1.json',dict(sha256={str(p):M.digest(p) for p in paths}))
    M.write(out/'artifact-sha256-r1.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='artifact-sha256-r1.json'})
    print(json.dumps(dict(status=result['status'],launch=launch,field={k:v for k,v in field.items() if k not in ('placements','field_spine_edges')}),indent=2))

if __name__=='__main__':main()
