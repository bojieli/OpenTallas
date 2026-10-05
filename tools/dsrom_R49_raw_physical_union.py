#!/usr/bin/env python3
"""Literal R49 raw-bank/feedback/clock sites; no cross-die read tree or RTL.

Clock sites and supply rails are constructive geometry. Their signal routing,
parent power/clock ingress and hold timing still require source context.
"""
import gzip, hashlib, json, math, re
from collections import Counter
from pathlib import Path
from dsrom_noECC_production_context import lef_masters
from dsrom_noECC_hold_station_geometry import pin_rects
from dsrom_noECC_liberty import cell_bodies
from dsrom_noECC_slew_enable_diagnosis import pin_models
from dsrom_noECC_native_clock_access import parse_rc

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_R49_raw_physical_union_20261002'
HQ='DFFHQNx1_ASAP7_75t_R'; INV='INVx1_ASAP7_75t_R'
NAND='NAND2x1_ASAP7_75t_R'; BUF='BUFx4_ASAP7_75t_R'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):
    p=BASE/'inputs'/name
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def overlap(a,b): return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def cell(name,master,x,y,orientation,role,lef):
    w,h=lef[master]['size_DBU']
    if x%54 or y%270: raise ValueError('non-site placement')
    return dict(instance=name,master=master,bbox_DBU=[x,y,x+w,y+h],orientation=orientation,role=role)
def pin(p,name,lef):
    rr=pin_rects(p,lef[p['master']],name)
    if not rr:raise ValueError('missing pin '+name)
    biggest=max(rr,key=lambda r:(r['bbox_DBU'][2]-r['bbox_DBU'][0])*(r['bbox_DBU'][3]-r['bbox_DBU'][1]))
    a,b,A,B=biggest['bbox_DBU']
    return dict(instance=p['instance'],pin=name,literal_rectangles=rr,point_DBU=[(a+A)/2,(b+B)/2])
