#!/usr/bin/env python3
"""Pinned unique-net/abstract occupancy/97-node TC prerequisite; no RTL/P&R.

Produces net groups, cut bounds and per-node dependency expressions. The macro
LEF gives actual pins/OBS/power rectangles, never internal free cell locations
or parent routed PDN/occupancy. A safe physical cut remains a named gate.
"""
import argparse
from collections import Counter,defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from hbm_tc_geometry_prerequisite import ROOT,BASE,SOURCE,SX,SY,ceilgrid
from hbm_tc_nested_dot_delta import selected_grid

PRIOR='23a7aa87c9ff595ce064aead4d5d289c35f77347'
GEOM='abd91bff16eb9b927d0140f94bcb6c4d13d7b90c'
DOT='d8fe3fd2140ff953a47bf9277360f3689e8c61ee'
BDREV='283c3d1d9e71a3727acace329ff322ce14a928a5'
DEST='results/uarch/hbm_tc_unique_net_sourceplan_20261002'


def full_lef(text):
    size=list(map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text).groups()));pins={};obs=[]
    for name,body in re.findall(r'\bPIN\s+(\S+)\s+(.*?)\n\s*END\s+\1(?:\s|$)',text,re.S):
        use=re.search(r'USE\s+(\w+)',body)[1];rects=[]
        for layer,chunk in re.findall(r'LAYER\s+(\w+)\s*;(.*?)(?=LAYER|END|$)',body,re.S):
            for r in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',chunk):rects.append(dict(layer=layer,rect_um=list(map(float,r))))
        pins[name]=dict(use=use,rectangles=rects)
    if '\n  OBS' in text:
        for layer,chunk in re.findall(r'LAYER\s+(\w+)\s*;(.*?)(?=LAYER|END|$)',text.split('\n  OBS',1)[1],re.S):
            for r in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',chunk):obs.append(dict(layer=layer,rect_um=list(map(float,r))))
    return dict(size_um=size,pins=pins,OBS=obs)


def union_area(rects):
    xs=sorted({v for r in rects for v in [r[0],r[2]]});area=0
    for a,b in zip(xs,xs[1:]):
        ys=sorted((r[1],r[3]) for r in rects if r[0]<b and r[2]>a);length=0;end=-math.inf
        for lo,hi in ys:
            length+=max(0,hi-max(lo,end));end=max(end,hi)
        area+=(b-a)*length
    return area


def i8word(code):
    sign=code>>7;mag=((~code+1)&255) if sign else code
    if not mag:return 0
    msb=mag.bit_length()-1;nrm=(mag<<(7-msb))&255
    return sign<<15 | (127+msb)<<7 | (nrm&127)


def source_contract(texts):
    checks={
        'qweight':'iw[sp*LS*16 +: LS*16]', 'qfragment':'ix[(col * L + sp * LS + q) * 16 +: 16]',
        'qtag':'tag(stag[TAGW-1:0])','qvalid':'v(sov[0])',
        'vweight':'iwf[sp*LSB*16 +: LSB*16]','vfragment':'ix[col*XC + LB*266 + (sp*LSB + q)*16 +: 16]',
        'bdweight':'iwq[sp*LBS*256 +: LBS*256]','bdexp':'iwe[sp*LBS*10 +: LBS*10]',
        'bdzero':"{4'd0, s1_w[128*j + 4*b +: 4]}",
        'bdhigher':"(j < LB / 2) ? s1_w[256*j + 8*b +: 8] : 8'd0",
        'bubble':"wire [15:0] wg = v_ql[l] ? w_q[16*l +: 16] : 16'd0;",
        'unmasked_y':'y <= s4_y; fault <= s4_v && s4_bad;', 'i8_lsb_constant':"(m == 8'd0) ? 16'd0 : {s, 8'd127 + {5'd0, msb}, nrm[6:0]}"}
    for k,s in checks.items():
        if not any(s in t for t in texts.values()):raise ValueError('source binding drift '+k)
    return checks


def pincenter(info,pin,row):
    rs=info['pins'][pin]['rectangles']
    if len(rs)!=1:raise ValueError('signal multi-access requires explicit binding')
    a,b,c,d=rs[0]['rect_um'];return [row['x']+(a+c)/2,row['y']+(b+d)/2]


