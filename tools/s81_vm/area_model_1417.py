#!/usr/bin/env python3
"""Inventory-based structural area budgets; never a routed-fit qualification."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')

def checked_write(path, obj):
    assert json.loads(LOCK.read_text())['owner'] == 'codex', 'STOP: coordinator changed'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + '\n')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def shelf(rects, width=3369.6, gap=5.4):
    """Deterministic capacity-only rectangle witness, no reach or cut inference."""
    shelves=[]; placed=[]
    for name,w,h in sorted(rects, key=lambda r:(-r[2],-r[1],r[0])):
        assert w <= width
        for row in shelves:
            if h<=row['h'] and row['x']+w<=width:break
        else:
            row={'x':0.,'y':sum(s['h']+gap for s in shelves),'h':h}
            shelves.append(row)
        placed.append({'name':name,'xy_um':[row['x'],row['y']],'outline_um':[w,h]})
        row['x']+=w+gap
    height=max((r['xy_um'][1]+r['outline_um'][1] for r in placed),default=0)
    return dict(status='CAPACITY_ONLY_NO_CONNECTIVITY_OR_ROUTING_PROOF', width_um=width,
                height_um=height, fits_height_4150=height<=4150, gap_um=gap,rectangles=placed)

def maxrects(rects,width=3369.6,height=4150.,gap=5.4):
    """R0-only capacity witness in the fixed target; exact geometric overlap check."""
    free=[(0.,0.,width+gap,height+gap)];placed=[]
    for name,w,h in sorted(rects,key=lambda r:(-max(r[1:]),-r[1]*r[2],r[0])):
        rw,rh=w+gap,h+gap
        choices=[(min(fw-rw,fh-rh),max(fw-rw,fh-rh),y,x) for x,y,fw,fh in free if rw<=fw+1e-6 and rh<=fh+1e-6]
        if not choices:return dict(status='HEURISTIC_NO_CAPACITY_WITNESS',fits_height_4150=False,failed_rectangle=name)
        _,_,y,x=min(choices);new=[]
        for fx,fy,fw,fh in free:
            if x>=fx+fw-1e-6 or x+rw<=fx+1e-6 or y>=fy+fh-1e-6 or y+rh<=fy+1e-6:
                new.append((fx,fy,fw,fh));continue
            if x>fx:new.append((fx,fy,x-fx,fh))
            if x+rw<fx+fw:new.append((x+rw,fy,fx+fw-x-rw,fh))
            if y>fy:new.append((fx,fy,fw,y-fy))
            if y+rh<fy+fh:new.append((fx,y+rh,fw,fy+fh-y-rh))
        free=[]
        for i,a in enumerate(new):
            if any(i!=j and a[0]>=b[0]-1e-6 and a[1]>=b[1]-1e-6 and a[0]+a[2]<=b[0]+b[2]+1e-6 and a[1]+a[3]<=b[1]+b[3]+1e-6 and (a!=b or i>j) for j,b in enumerate(new)):continue
            free.append(a)
        placed.append({'name':name,'xy_um':[x,y],'outline_um':[w,h]})
    for i,a in enumerate(placed):
        ax,ay=a['xy_um'];aw,ah=a['outline_um'];assert ax+aw<=width+1e-6 and ay+ah<=height+1e-6
        for b in placed[:i]:
            bx,by=b['xy_um'];bw,bh=b['outline_um']
            assert ax+aw+gap<=bx+1e-6 or bx+bw+gap<=ax+1e-6 or ay+ah+gap<=by+1e-6 or by+bh+gap<=ay+1e-6
    return dict(status='CAPACITY_ONLY_NO_CONNECTIVITY_OR_ROUTING_PROOF',width_um=width,
                height_um=max(r['xy_um'][1]+r['outline_um'][1] for r in placed),fits_height_4150=True,gap_um=gap,rectangles=placed)

def build(inventory):
    inv=json.loads(inventory.read_text())
    census_path=ROOT/'results/physical/s81_vm_write_edge_1015/census.json'
    calibration=ROOT/'results/physical/s81_vm_write_edge_1015/lib_area_calibration.json'
    census=json.loads(census_path.read_text())
    families=collections.defaultdict(lambda:dict(count=0,outline_area_um2=0,outlines_um=[]))
    stage=collections.defaultdict(float)
    def category(m):
        if 'bank128' in m:return 'SRAM_banks'
        if any(s in m for s in ('wdispatch','wstage','write_capture','w0_','wcontrol')):return 'write_distribution_storage'
        if 'read_q' in m or 'read_v' in m or 'rsched' in m:return 'read_distribution'
        if 'cap_' in m:return 'serial_capture'
        if 'relay' in m:return 'local_relays'
        if 'x34' in m or 'x43' in m:return 'fixed_ratio_CDC'
        return 'other'
    for leaf in inv['leaves']:
        w,h=leaf['outline_um'];m=leaf['master'];f=families[m]
        f['count']+=1;f['outline_area_um2']+=w*h
        if [w,h] not in f['outlines_um']:f['outlines_um'].append([w,h])
        stage[category(m)]+=w*h
    baseline=sum(f['outline_area_um2'] for f in families.values())
    excluded={'dsfd_vm_static_wdispatch128','dsfd_vm_static_wstage128','dsfd_vm_static_write_capture128'}
    old_write=sum(families[m]['outline_area_um2'] for m in excluded)
    data_shape=[237.6,54.0];meta_shape=[237.6,54.0];sel_shape=[302.4,54.0]
    # 8 payload stripes + one metadata stripe + one select controller.
    new_write=16*(9*data_shape[0]*data_shape[1]+sel_shape[0]*sel_shape[1])
    macro=[174.120,29.736];bank_shape=[194.4,54.0]
    bank_reduction=families['dsfd_vm_static_bank128']['outline_area_um2']-128*bank_shape[0]*bank_shape[1]
    alts=[]
    for name,striped,banks in [('A_striped_fused_write',True,False),('B_local_bank_slot',False,True),('C_combined',True,True)]:
        area=baseline-(old_write-new_write if striped else 0)-(bank_reduction if banks else 0)
        rects=[]
        for l in inv['leaves']:
            if striped and l['master'] in excluded:continue
            w,h=bank_shape if banks and l['master']=='dsfd_vm_static_bank128' else l['outline_um']
            rects.append((l['path'],w,h))
        if striped:
            # Local layout: selector below a3x3 stripe array, explicit routing reserve.
            # Model reserves the local bounding box, not merely bare leaf area.
            for q in range(16):rects.append((f'write_quarter_{q}',820.8,324.0))
        alts.append(dict(name=name,status='UNMEASURED_STRUCTURAL_BUDGET_NOT_ACTUAL_VM_FIT',
            bare_outline_budget_mm2=area/1e6, reduction_against_bare_mm2=(baseline-area)/1e6,
            target_available_area_mm2=3369.6*4150/1e6,
            target_spare_after_bare_mm2=(3369.6*4150-area)/1e6,
            added_write_stream_edges=2 if striped else 0,
            added_write_ns=2/1.2 if striped else 0,
            added_read_stream_edges=0, initiation_interval_edges=1,
            capacity_packing=maxrects(rects), shelf_crosscheck=shelf(rects)))
    # A2 changes selector encoding only. Its source-ingress routing reservation
    # remains the same; do not spend the saved internal bus width twice.
    id_alt=json.loads(json.dumps(alts[0]));id_alt['name']='A2_compact_source_ID'
    id_alt['bare_outline_budget_mm2']-=16*(302.4-172.8)*54/1e6
    id_alt['reduction_against_bare_mm2']=baseline/1e6-id_alt['bare_outline_budget_mm2']
    id_alt['target_spare_after_bare_mm2']=3369.6*4150/1e6-id_alt['bare_outline_budget_mm2']
    alts.append(id_alt)
    pin_models={
       'data16':dict(outline_um=data_shape,faces={'N':848,'S':1272,'E':137,'W':26},
                     declared_state_bits_upper=4800),
       'metadata26':dict(outline_um=meta_shape,faces={'N':1378,'S':1272,'E':217,'W':26},
                         declared_state_bits_upper=7000),
       'selector':dict(outline_um=sel_shape,faces={'N':1272,'S':901,'E':1,'W':2},
                       declared_state_bits_upper=2200)}
    for p in pin_models.values():
        w,h=p['outline_um'];p['pitch_um']=0.096
        p['face_fractions']={face:bits*0.096/(w if face in ('N','S') else h) for face,bits in p['faces'].items()}
        assert max(p['face_fractions'].values())<=0.56
    # Identical-order per-bit selector positions, centered independently on each face.
    # Target stripes have vertical gaps; all selector outputs remain registered.
    pin_links=[]
    for stripe in range(9):
        col=stripe%3;row=stripe//3;target_y=81.0+81.0*row
        for bit in range(1272):
            x=259.2+(302.4-1272*.096)/2+(bit+.5)*.096
            tx=x+243*(col-1)
            pin_links.append(dict(stripe=stripe,bit=bit,source_um=[x,54.0],target_um=[tx,target_y],
                                  manhattan_um=target_y-54.0+abs(tx-x)))
    raw_dir=ROOT/'results/arch/s81_vm_area_1417/raw'
    mapped={p.stem:dict(path=str(p.relative_to(ROOT)),sha256=sha(p),**json.loads(p.read_text()))
            for p in raw_dir.glob('*.json')}
    finite_controls=[]
    for depth in (512,4096,65536):
        macros=13*math.ceil(depth/1024)
        finite_controls.append(dict(compiled_switch_cycles=depth,real_512x128_macro_count=macros,
            allocated_bytes=macros*8192,allocated_cycles_per_stage=1024*math.ceil(depth/1024),
            bare_macro_area_mm2=macros*macro[0]*macro[1]/1e6,
            reuse_closed_bank_outline_mm2=macros*220.32*75.6/1e6,
            status='FINITE_CAPACITY_BUDGET_NO_CONTROL_RTL_OR_PRODUCTION_DEPTH_PROOF'))
    benes=dict(status='FULL128PORT_RAIL_PROVED_NETWORK_GEOMETRY_AND_CONTROL_UNQUALIFIED',
        live_sources=53,padded_input_ports=128,live_bank_lane_destinations=96,
        stages=13,switches_per_stage=64,packet_data_bits=512,packet_metadata_bits=39,
        rail_bits=16,rail_count=35,leaf_count=455,stage_leaf_outline_budget_um=[432.,12.96],
        mapped_stage_ff_expected=4160,physical_edges_per_stage=2,network_edges=26,
        source_W0_to_slot_write_edges=27,source_W0_to_drain_capture_edges='28+lane',
        added_against_old_drain_capture_edges=24,added_ns_before_endpoint_relays=24/1.2,
        initiation_interval_edges=1,selector_bits_per_cycle=832,selector_bytes_per_cycle=104,
        network_bare_leaf_outline_budget_mm2=455*432.*12.96/1e6,
        VM_bare_budget_excluding_controller_and_endpoint_relays_mm2=(baseline-families['dsfd_vm_static_wdispatch128']['outline_area_um2']+455*432.*12.96)/1e6,
        stage_pin_faces=dict(N=2048,S=2048,E=65,W=0),
        stage_face_fractions=dict(N=2048*.096/432.,S=2048*.096/432.,E=65*.096/12.96),
        pipe_local_layout=dict(columns_of_pipes=7,rows_of_pipes=5,stages_progress='N/S',
            pipe_outline_um=[432.,13*18.36],
            network_only_box_um=[3024.,5*13*18.36],
            max_stage_link_manhattan_budget_um=432.+18.36,
            status='NETWORK_ONLY_BUDGET_NOT_SOURCE_OR_BANK_PLACEMENT'),
        controller_macro= 'ot_sram_1r1w_512x128_m4_r2c2',finite_control_storage=finite_controls,
        controller_implementation='Each13stage bank stores packedpairs of64bit controls in real128bit words; fetchearly through realbank+registeredhalfselect. Stage controls are aligned compiler calendar inputs, not hidden ideal memory.',
        source_ingress_bits_per_stream_edge=53*(512+39),network_interstage_bits_per_edge=128*(512+39),
        endpoint_status='All35bitplane source ingress and96bank/lane output transpose UNPLACED; required relays add cycles beyond24',
        production_calendar_status='No supported maximum program depth/loop encoding evidence; no unbounded or free control store assumed',
        route_proof='results/arch/s81_vm_area_1417/benes_routes.json',
        RTL_proof='results/arch/s81_vm_area_1417/benes_rail.json')
    return dict(schema='opentallas.s81.vm-area-structural-model.v1',
        source_inventory=dict(path=str(inventory),sha256=sha(inventory),source_commit=inv['source_commit'],hard_leaf_count=len(inv['leaves'])),
        status='MODEL_AND_COMPONENT_CANDIDATE_ONLY_NO_PHYSICAL_QUALIFICATION',
        baseline_explicit_clock_pin_count=sum(p['bits'] for l in inv['leaves'] for n,p in l['ports'].items() if n=='ck' or n.startswith('ck_') or n.endswith('_ck')),
        invariant=dict(bytes=1048576,banks=128,real_SRAM='ot_sram_1r1w_512x128_m4_r2c2',
            SRAM_dimensions_um=macro,SRAM_area_mm2=128*macro[0]*macro[1]/1e6,
            logical_512bit_read_ports=32,logical_512bit_write_ports=32,sources=53,max_capture_lanes_per_bank=3,
            storage_slots_per_bank=3,ideal_RAM=False),
        baseline_bare_outline_mm2=baseline/1e6,baseline_families=dict(families),baseline_stages_um2=dict(stage),
        measured_candidate_maps=mapped,
        mapped_baseline=dict(census_path=str(census_path.relative_to(ROOT)),census_sha256=sha(census_path),
            calibration_path=str(calibration.relative_to(ROOT)),calibration_sha256=sha(calibration),
            corrected_total_cell_area_um2=census['total_mapped_cell_area_um2'],rows=census['rows']),
        write_replacement=dict(old_outline_um2=old_write,new_leaf_outline_budget_um2=new_write,quarter_count=16,
            pin_models=pin_models,clock_roots=160,previous_dispatch_stage_capture_roots=272,
            local_quarter_box_um=[820.8,324.0],
            edge_accounting={'W0':'P','selector_input_and_payload_sample':'P+1','selector_output':'P+2',
                'stripe_selector_pin_sample':'P+3','stripe_mux_output':'P+4','slot_write':'P+5',
                'registered_drain_capture':'P+6+lane','old_registered_drain_capture':'P+4+lane',
                'downstream_scatter_relay_bank':'unchanged edge count; all writes and dependent reads must shift +2'},
            local_selector_bitlinks=pin_links,max_selector_pin_reach_um=max(x['manhattan_um'] for x in pin_links),
            ingress_cut_budget=dict(payload_bits=6784,metadata_bits=1378,total_source_bits=8162,
                north_bits_budget=4081,south_bits_budget=4081,
                single_face_fraction=8162*.096/820.8,
                two_face_fraction=4081*.096/820.8,
                selector_horizontal_cut_fraction=1272*.096/324.0,
                status='DISTRIBUTED_N_S_INGRESS_BUDGET_ONLY_NO_SOURCE_NET_EMBEDDING',
                required='Distribute real53source data/header landings across N/S and stripe rows; source edges remain registered; no oneface ingress claim',
                open='Actual source terminals, horizontal data cuts, selector routing trees, clock/PG reservations, legal die-overleaf layer allocation'),
            local_reach_scope='SELECTOR_TO_STRIPES_ONLY; source ingress, drains and outgoing bank distribution OPEN'),
        bank_replacement=dict(outline_budget_um=bank_shape,macro_halo_um=5.4,
            macro_plus_halo_um=[macro[0]+10.8,macro[1]+10.8],
            clock_root_policy='Retain one root per bank and measured phi-R; no shared root waiver',
            required_changes='New slot/pin profiles, macro placement, PG/clock insertion, same actual SRAM and pin stages',
            status='UNMAPPED_UNROUTED_AREA_BUDGET'),
        alternatives=alts,
        compact_ID_replacement=dict(status='FULL53SOURCE_COMPONENT_PROVED_PHYSICAL_GEOMETRY_OPEN',
            source='tools/s81_vm/area_id_candidate.sv',proof='results/arch/s81_vm_area_1417/idstripe_proof.json',
            selector_bits=168,record_count=24,record_bits=7,record_encoding='valid+6bit sourceID; ID0..52',
            local_decode='registeredsourceID ->53equalitychoices ->W16orW26 mux ->register',
            selector_outline_budget_um=[172.8,54.0],data_outline_budget_um=data_shape,
            metadata_outline_budget_um=meta_shape,quarter_routing_box_budget_um=[820.8,324.],
            data_pin_faces=dict(N=848,S=168,E=137,W=26),metadata_pin_faces=dict(N=1378,S=168,E=217,W=26),
            selector_pin_faces=dict(N=168,S=901,E=1,W=2),
            selector_horizontal_cut_fraction=168*.096/324.,
            source_ingress_north_south_bits_each=4081,source_ingress_each_face_fraction=4081*.096/820.8,
            maximum_local_selector_manhattan_budget_um=432.,
            same_clock_root_count_as_onehot=160,
            legal_traffic='Allpayload,row,mask,tag andcapture/drain edges exact against currentdispatch/store/capture',
            invalid_duplicate='Stickyfault retained; highestsourceID wins. OldORduplicatepayload intentionally notclaimed equivalent.',
            remaining_gates='Actualsharedsourcebus ingress, clock/PGcut, native localdecode timing and128SRAM composition'),
        fundamental_switch_alternative=benes,
        composed_candidate_calendars=dict(status='ANALYTICAL_CANDIDATES_NOT_PRODUCTION_PROFILES',
            unchanged_read=dict(returned_edge=16,raw_macro_edge=7),
            A_and_A2=dict(write_raw_edge='P+12+lane',write_returned_edge='P+14+lane',dependent_read_issue='Q>=P+6+lane'),
            D_Benes=dict(write_raw_edge='P+34+lane',write_returned_edge='P+36+lane',dependent_read_issue='Q>=P+28+lane'),
            condition='Dagesexcludeanyendpointtranspose relays; no authoritativefullprogrammebinding or5percentclaim;II1doesnotprovefulltokenprice'),
        landing_update=dict(actual_inventory_landing_count=1,old_outline_um=[181.44,181.44],
            proposed_independent_roots=4,new_leaf_outline_um=[95.04,95.04],
            outline_delta_mm2=(4*95.04**2-181.44**2)/1e6,clock_root_delta=3,
            status='SEPARATE_OWNER_CANDIDATE_PENDING_NATIVE_AUDIT_NOT_SILENTLY_ADOPTED'),
        required_RTL_changes=['Opt-in stripe/control hierarchy, full53source interfaces and all3slots',
            'Fuse dispatch/store/capture boundaries while retaining all stage state',
            'Separate selector/meta/eight data clocks and local reset releases; measured insertion per new leaf',
            'Expose fixed compiler drain descriptors early enough for pure drain pin capture',
            'Shift source-write commit/dependent-read calendars by exactly2streamedges; no immutable repricing'],
        open_gates=['Correct per-root reset release, clock insertion/spread and source-matched native views',
            'Map complete53source data16/meta26/selector at all4BANK_BASE values',
            'TT/SS setup FFhold DRC0 with actual facepins and M5/PG',
            'Global all-net pin reach, register relays where required, data/control alignment',
            'Globalcuts,PG/IR,real fullVM placement and compiled production throughput against immutable price'])

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--inventory',type=Path,required=True)
    ap.add_argument('--output',type=Path,default=ROOT/'results/arch/s81_vm_area_1417/model.json')
    a=ap.parse_args();model=build(a.inventory);checked_write(a.output,model)
    print(json.dumps({k:model[k] for k in ('baseline_bare_outline_mm2','baseline_stages_um2')},indent=2))
    for alt in model['alternatives']:
        print(alt['name'],alt['bare_outline_budget_mm2'],alt['capacity_packing']['height_um'],alt['capacity_packing']['fits_height_4150'])