def gz_records(path,records):
    path.write_bytes(gzip.compress((''.join(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n' for r in records)).encode(),mtime=0))

def build():
    origins=load('origins.json')
    for r in origins:
        if sha(BASE/'inputs'/r['copy'])!=r['sha256']:raise ValueError('source pin changed')
    r49=load('R49.json'); home=load('Maxwell_home.json'); c=load('capture.json.gz')
    joined=load('Maxwell_R49_home.json')
    epic=load('Epic_allowed_cut.json'); epic_core=load('Epic_core.json')
    station=load('prior_selector_station.json');parent_review=load('selector_parent_review.json')
    selector_join=load('Epic_selector_join_r2.json')
    lef=lef_masters('\n'.join(load('cell_LEF.json.gz').values()))
    libs={k:cell_bodies(k) for k in ('ss','ff')};pin_caps={k:pin_models(v) for k,v in libs.items()}
    area={}
    for master in (HQ,INV,NAND,BUF,'DFFASRHQNx1_ASAP7_75t_R','AND2x2_ASAP7_75t_R'):
        aa={k:float(re.search(r'\barea\s*:\s*([-+\d.eE]+)',libs[k][master])[1]) for k in ('ss','ff')}
        if aa['ss']!=aa['ff']:raise ValueError('corner area mismatch')
        area[master]=aa['ss']
    tc=epic['instance_ledger']
    transport_data_body=math.fsum([tc[HQ]*area[HQ],tc['DFFASRHQNx1_ASAP7_75t_R']*area['DFFASRHQNx1_ASAP7_75t_R'],tc[INV]*area[INV],(tc['BUFx4_repeater_ASAP7_75t_R']+tc['BUFx4_terminal_ASAP7_75t_R'])*area[BUF]])
    clock_floor_body=epic['source_clock_buffer_floor_not_implemented_here']*area[BUF]
    if abs(transport_data_body+clock_floor_body-station['cost']['station_cell_area_um2'])>1e-7:raise ValueError('prior station primitive union not reproduced')
    if epic_core['state_bits_model_gross']!=station['fixed']['core_state_bits']:raise ValueError('core/transport basis mismatch')
    ties_area=math.prod(lef['TIEHIx1_ASAP7_75t_R']['size_DBU'])/1e6
    guard_body=(tc['AND2x2_helper_control_fence']+tc['AND2x2_original_VM_reset_guard'])*area['AND2x2_ASAP7_75t_R']
    transport_tie_body=tc['TIEHIx1_ASAP7_75t_R']*ties_area
    core_async_body=epic_core['async_reset_master_debit']['total_additional_cell_area_with_ties_um2']
    core_base_body=epic_core['area']['accounted_cell_master_sum_um2']
    core_plus_transport_body=math.fsum([core_base_body,core_async_body,transport_data_body,clock_floor_body,guard_body,transport_tie_body])
    rcpath=ROOT/'results/uarch/dsrom_noECC_production_context_20261002/inputs/setRC.tcl'
    rc,via_R=parse_rc(rcpath.read_text())
    if r49['no_combinational_read_tree_across_dies'] is not True:raise ValueError('cross-die tree forbidden')
    width=sum(lef[m]['size_DBU'][0]*n for m,n in ((HQ,1),(INV,1),(BUF,2),(NAND,3)))
    oldwidth=sum(lef[m]['size_DBU'][0]*n for m,n in ((HQ,1),(INV,1),(NAND,3)))
    if (69*width,69*oldwidth)!=(204930,152766):raise ValueError('wrong raw feedback source masters')
    roles=[('dataFF',HQ),('restore',INV),('holdN0',NAND),('holdN1',NAND),('holdN2',NAND),('feedback0',BUF),('feedback1',BUF)]
    bit_template={};xx=0
    for role,master in roles:
        bit_template[role]=dict(instance=role,master=master,bbox_DBU=[xx,0,xx+lef[master]['size_DBU'][0],270],orientation='R0')
        xx+=lef[master]['size_DBU'][0]
    links=[('dataFF','QN','restore','A'),('restore','Y','feedback0','A'),('feedback0','Y','feedback1','A'),('feedback1','Y','holdN1','A'),('holdN1','Y','holdN2','B'),('holdN2','Y','dataFF','D')]
    feedback_paths=[]
    for sr,sp,dr,dp in links:
        a=pin(bit_template[sr],sp,lef);b=pin(bit_template[dr],dp,lef)
        feedback_paths.append(dict(source_role=sr,source_pin=sp,dest_role=dr,dest_pin=dp,
            source_point_local_DBU=a['point_DBU'],dest_point_local_DBU=b['point_DBU'],
            L1_projection_um=sum(abs(v-w) for v,w in zip(a['point_DBU'],b['point_DBU']))/1000,
            source_literal_pin_rectangles=a['literal_rectangles'],dest_literal_pin_rectangles=b['literal_rectangles']))
    if [p['L1_projection_um'] for p in feedback_paths]!=[p['L1_projection_um'] for p in joined['proposed_feedback_only_pin_routes_per_bit']]:raise ValueError('typed feedback endpoints differ from Maxwell')
    delta=69*(width-oldwidth)
    outer=list(home['model_selected_home_DBU']);old_common=list(home['common_circuit_reserved_bbox_DBU'])
    widened=list(joined['canonical_island_home_DBU'])
    common=list(joined['corrected_common_bbox_DBU'])
    if widened!=outer or common!=[old_common[0]+delta,*old_common[1:]]:raise ValueError('current Maxwell home mismatch')
    # Reviewed Maxwell common area remains adequate after its left-edge shift.
    # No new enclosure/debit: preserve the actual same-candidate allocation.
    obstacles=[]
    for key,kind in [('services.json.gz','service'),('field.json.gz','field'),('cfg.json.gz','cfg'),('bands.json.gz','band')]:
        inventory=load(key)
        if kind=='field':
            frames=load('frames.json.gz');sizes={'q_pair':frames['q_priced_outline_um'],'BF16_column_pair':frames['BF_priced_outline_um']}
            xx=yy=4320;rowheight=0;updated=[]
            for row in inventory:
                w,h=[round(v*1000) for v in sizes[row['source_class']]]
                if xx+w+4320>33000000:xx=4320;yy+=rowheight+8640;rowheight=0
                updated.append(dict(row,bbox_DBU=[xx,yy,xx+w,yy+h]));xx+=w+8640;rowheight=max(rowheight,h)
            if len(updated)!=2048:raise ValueError('incomplete source field')
            if max(r['bbox_DBU'][3] for r in updated)-max(r['bbox_DBU'][3] for r in inventory)!=home['field_end_delta_DBU']:raise ValueError('Maxwell field regeneration mismatch')
            inventory=updated
        for row in inventory:
            b=row['bbox_DBU'];dy=home['field_end_delta_DBU'] if kind in ('cfg','band') else 0
            obstacles.append(dict(kind=kind,name=row.get('name',str(row.get('local_pair'))),bbox_DBU=[v+(dy if i%2 else 0) for i,v in enumerate(b)]))
    selector_box=selector_join['slot']['current_selector_bbox_DBU']
    obstacles.append(dict(kind='selector',name='retained_selector',bbox_DBU=selector_box))
    # Reserve ALL separately priced core-clock buffers outside the core slot.
    # The core's existing headroom is not credited again. This is a site bank,
    # not a routed clock tree; sink assignment and upstream phase remain open.
    clock_count=selector_join['clock']['additional_core_fanout_floor']['BUF_cells']
    clock_site_rows=(selector_box[3]-selector_box[1])//540
    columns=math.ceil(clock_count/clock_site_rows)
    cx=math.ceil((selector_box[2]+4320)/54)*54;cy=math.ceil(selector_box[1]/540)*540
    clock_box=[cx,cy,cx+columns*lef[BUF]['size_DBU'][0],cy+clock_site_rows*540]
    selector_clocks=[];index=0
    for level,count in enumerate(selector_join['clock']['additional_core_fanout_floor']['leaf_to_root_counts']):
        for j in range(count):
            row,column=divmod(index,columns)
            selector_clocks.append(cell(f'selector_core_clock_L{level}_{j}',BUF,cx+column*lef[BUF]['size_DBU'][0],cy+row*540,'R0','selector_core_clock_additional',lef));index+=1
    if index!=clock_count:raise ValueError('selector clock count mismatch')
    selector_conflicts=[p for p in obstacles if overlap(clock_box,p['bbox_DBU'])]
    if selector_conflicts or overlap(clock_box,widened):raise ValueError('selector added clock bank overlaps existing allocation')
    if not (0<=clock_box[0]<clock_box[2]<=33000000 and 0<=clock_box[1]<clock_box[3]<=26000000):raise ValueError('selector bank outside die')
    selector_rails=[dict(net='VSS' if j%2==0 else 'VDD',layer='M1',bbox_DBU=[clock_box[0],cy+j*270-9,clock_box[2],cy+j*270+9]) for j in range(2*clock_site_rows+1)]
    for item in selector_clocks:
        for supply in ('VDD','VSS'):
            for r in pin_rects(item,lef[BUF],supply):
                b=r['bbox_DBU'];rail=selector_rails[round(((b[1]+b[3])/2-cy)/270)]
                if rail['net']!=supply or rail['layer']!=r['layer'] or not all((rail['bbox_DBU'][0]<=b[0],rail['bbox_DBU'][1]<=b[1],rail['bbox_DBU'][2]>=b[2],rail['bbox_DBU'][3]>=b[3])):raise ValueError('selector clock supply outside literal rails')
    gz_records(BASE/'selector_core_clock_cells.jsonl.gz',selector_clocks)
    clock_body=clock_count*area[BUF];bank_reserve=math.prod([clock_box[2]-clock_box[0],clock_box[3]-clock_box[1]])/1e12
    if bank_reserve<2*clock_body/1e6:raise ValueError('selector bank under-reserved')
    conflicts=[p for p in obstacles if overlap(widened,p['bbox_DBU'])]
    cases={}
    for s in r49['shards']:
        shard=s['physical_shard'];seats=s['seats'];rootdefs={int(k):v for k,v in s['depths_by_local_root'].items()}
        prior=next(v for v in home['per_shard_raw_slots'] if v['shard']==shard)
        x,y=prior['bbox_DBU'][:2]; raw=[x,y,x+69*width,y+seats*540]
        old_conflict=[max(raw[0],old_common[0]),max(raw[1],old_common[1]),min(raw[2],old_common[2]),min(raw[3],old_common[3])]
        p=[];nets=[];root_sites=[];rows=[];parents=[];rowidx=0;bankparents=[]
        def place_clock(name,xx,yy):
            v=cell(name,BUF,xx,yy,'MX','raw_clock_buffer',lef);p.append(v);return v
        for root,depth in sorted(rootdefs.items()):
            bankfirst=rowidx;seatparents=[]
            owned=[v['row'] for v in s['ordered_owned_rows'] if v['local_root']==root]
            if len(owned)!=depth:raise ValueError('seat ownership mismatch')
            for seat in range(depth):
                yy=y+rowidx*540;prefix=f's{shard}_r{root}_seat{seat}'
                ffs=[]
                for bit in range(69):
                    xx=x+bit*width
                    # Actual two BUFx4 feedback cells included INSIDE raw width.
                    for role,master in roles:
                        v=cell(f'{prefix}_b{bit}_{role}',master,xx,yy,'R0',role,lef);p.append(v)
                        if role=='dataFF':ffs.append(v)
                        xx+=lef[master]['size_DBU'][0]
                select=cell(prefix+'_write_select_INV',INV,x,yy+270,'MX','row_write_select_INV',lef);p.append(select)
                leaves=[]
                for group in range(9):
                    b=place_clock(prefix+f'_clock_leaf{group}',x+group*8*width+162,yy+270);leaves.append(b)
                    sinks=[pin(v,'CLK',lef) for v in ffs[group*8:(group+1)*8]]
                    nets.append(dict(name=b['instance']+'_Y',source=pin(b,'Y',lef),sinks=sinks,source_clock_level=0,wire_and_native_access_not_yet_constructed=True))
                for group in range(2):
                    b=place_clock(prefix+f'_clock_parent{group}',x+(16+32*group)*width+594,yy+270);seatparents.append(b)
                    nets.append(dict(name=b['instance']+'_Y',source=pin(b,'Y',lef),sinks=[pin(v,'A',lef) for v in leaves[group*8:(group+1)*8]],source_clock_level=1,wire_and_native_access_not_yet_constructed=True))
                rows.append(dict(local_root=root,logical_root=root+64*shard,seat=seat,owned_global_row=owned[seat],row_origin_DBU=[x,yy],raw_DATA_FF_RESETN_ports=0))
                rowidx+=1
            for group in range(math.ceil(len(seatparents)/8)):
                yy=y+bankfirst*540+270;xx=x+(24+32*group)*width+1026
                b=place_clock(f's{shard}_r{root}_clock_bank{group}',xx,yy);bankparents.append(b)
                nets.append(dict(name=b['instance']+'_Y',source=pin(b,'Y',lef),sinks=[pin(v,'A',lef) for v in seatparents[group*8:(group+1)*8]],source_clock_level=2,wire_and_native_access_not_yet_constructed=True))
        if rowidx!=seats:raise ValueError('seat count')
        # Upper forest has separate root pin on each physical die. The named
        # sites reserve a row of the translated control home, not a shared die.
        children=bankparents;cursor=common[0];upper=[]
        for level in (3,4,5):
            nextlevel=[]
            for j in range(max(1,math.ceil(len(children)/8))):
                b=cell(f's{shard}_clock_upper_L{level}_{j}',BUF,cursor,common[1],'R0','raw_clock_upper',lef);cursor+=432;p.append(b);upper.append(b);nextlevel.append(b)
                nets.append(dict(name=b['instance']+'_Y',source=pin(b,'Y',lef),sinks=[pin(v,'A',lef) for v in children[j*8:(j+1)*8]],source_clock_level=level,wire_and_native_access_not_yet_constructed=True))
            children=nextlevel
        if len(children)!=1:raise ValueError('finite forest root')
        byname={v['instance']:v for v in p}
        for n in nets:
            sinks=n['sinks'];xy=[n['source']['point_DBU']]+[t['point_DBU'] for t in sinks]
            # Lower bound only; not routed wire or upper RC. This catches
            # the false assumption that5.76fF always covers an arbitrary reach.
            span=(max(t[0] for t in xy)-min(t[0] for t in xy)+max(t[1] for t in xy)-min(t[1] for t in xy))/1000
            n['endpoint_spanning_L1_lower_bound_um']=span
            n['M8_M9_only_route_family_minimum_metal_C_fF']=span*min(rc['M8'][1],rc['M9'][1])
            n['source_wire_allowance_5p76_fF_exceeded_in_this_route_family']=n['M8_M9_only_route_family_minimum_metal_C_fF']>5.76
            n['SS_FF_pin_cap_fF']={k:math.fsum(pin_caps[k][byname[sink['instance']]['master']][sink['pin']]['max_cap_fF'] for sink in sinks) for k in ('ss','ff')}
            n['wire_C_is_family_lower_bound_not_extraction_or_full_cone_upper_bound']=True
        # This pinned capture abstract uses M1 supplies. Do not transfer the
        # complete-element's M2 PG projection merely because masters match.
        # Dense literal rails extend to the final MX word-select/clock row's top
        # VSS contact. That rail was absent from the old2*seats projection.
        rails=[dict(net='VSS' if j%2==0 else 'VDD',layer='M1',bbox_DBU=[x,y+j*270-9,raw[2],y+j*270+9]) for j in range(2*seats+1)]
        # Connect the separately reserved upper-clock row to the same local
        # VSS/VDD projections across the4.32um moat. External M2+ feeds and
        # power-current/IR budgets are not supplied by this local rail union.
        for rail in rails[:2]:rail['bbox_DBU'][2]=cursor
        power_missing=[]
        for item in p:
            for supply in ('VDD','VSS'):
                for rect in pin_rects(item,lef[item['master']],supply):
                    bb=rect['bbox_DBU']
                    if not any(r['net']==supply and r['layer']==rect['layer'] and r['bbox_DBU'][0]<=bb[0] and r['bbox_DBU'][1]<=bb[1] and r['bbox_DBU'][2]>=bb[2] and r['bbox_DBU'][3]>=bb[3] for r in rails):power_missing.append([item['instance'],supply])
        if power_missing:raise ValueError('local literal supply pin outside named rail union')
        for master in (HQ,INV,NAND,BUF):
            pins={v['name']:v for v in lef[master]['pins']}
            for supply in ('VDD','VSS'):
                if not any(r['layer']=='M1' for r in pins[supply]['rectangles']):raise ValueError('wrong raw power master')
        gz_records(BASE/f'shard{shard}_cells.jsonl.gz',p)
        gz_records(BASE/f'shard{shard}_clock_nets.jsonl.gz',nets)
        counts=Counter(v['master'] for v in p)
        clocklevels=Counter(n['source_clock_level'] for n in nets)
        feedback=2*seats*69
        cases[str(shard)]=dict(physical_shard=shard,seats=seats,raw_slot_bbox_DBU=raw,shifted_control_bbox_DBU=common,
            prior_control_overlap_bbox_DBU=old_conflict,prior_control_overlap_area_um2=(old_conflict[2]-old_conflict[0])*(old_conflict[3]-old_conflict[1])/1e6,
            rows=rows,primitive_master_counts=dict(counts),physical_clock_levels=dict(clocklevels),raw_clock_buffer_count=len(nets),raw_clock_root_input=pin(children[0],'A',lef),
            raw_clock_root_source_parent_required=True,equal_depth_is_not_skew=True,clock_SKew_and_RC_qualified=False,
            raw_resettable_FF_count=0,control_reset_count_not_silently_split_or_replicated=1483,
            raw_record_bits=seats*69,MACs_per_cycle=0,no_ready_root_ports=64,
            maximum_root_boundary_bits_per_stream_cycle=64*69,maximum_root_boundary_bytes_per_stream_cycle=64*69/8,
            source_feedback_BUF_count=feedback,feedback_cells_in_width_not_recharged=True,
            PG_M1_literal_rails=rails,actual_final_MX_supply_rail_added=True,parent_PG_via_feeds_and_current_capacity_qualified=False,
            literal_supply_pins_not_in_same_net_rail=power_missing,upper_clock_rail_bridge_covers_moat=True,
            upper_clock_site_row_reservation_DBU=[common[0],common[1],cursor,common[1]+270],
            clock_nets_exceeding_source_5p76_wire_allowance=[dict(name=n['name'],level=n['source_clock_level'],spanning_L1_um=n['endpoint_spanning_L1_lower_bound_um'],M8_M9_family_minimum_metal_C_fF=n['M8_M9_only_route_family_minimum_metal_C_fF']) for n in nets if n['source_wire_allowance_5p76_fF_exceeded_in_this_route_family']],
            source_local_read_mux_node_count=(seats-64)+63,local_drain_and_selector_pipeline_source_required_from_Nash=True,
            no_shared_576_comb_tree=True,clock_and_feedback_wires_not_timing_qualified=True,
            cell_artifact_sha256=sha(BASE/f'shard{shard}_cells.jsonl.gz'),net_artifact_sha256=sha(BASE/f'shard{shard}_clock_nets.jsonl.gz'))
    rawclock=sum(v['raw_clock_buffer_count'] for v in cases.values());oldclock=sum(c['fanout8_tree']['clock'])
    ordered_runs=[]
    for row in r49['ordered_global_output_rows']:
        shard=((row%256)//2)//64
        if ordered_runs and ordered_runs[-1]['physical_shard']==shard:ordered_runs[-1]['row_end_exclusive']=row+1
        else:ordered_runs.append(dict(physical_shard=shard,row_begin=row,row_end_exclusive=row+1))
    result=dict(schema='DS_R49_RAW_PHYSICAL_UNION_V1',candidate=home['candidate'],source_origins=origins,
        physical_shards=cases,raw_bit_width_DBU=width,raw_word_width_DBU=69*width,mandatory_width_delta_DBU=delta,
        predecessor_capture_home_DBU=outer,joined_Maxwell_capture_home_DBU=widened,reviewed_Maxwell_R49_home_bound=True,
        complete_parent_known_rectangle_conflicts=conflicts,inside_26x33mm=0<=widened[0]<widened[2]<=33000000 and 0<=widened[1]<widened[3]<=26000000,
        source_body_clock_buffers_whole_owner=oldclock,raw_only_constructed_clock_buffers=rawclock,
        minimum_extra_clock_buffers_vs_whole_owner_floor=max(0,rawclock-oldclock),
        minimum_extra_clock_cell_area_um2=max(0,rawclock-oldclock)*c['source_cell_facts'][BUF]['SS']['area_um2'],
        minimum_extra_clock_core_reserve_at50pct_um2=2*max(0,rawclock-oldclock)*c['source_cell_facts'][BUF]['SS']['area_um2'],
        enclosure_delta_per_die_mm2=0,
        previous_raw_reservation_um2=r49['feedback']['baseline_old_raw_slot_reservation_um2'],
        corrected_raw_reservation_um2=r49['feedback']['total_raw_slot_reservation_um2'],
        raw_feedback_corrected_reservation_delta_um2=r49['feedback']['slot_delta_um2'],
        proposed_ordered_read_runs=ordered_runs,read_runs_do_not_prove_service_rate_or_deadlines=True,
        extra_control_clock_tree_not_free=True,no_automatic_tree_embedding_credit=True,
        inherited_control_state_bits=1483,R49_context_request_reply_bits=[170,187,240],physical_shard_is_not_stage_or_rank=True,
        ordered_output_rows_preserved=True,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,period_ps=2500/3,
        added_capture_edges=0,physical_build_admitted=False,actual_pipeline_adopted=False,
        source_capture_supply_layer='M1',complete_element_M2_PG_not_transferred=True,
        source_raw_role_order_from_Maxwell=joined['actual_raw_bit_cell_roles'],forward_does_not_traverse_feedback_BUF=True,
        typed_feedback_literal_endpoint_template=feedback_paths,typed_feedback_prototype_source_sha256=joined['source_feedback_prototype_sha256'],
        forward_path_contract=dict(write_input='root raw69 ->holdN0/A ->holdN0/Y ->holdN2/A ->holdN2/Y ->dataFF/D',
             read_output='dataFF/QN ->restore/A ->restore/Y ->local read mux input; feedback0/A is an additional branch load, not inserted in the forward path',
             conditional_mux_equation='D=(write_enable & raw_input) | (!write_enable & restored_held_Q)',
             FF_QN_inversion_retained=True,new_forward_buffer_count=0,actual_forward_wire_hold_and_read_mux_provider_not_qualified=True),
        finite_credit_contract=dict(raw_capture_READY=False,reserve_all576_owned_seats_before_phase_GO=True,
             per_shard_capacity=[320,256],per_root_depths='shard0 roots0..31 depth6, roots32..63 depth4; shard1 all64 roots depth4',
             physical_shard_identity_separate_from_stage_rank=True,request_bits=187,reply_bits=240,context_bits=170,
             read_sink_seat_reserved_before_issue_required=True,ACK_not_home_visibility=True,
             phase_release_requires_source_idle_and_zero_delivery_debt_and_causal_home_visible=True,
             implemented_read_credit_count_and_token_FIFO_capacity_not_bound=True,
             implementation_owner='Nash local64-root drain/control/selector and Kepler lease/visibility provider',
             actual_accepted_consumer_and_capture_deadline_not_bound=True),
        source_RC_path=str(rcpath.relative_to(ROOT)),source_RC_sha256=sha(rcpath),clock_wire_RC_is_not_extracted=True,
        selector_additional_core_clock_bank=dict(source_commit='5ff80ab93455caddfce7c2adaed91e0cef0e3b78',
            source_current_selector_bbox_DBU=selector_box,
            predecessor_Maxwell_selector_bbox_DBU=home['retained_selector_core_bbox_DBU'],
            current_core_rectangle_area_mm2=math.prod([selector_box[2]-selector_box[0],selector_box[3]-selector_box[1]])/1e12,
            core_rectangle_local_colocation_deficit_mm2=selector_join['slot']['deficit_if_all_core_clock_floor_colocated_mm2'],
            source_full_reservation_mm2=selector_join['area']['proposed_finite_cell_reservation_with_core_clock_floor'],
            total_selector_state_bits=selector_join['state']['total_proposed_core_plus_cut_bits'],
            already_priced_transport_clock_buffers=selector_join['clock']['station_fanout_floor']['BUF_cells'],
            separately_added_core_clock_buffers=clock_count,clock_cell_body_um2=clock_body,
            source_additional_core_clock_50pct_mm2=2*clock_body/1e6,
            named_site_bank_bbox_DBU=clock_box,row_pitch_DBU=540,columns=columns,rows=clock_site_rows,
            unused_legal_sites=clock_site_rows*columns-clock_count,legal_site_reservation_mm2=bank_reserve,
            full_bank_debited_not_only_core_rectangle_deficit=True,
            complete_source_reservation_replacing_analytical_clock_floor_with_bank_mm2=2*core_plus_transport_body/1e6+bank_reserve,
            complete_reservation_including_current_core_rectangle_headroom_mm2=2*core_plus_transport_body/1e6+bank_reserve+selector_join['slot']['current_selector_slot_mm2']-selector_join['slot']['core_plus_ASR_debit_mm2'],
            minimum_selector_to_clock_bank_gap_DBU=clock_box[0]-selector_box[2],
            conflicts_with_known_field_service_cfg_band_selector_rectangles=selector_conflicts,
            no_corridor_borrowing_or_core_headroom_credit=True,
            cell_artifact_sha256=sha(BASE/'selector_core_clock_cells.jsonl.gz'),
            PG_M1_literal_rails=selector_rails,literal_supply_pin_union_checked=True,
            clock_pin_shapes_per_cell=pin_rects(selector_clocks[0],lef[BUF],'A'),
            no_new_resettable_cells=True,existing_selector_RESETN_SETN_union_still_required=True,
            parent_PG_feed_vias_current_and_pin_escape_not_qualified=True,
            actual_core_sink_assignment_routes_parent_root_and_matched_skew_not_bound=True,
            named_clock_sites_are_not_routed_clock_tree_or_deadline_proof=True,
            split_into_PAR2_shards_or_ownership_move_not_adopted=True),
        selector_source_join=dict(source_commits=['545f2fa1ca39ce0a8147873e6909b956edc2b07e','a4e504d36'],
            literal_packet_cut_helpers=epic['helpers'],transport_ASR_present_flags=epic['instance_ledger']['DFFASRHQNx1_ASAP7_75t_R'],
            transport_tie_providers=epic['instance_ledger']['TIEHIx1_ASAP7_75t_R'],
            additional_core_ASR_and_tie_providers=epic_core['async_reset_master_debit']['new_minus_replaced_async_bits'],
            core_added_state_bits=epic_core['added_state_bits_vs_original_model'],
            primitive_sources=epic['source_context_pins'],source_compile_admitted=epic['compile_admitted'],
            mapped_primitive_and_backend_qualification_not_supplied=True,source_capture_timing_FAIL_preserved=epic['capture_context_FAIL_preserved'],
            actual_consumer_deadline=epic['consumer_deadline'],geometry_or_functional_TT_sources_do_not_supply_SSFF_or_runtime_credit=True,
            complete_selector_reservation_not_replaced_by_candidate_only_charge=True),
        selector_complete_known_cost_once=dict(core_state_gross=epic_core['state_bits_model_gross'],core_state_increment=epic_core['added_state_bits_vs_original_model'],
            original_core_state_inferred=epic_core['state_bits_model_gross']-epic_core['added_state_bits_vs_original_model'],
            transport_payload_and_present_FF=tc[HQ]+tc['DFFASRHQNx1_ASAP7_75t_R'],
            core_plus_transport_state_gross=epic_core['state_bits_model_gross']+tc[HQ]+tc['DFFASRHQNx1_ASAP7_75t_R'],
            core_source_construction_body_with_declared_allowances_um2=core_base_body,
            core35_ASR_replacement_and_ties_delta_um2=core_async_body,
            transport_data_primitives_body_um2=transport_data_body,transport_clock_floor_already_in_old_station=epic['source_clock_buffer_floor_not_implemented_here'],
            transport_clock_floor_body_um2=clock_floor_body,old_station_body_exact_reproduced_um2=transport_data_body+clock_floor_body,
            old_station_not_recharged_as_new_transport=True,
            transport19_guard_body_um2=guard_body,transport229_tie_body_um2=transport_tie_body,
            complete_known_construction_body_um2=core_plus_transport_body,complete_known_construction_at50pct_reserve_mm2=2*core_plus_transport_body/1e6,
            retained_core_slot_from_Maxwell_mm2=home['selector_core_1p68242_reserved_once'] and 1.68242,
            extra_transport_station_guards_ties_vs_retained_core_slot_mm2=2*core_plus_transport_body/1e6-1.68242,
            baseline_core_ASR_netlist_census_and_global_route_clock_PG_still_open=True,
            old_station_containment_inside_fixed418_debit_not_proven=True,source_constructor_not_mapped_physical_area=True,
            parent_review_tests=parent_review['parent_tests'],parent_review_is_static_only=parent_review['prepared_verifier_tests_are_not_actual_HDL_runs']),
        required_parent_source_bindings=['Named parent clock/PG union including control home left edge displaced by52.164um in reviewed unchanged324um enclosure',
          'Nash separate64-root local drain/selector registered cuts, finite result seats/reverse credit and reset-safe valid retirement',
          'Actual per-die upstream CLK driver/phase/root path and control RESETN release waveform',
          'Typed feedback min/max wires, PG feeds/vias/OBS and clock slew/skew at literal pins; scalar20NAND historical cone not a576-seat crossdie provider'])
    (BASE/'model.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    return result
if __name__=='__main__':
    x=build();print(json.dumps({k:x[k] for k in ('mandatory_width_delta_DBU','joined_Maxwell_capture_home_DBU','complete_parent_known_rectangle_conflicts','raw_only_constructed_clock_buffers','minimum_extra_clock_buffers_vs_whole_owner_floor')},indent=2))