def netgroups(model,rows,abstracts):
    q=model=='qwen';L=32 if q else 16;NC=16 if q else 8;groups=[];unused=[]
    for row in rows:
        if row['kind'] not in ('failed_source_TC','same_source_BD'):continue
        col,sp=map(int,re.search(r'g_col\[(\d+)\].g_sub\[(\d+)\]',row['name']).groups());tc=row['kind']=='failed_source_TC';a=abstracts['tc' if tc else 'bd']
        def add(family,src,width,port,role,constant=False):
            groups.append(dict(parent_net_family=family,source_bit_lo=src,width=width,port=port,instance=row['name'],column=col,subpartition=sp,role=role,constant_zero=constant,endpoint_centers_um=[pincenter(a,port+'['+str(i)+']',row) for i in range(width)] if width>1 else [pincenter(a,port,row)]))
        if tc:
            add('iw' if q else 'iwf',sp*L*16,L*16,'w','input_weight')
            add('ix',col*(128*16 if q else 3152)+(0 if q else 2128)+sp*L*16,L*16,'x','input_fragment')
        else:
            add('iwq',sp*512,512,'wq','input_weight');add('iwe',sp*20,20,'we','input_weight')
            # Packed ix uses266-bit block lanes: q512 and e20 are interleaved.
            for block in range(2):
                for port,lo,w,offset in [('xq',0,256,0),('xe',0,10,256)]:
                    pp=[pincenter(a,port+'['+str(block*w+i)+']',row) for i in range(w)]
                    groups.append(dict(parent_net_family='ix',source_bit_lo=col*3152+(sp*2+block)*266+offset,width=w,port=port,port_bit_lo=block*w,instance=row['name'],column=col,subpartition=sp,role='input_fragment',constant_zero=False,endpoint_centers_um=pp))
        # Logical identity across all consumers, not one copy per column.
        for family,port in [('iv' if q else 'iv_f' if tc else 'iv_b','v'),('ifirst','first'),('ilast','last'),('clk','clk'),('rst_n','rst_n')]:add(family,0,1,port,'clock_reset' if port in ('clk','rst_n') else 'input_metadata')
        add('itag',0,16,'tag','input_metadata')
        if not tc:add('ifp4',0,1,'fp4','input_metadata')
        # Output pin nets exist but unused tag/valid bits have no parent sinks.
        add(row['name']+'.y',0,32,'y','output')
        add(row['name']+'.fault',0,1,'fault','output')
        if sp==0:
            add(row['name']+'.otag',0,16,'otag','output');add(row['name']+'.ov',0,1,'ov','output')
        else:unused.append(dict(instance=row['name'],unconsumed_parent_ports={'otag':16,'ov':1},physical_pins_still_exist=True))
    nets={}
    for g in groups:
        for i in range(g['width']):
            bit=g['source_bit_lo']+i;family=g['parent_net_family'];constant=(q and family=='iw' and bit%16==0) or (family=='iwq' and bit//256>=4 and bit%8>=4)
            if constant:g.setdefault('constant_zero_source_bit_offsets',[]).append(i)
            key=family+'['+str(bit)+']'
            n=nets.setdefault(key,dict(family=family,bit=bit,role=g['role'],constant_zero=constant,endpoints=[]))
            pin=g['port'] if g['width']==1 else g['port']+'['+str(g.get('port_bit_lo',0)+i)+']'
            n['endpoints'].append(dict(instance=g['instance'],pin=pin,center_um=g['endpoint_centers_um'][i]))
    return groups,nets,unused


def channel_census(nets,rows,model):
    # These are partition cuts through the proposed compact placement, NOT
    # claims of empty physical corridors or driver locations. For a shared
    # net with sinks on both sides, a crossing is unavoidable. Single-sink
    # nets need a driver/consumer coordinate to determine their crossing.
    tc=[r for r in rows if r['kind']=='failed_source_TC'];cuts=[]
    xs=sorted({round(r['x']+r['w']/2,6) for r in tc});ys=sorted({round(r['y']+r['h']/2,6) for r in tc})
    for axis,points in [('x',xs),('y',ys)]:
        for pos in [(a+b)/2 for a,b in zip(points,points[1:])]:
            low=Counter();high=Counter();constants=Counter();spans=[]
            for key,n in nets.items():
                if n['role']=='clock_reset':continue
                if n['constant_zero']:constants[n['family']]+=1;continue
                vals=[e['center_um'][0 if axis=='x' else 1] for e in n['endpoints']]
                high[n['role']]+=1
                if min(vals)<pos<max(vals):low[n['role']]+=1;spans.append(key)
            cuts.append(dict(axis=axis,coordinate_um=round(pos,6),source_bound_unique_crossing_lower_by_role=dict(low),unknown_driver_unique_crossing_upper_by_role=dict(high),total_unique_lower=sum(low.values()),total_unique_upper=sum(high.values()),mandatory_spanning_net_ids=spans,constant_local_tie_eligible_source_bits_by_family=dict(constants),capacity_is_unbound='Cut intersects macro OBS; partition demand is not channel routability. Actual producer/consumer positions, layer routes and PDN vias required.'))
    return cuts


def build():
    pins=[]
    def raw(rev,path):
        b=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT);pins.append(dict(git=rev,path=path,sha256=hashlib.sha256(b).hexdigest()));return b
    def rec(rev,path):return json.loads(raw(rev,path))
    for p in ['tools/hbm_tc_geometry_prerequisite.py','tools/hbm_tc_nested_dot_delta.py','tools/qwen_hbm_complete_program.py']:
        if (ROOT/p).read_bytes()!=raw(PRIOR,p):raise ValueError('pinned helper differs')
    attribution=rec(PRIOR,'results/uarch/hbm_tc_reservation_attribution_20261001/model.json')
    upper=rec(GEOM,'results/uarch/hbm_tc_geometry_prerequisite_20261001/model.json')
    nested=rec(DOT,'results/uarch/hbm_tc_nested_dot_delta_20261001_r2/summary.json')
    texts={}
    for p in ['rtl/gpu/ot_gpu_sm_q.sv','rtl/gpu/ot_gpu_sm_v.sv','rtl/gpu/ot_gpu_xstore.sv','rtl/gpu/ot_gpu_tc_col.sv','rtl/v41rom/ot_v41_bmul2.sv','tools/chip_assembly/tcl/pdn_sm.tcl','tools/chip_assembly/tcl/pdn_block.tcl','tools/chip_assembly/floorplans.py']:
        texts[p]=raw(SOURCE,p).decode()
        if p not in ('rtl/gpu/ot_gpu_tc_col.sv','rtl/v41rom/ot_v41_bmul2.sv','tools/chip_assembly/floorplans.py') and raw(BASE,p).decode()!=texts[p]:raise ValueError('source contextual mismatch '+p)
        if p=='tools/chip_assembly/floorplans.py':
            basefp=raw(BASE,p).decode()
            for which in ['q','v']:
                if selected_grid(basefp,which)!=selected_grid(texts[p],which):raise ValueError('grid source mismatch')
    checks=source_contract(texts);bd=full_lef(raw(BDREV,'results/physical_abi3/asap7/chip/abstracts/ot_gpu_bd_col/ot_gpu_bd_col.lef').decode())
    memory_abstracts={}
    for k,n in [('big','ot_sram_1r1w_1024x256_m2_r2c2'),('small','ot_sram_1r1w_128x256_m1_r2c2'),('scale','ot_sram_1r1w_256x256_m2_r2c2')]:
        memory_abstracts[k]=full_lef(raw(BASE,'physical/asap7_memory_macros/'+n+'/'+n+'.lef').decode())
    manifests={};models={}
    for model,a in attribution['models'].items():
        q=model=='qwen';L=32 if q else 16;term='results/physical_abi3/asap7/gpu/'+('w13_tc_col_terminal_20261001T2112Z' if q else 'w13_tc16_terminal_20261001T120346Z');macro='ot_gpu_tc_col' if q else 'ot_gpu_tc16'
        path='records/results/physical_abi3/asap7/chip/abstracts/'+macro+'/'+macro+'.lef';b=raw(BASE,term+'/'+path);receipt=rec(BASE,term+'/receipt.json')
        if hashlib.sha256(b).hexdigest()!=receipt['files'][path]:raise ValueError('terminal abstract pin')
        tc=full_lef(b.decode());rows=a['compact_unchanged_column_placement'];groups,nets,unused=netgroups(model,rows,{'tc':tc,'bd':bd})
        manifests[model]=dict(groups=groups,nets=nets,unconsumed_output_ports=unused)
        counts=Counter(n['family'] for n in nets.values() if n['role']=='input_weight' and not n['constant_zero']);fans=defaultdict(Counter)
        for n in nets.values():fans[n['role']][len(n['endpoints'])]+=1
        supply=[dict(pin=name,**r) for name,p in tc['pins'].items() if p['use'] in ('POWER','GROUND') for r in p['rectangles']]
        supplyarea={l:union_area([r['rect_um'] for r in supply if r['layer']==l]) for l in sorted({r['layer'] for r in supply})}
        placed_abstract_occupancy=[]
        for row in rows:
            info=tc if row['kind']=='failed_source_TC' else bd if row['kind']=='same_source_BD' else memory_abstracts[row['kind'].removeprefix('SRAM_')]
            def translate(rect):return [round(rect[i]+(row['x'] if i%2==0 else row['y']),6) for i in range(4)]
            placed_abstract_occupancy.append(dict(instance=row['name'],geometry_is_compact_model_not_actual_parent_route=True,OBS=[dict(layer=o['layer'],rect_um=translate(o['rect_um'])) for o in info['OBS']],power_rectangles=[dict(pin=p,layer=r['layer'],rect_um=translate(r['rect_um'])) for p,entry in info['pins'].items() if entry['use'] in ('POWER','GROUND') for r in entry['rectangles']]))
        oldgrid={n:(x,y) for n,x,y in selected_grid(texts['tools/chip_assembly/floorplans.py'],'q' if q else 'v')}
        moves=[]
        for row in rows:
            if row['kind']!='failed_source_TC':continue
            ox,oy=oldgrid[row['name']];disp=abs(row['x']-ox)+abs(row['y']-oy)
            moves.append(dict(instance=row['name'],old_declared_macro_origin_um=[ox,oy],new_geometric_witness_origin_um=[row['x'],row['y']],Manhattan_endpoint_displacement_bound_um=round(disp,6),wire_stage_delta_interval_fixed_unknown_other_endpoint=[-math.ceil(disp/504),math.ceil(disp/504)],old_grid_is_not_actual_SM_route=True))
        alignment=19;ff=40*L+alignment;ffarea=ff*upper['stock_cell_area_bounds']['largest_DFF_um2'];free=a['failed_source_cell_area_accounting']['unused_core_area_arithmetic_um2']
        models[model]=dict(unique_dynamic_weight_bits_by_family=dict(counts),unique_fragment_bits=sum(n['role']=='input_fragment' for n in nets.values()),unique_metadata_bits=sum(n['role']=='input_metadata' for n in nets.values()),used_output_bits=sum(n['role']=='output' for n in nets.values()),physical_macro_input_bit_incidences=sum(len(n['endpoints']) for n in nets.values() if n['role'].startswith('input')),fanout_histograms_by_role={k:dict(v) for k,v in fans.items()},constant_zero_input_bit_incidences=sum(len(n['endpoints']) for n in nets.values() if n['constant_zero']),constant_route_rule='Keep declared port incidences; source-known zeros can use local ties with max32loads/tie, priced separately. No Boolean alias credit across nonconstant bit functions.',placed_abstract_occupancy=placed_abstract_occupancy,partition_channel_demand=channel_census(nets,rows,model),actual_macro_abstract=dict(size_um=tc['size_um'],OBS=tc['OBS'],power_rectangles=supply,power_union_area_by_layer_um2=supplyarea,over_macro_M1_M6_blocked=True,unused_core_whitespace_not_visible_in_LEF=True,upper_layer_no_OBS_is_not_free_capacity=True),parent_PDN=dict(same_source_tcl_sha256=hashlib.sha256(texts['tools/chip_assembly/tcl/pdn_sm.tcl'].encode()).hexdigest(),actual_parent_route_occupancy='NOT_RETAINED',available_source='same-source Tcl rail/ring/connection declarations; archived macro M6 supply rectangles',missing_provider='W13_PARENT_SM_ROUTE_BLOCKAGES_PDN_VIAS_GRID_WITH_SOURCE_SHA',no_nominal_stripes_claimed_as_actual=True),internal_valid_control_RTL_loads=dict(v_input_register_D_loads=L+1,v_input_first_last_AND_loads=2,v_q_multiplier_valid_ports=L,v_q_u_v_delay_port=1,v_ql_per_lane_bubble_mux_select_bit_loads=16,restart_fl5_mux_select_bit_loads=32*L,physical_register_aliasing_and_slew_requires_mapped_provider=True),parent_consumed_output_RTL_loads={'Q_sov0_combiner_valid_port':1,'Q_stag0_tag_bits':16} if q else {'BD_bov0_data_mux_select_bits':128,'BD_bov0_tag_mux_select_bits':16,'BD_bov0_tin_v_OR_and_cf_AND_loads':2,'TC_fov0_tin_v_OR_and_cf_AND_loads':2,'other_subpartition_valid_and_tags':0},cut_plan=dict(fields_per_lane={'da':18,'db':18,'sign':1,'zero':1,'nonfinite':1,'valid':1},field_source='ot_v41_bmul2 dec/da/db and s1_s/s1_z/s1_nf/s1_v; cut before signed11bit s1_e add',lane_source_endpoints=[dict(lane=l,producer=f'g_lane[{l}].u_mul.da/db + a/b sign/zero/nonfinite + v',consumer=f'g_lane[{l}].u_mul.s1_a/s1_b/s1_e/s1_s/s1_z/s1_nf/s1_v',new_cut_bits=40,actual_register_coordinates='NOT_RETAINED',location_constraint='Inside same lane island, adjacent to decode outputs and s1 exponent add; use real placement boxes before selecting coordinates') for l in range(L)],alignment_added_FF={'u_f_D5_to_D6':1,'u_v_D5_to_D6':1,'u_l_LL12_to_LL13':1,'u_t_W16_D12_to_D13':16},per_lane_bank_area_upper_um2=40*upper['stock_cell_area_bounds']['largest_DFF_um2'],per_lane_new_bank_footprint_at_density45_um=[ceilgrid(math.sqrt(40*upper['stock_cell_area_bounds']['largest_DFF_um2']/.45),.054),ceilgrid(math.sqrt(40*upper['stock_cell_area_bounds']['largest_DFF_um2']/.45),.27)],bank_footprint_status='Candidate footprint only; no coordinate, whitespace or power/clock clearance proof. Source-supported lane pin anchors are in net_manifest endpoint_centers, not internal lane locations.',internal_long_channel_demand_of40L_is_not_mandatory=True,minimum_added_FF_bits=ff,previous20_alignment_bits_is_one_bit_reserve=True,FF_area_upper_um2=ffarea,unused_core_area_arithmetic_um2=free,FF_area_fraction_of_arithmetic_unused_core=ffarea/free,safe_physical_cut_location='NOT_ESTABLISHED_FROM_RETAINED_SOURCES',no_new_macro_outline_forced_by_FF_area=True,clock_assumptions={'new_clock_loads':ff,'new_valid_reset_loads':L+3,'fanout_buffer_caps_are_not_measured_needs':True,'clock_skew_and_local_CTS_provider':'W13_LANE_ISLAND_CLOCK_RESET_CAP_MINMAX_SSFF'},hold_assumptions={'known_old_FF_failure_ps':upper['failure_unchanged']['FF_hold_wns_ps'] if q else receipt.get('ff_hold_wns_ps'),'new_direct_sign_zero_nf_valid_paths_need_min_delay':True,'old_tree_bypass_hold_path_is_separate':True,'predecode_cut_alone_does_not_fix_existing_tree_bypass_hold':True,'Q_same_clock_old_endpoint_min_added_delay_required_ps':0.9053036098549683,'required_noninverting_hold_delay_expression':'FF_added_min_delay >= old_deficit + delta_capture_minus_launch_clock + explicit_guard;25ps uncertainty already included in measured deficit. Need source-bound FF library/path clocks before choosing cell count.','repair_buffer_count':'UNBOUND_ENDPOINT_MIN_DELAY_AND_CLOCK_SKEW; prior cap is a counterfactual only'},valid_fanout_warning='Identical v_q/v_ql registers can merge; RTL replicas are not proof of physical fanout replication. Carry valid locally at cut, but keep actual bubble data mask because multiplier y is not valid-gated.',minimum_cut_latency_delta=1,II_candidate_cycles=1,II_is_not_contextually_qualified=True),macro_endpoint_movement_bounds=moves,maximum_declared_to_compact_TC_endpoint_displacement_um=max(x['Manhattan_endpoint_displacement_bound_um'] for x in moves),no_sm_admission=True)
    cal=rec(BASE,'results/rtl/deepseek_hbm_complete_20261001/whole-program-calendar-r2.json');graph=rec(BASE,'results/rtl/w19_hbm_tp96_program_oreduce.json')
    flat=[(layer['layer'],o) for layer in graph['layers'] for o in layer['ops']];revdeps=defaultdict(list)
    for c in cal['operations']:
        for dep in c['dependencies']:revdeps[dep].append(c['pc'])
    events=[]
    for row in nested['explicit_BF16_matrix_events']+nested['nested_compressor_projection_events']:
        pc=row['pc'];c=cal['operations'][pc];layer,o=flat[pc]
        if (c['layer'],c['source_op_id'])!=(layer,o['id']):raise ValueError('calendar identity')
        nestedrow='dependency_after' in row
        events.append(dict(model='deepseek_v41',event_id=row['event_id'],pc=pc,layer=layer,source_op_id=o['id'],matrix_shape=row['matrix_shape'],participants=row.get('active_ranks',row.get('participants')),source_calendar_dependency_PCs=c['dependencies'],actual_graph_consumers_PCs=revdeps[pc],result_dependency_after=row.get('dependency_after', [f'pc{n}.issue_after_pc{pc}.resultvisible' for n in revdeps[pc]]),TC_drains_delta_cycles=1,old_parent_drain_cycles=row.get('shape_specific_parent_drain_cycles_structural',row.get('parent_SM_drain_from_last_issue_cycles_structural')),new_parent_drain_cycles=row.get('shape_specific_new_parent_drain_cycles_structural',row.get('new_parent_SM_drain_cycles_structural')),nested_WK_opt_in_mapping_required=nestedrow,wire_input_endpoint_ref='deepseek_v41.macro_endpoint_movement_bounds + source-visible ix/iwf producer provider',wire_output_endpoint_ref='deepseek_v41 TC y/ov/otag/fault -> col combine -> stack -> source resultvisible provider',result_visible_delta_expression='1 + EXPOSED_INPUT_READY_SHIFT(event) + OUTPUT_WIRE_STAGE_SHIFT(event)',wire_stage_expression='ceil(L_new_endpoint/504)-ceil(L_old_endpoint/504); require actual endpoint boxes and readiness slack',binding_provider_id=f'W13_DS_PC{pc}_TC_ENDPOINT_READY_AND_COMMIT',whole_broadcast_counts_used=False))
    if len(events)!=97 or len({e['event_id'] for e in events})!=97:raise ValueError('97 DS node binding')
    import qwen_hbm_complete_program as Q
    config=rec(BASE,'compiler/models/qwen3-8b/config.json');raw(BASE,'compiler/models/qwen3-8b/checkpoint_source.json') # metadata only
    qops=Q.compile_program(config=config)['instructions'];qdeps=defaultdict(list)
    for o in qops:
        for dep in o['dependencies']:qdeps[dep].append(o['id'])
    for o in qops:
        if o['opcode'] not in ('MATRIX','SCORES','PV'):continue
        events.append(dict(model='qwen',event_id=o['event_ids']['result_visible'],pc=o['id'],opcode=o['opcode'],participants=o['participants'],source_calendar_dependency_PCs=o['dependencies'],actual_graph_consumers_PCs=qdeps[o['id']],reads=o['reads'],writes=o['writes'],source_event_ids=o['event_ids'],TC_drains_delta_cycles=1,mapping_source=o['GPU_instructions'],requires_general_BF16_weight_feed_not_existing_W8_SM_decode=o['opcode']!='MATRIX',current_physical_mapping_is_not_qualified=True,wire_input_endpoint_ref='qwen macro port movement + ix/iw producer source-visible provider',wire_output_endpoint_ref='TC -> SUB4 combine -> stack -> optional row scale -> addressed commit',result_visible_delta_expression='1 + EXPOSED_INPUT_READY_SHIFT(event) + OUTPUT_WIRE_STAGE_SHIFT(event)',wire_stage_expression='ceil(L_new_endpoint/504)-ceil(L_old_endpoint/504); source-visible readiness slack required',binding_provider_id=f'W13_Q_OP{o["id"]}_TC_ENDPOINT_READY_AND_COMMIT',whole_broadcast_counts_used=False))
    retained=sorted(subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'results/physical_abi3/asap7/gpu/w13_tc_col_terminal_20261001T2112Z','results/physical_abi3/asap7/gpu/w13_tc16_terminal_20261001T120346Z'],cwd=ROOT,text=True).splitlines())
    return dict(schema='opentallas.hbm-tc-unique-net-sourceplan.v1',tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),pins=pins,source_contract_checks=checks,models=models,event_dependency_plan=events,DS_TC_nodes=97,Qwen_TC_nodes=sum(e['model']=='qwen' for e in events),Qwen_W8_parent_compatible_matrix_nodes=sum(e['model']=='qwen' and e['opcode']=='MATRIX' for e in events),Qwen_general_BF16_attention_feed_mapping_nodes=sum(e['model']=='qwen' and e['opcode']!='MATRIX' for e in events),retained_terminal_file_inventory=retained,retained_location_status='Terminal archives contain LEFs, reports, RTL and hashes, no internal DEF/ODB cell coordinate or parent routed occupancy record. Hash records are not placement data; no checkpoint payload read.',signal_constant_proofs=dict(Qwen_I8_code_domain=256,Qwen_BF16_weight_lsb_always_zero=all(i8word(c)&1==0 for c in range(256)),DS_iwq_last4blocks_high4bits_zero_in_both_FP4_FP8_modes=True,local_tie_max_fanout_assumption=32,local_tie_cells_required_Qwen=64,local_tie_cells_required_DS_BD=128,tie_cell_area_provider='Pinned stock-cell LEF upper bound; electrical maxfanout/cap must be confirmed before route admission',no_nonconstant_Boolean_alias_merge_credit=True),net_census_scope='64 Qwen TC macro boundaries;32 DS TC +32 BD boundaries. Existing RF/SIMD/glue clock/fanout not included; no full-SM claim.',net_census_interpretation='Registered bit identities and physical port incidences, excluding only source-known constants from long signal routes and unconsumed outputs. No optimization/tie placement is presumed measured. The upper per-cut bounds still require driver locations; lower shared-net crossings apply to this declared RTL identity graph and compact coordinates, not a mapped physical minimum. Boolean-equivalent bits may merge in synthesis; no credit or physical fanout guarantee is claimed without mapped metadata.',previous_upper_bounds_preserved=dict(git=GEOM,interpretation='Policy counterfactual only; no impossibility or die adoption follows'),failed_unchanged=upper['failure_unchanged'],review_gate=dict(status='SOURCEPLAN_FOR_PARENT_REVIEW_NOT_BUILD_READY',needed='Source-matched lane-island cell/clock/reset boxes and min/max path clocks, source-matched parent signal/PDN via occupancy and producer/consumer endpoints/readiness slack. Provide metadata extracts; this tool cannot select a safe in-core cell location from an opaque macro abstract.',fixed_constraints={'period_ps':833,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25},successor='Retain bubble gating and exact arithmetic; insert40bit lane predecode cut and19FF alignment; mul5->6/LL12->13; IL8/ALAT7 unchanged. Parent event plans price+1 once per result-visible drain. New signoff remains required after fully composed model and parent review.'),no_admission=True,no_RTL_PnR_retry=True,no_rate_or_die_adoption=True),manifests


def artifacts():
    model,manifest=build();packed=gzip.compress((json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)
    model['net_manifest_sha256']=hashlib.sha256(packed).hexdigest()
    return (json.dumps(model,sort_keys=True,indent=2)+'\n').encode(),packed


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output');ap.add_argument('--check');a=ap.parse_args();model,packed=artifacts()
    if a.check:
        p=Path(a.check)
        if (p/'model.json').read_bytes()!=model or (p/'net_manifest.json.gz').read_bytes()!=packed:raise SystemExit('sourceplan reproduction mismatch')
        print('PASS model/net-manifest reproduction; FAIL unchanged; physical cut/route gate open')
    elif a.output:
        p=Path(a.output);p.mkdir(parents=True,exist_ok=True)
        if any((p/n).exists() for n in ['model.json','net_manifest.json.gz']):raise SystemExit('refuse evidence overwrite')
        (p/'model.json').write_bytes(model);(p/'net_manifest.json.gz').write_bytes(packed)
    else:print(model.decode(),end='')

if __name__=='__main__':main()
