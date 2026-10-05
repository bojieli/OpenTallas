#!/usr/bin/env python3
"""Source-pinned perimeter FF strip alternative, model only; no decap credit.

New outlines, banks and boundary pins are proposals. Retained D/Q accesses
anchor geometry, not successor timing. Missing parent readiness never becomes
zero. No RTL/LEF/physical-tool output is generated.
"""
import argparse
from collections import defaultdict
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from hbm_tc_retained_placement_model import norm, pin_position
from hbm_tc_unique_net_sourceplan import full_lef, netgroups, channel_census
from hbm_tc_reservation_attribution import compact
from hbm_tc_geometry_prerequisite import ceilgrid, conflicts, capacity, SX, SY

ROOT=Path(__file__).resolve().parents[1]
PRIOR='0f5139a98dd67efdacbdbab4a0b149964dcd92dd'
SOURCE='000ba0898f5120a66d5905ccff333ebbbe28394d'
BASE='e72abea5ae169d3167dddc89543013f0e6bb3a7a'
DEST='results/uarch/hbm_tc_perimeter_strip_20261002'
RETAINED='results/uarch/hbm_tc_retained_placement_20261002'
UNIQUE='results/uarch/hbm_tc_unique_net_sourceplan_20261002'
ATTR='results/uarch/hbm_tc_reservation_attribution_20261001'
GEOM='results/uarch/hbm_tc_geometry_prerequisite_20261001'
POLICY=dict(utilization=.60,clock_leaf_load_cap=16,clock_branch_fanout_cap=4,
    hold_buffers_per_added_FF_cap=2,old_tree_hold_buffers_cap=2,signal_buffers_per_added_FF_cap=1,
    control_cells_per_lane_cap=2,alignment_control_cells_cap=2,
    boundary_power_guard_um=1.08,seam_channel_reservation_um=1.08,
    outer_row_margin_um=2.16,old_tree_hold_wire_fit_setup_limit_ps=40.,
    route_length_ratio_cases=[1.,1.25],new_clock_skew_guard_ps=40.)


def l1(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])


def pin_edge(entry,side):
    a,b,c,d=entry['rectangles'][0]['rect_um'];x,y=(a+c)/2,(b+d)/2
    distances={'W':x,'E':side-x,'S':y,'N':side-y}
    return min(distances,key=distances.get)


def cts_count(ff, leaf=16, branch=4):
    levels=[math.ceil(ff/leaf)]
    while levels[-1]>1:levels.append(math.ceil(levels[-1]/branch))
    return levels,sum(levels)


def strip_budget(lanes, stock, policy=POLICY):
    ff=40*lanes+19;levels,clock=cts_count(ff,policy['clock_leaf_load_cap'],policy['clock_branch_fanout_cap'])
    terms={
        'lane_and_alignment_FF':dict(count=ff,master='DFFASRHQNx1_ASAP7_75t_R',area_each=stock['DFFASRHQNx1_ASAP7_75t_R']),
        'CTS_buffers_cap':dict(count=clock,master='BUFx24_ASAP7_75t_R',area_each=stock['BUFx24_ASAP7_75t_R']),
        'hold_buffers_cap':dict(count=policy['hold_buffers_per_added_FF_cap']*ff+policy['old_tree_hold_buffers_cap'],master='BUFx2_ASAP7_75t_R',area_each=stock['BUFx2_ASAP7_75t_R']),
        'signal_buffers_cap':dict(count=policy['signal_buffers_per_added_FF_cap']*ff,master='BUFx2_ASAP7_75t_R',area_each=stock['BUFx2_ASAP7_75t_R']),
        'control_cells_cap':dict(count=policy['control_cells_per_lane_cap']*lanes+policy['alignment_control_cells_cap'],master='AND2x2_ASAP7_75t_R',area_each=stock['AND2x2_ASAP7_75t_R'])}
    for t in terms.values():t['area_um2']=t['count']*t['area_each']
    return dict(terms=terms,total_cell_area_cap_um2=sum(t['area_um2'] for t in terms.values()),
        FF_count=ff,clock_tree_level_counts=levels,cap_basis='explicit rejection caps priced with locked LEF cells; no measured successor count or timing claim',
        hold_cap_is_not_delay_cure=True,control_cap_is_not_logic_change=True,
        decap_replacement_credit_um2=0,extra_wire_stage_FF_not_hidden_in_base=True)


def semantic_endpoints(d,masters,lanes):
    comps={norm(c[0]):c for c in d['components'] if c[1].startswith('DFF')}
    roots=defaultdict(list)
    for n in comps:roots[n.split('$_',1)[0]].append(n)
    prefix='u.' if lanes==16 else ''
    def point(name,pin):
        c=comps[name];return dict(instance=name,pin=pin,first_access_center_um=pin_position(c,masters[c[1]],pin))
    result=[]
    for lane in range(lanes):
        stem=prefix+f'g_lane[{lane}].u_mul.'
        fields={}
        for field,width in [('s1_a',8),('s1_b',8),('s1_e',11),('s1_s',1),('s1_z',1),('s1_nf',1),('s1_v',1)]:
            pp=[]
            for bit in range(width):
                root=stem+field+(f'[{bit}]' if width>1 else '')
                names=roots[root]
                if field=='s1_v' and not names:
                    # Both source registers are identical one-cycle v_q delays
                    # with async active-low reset; synthesis retained u_v[1].
                    names=roots[prefix+'u_v.line[1]']
                if len(names)!=1:raise ValueError('semantic FF not unique '+root)
                pp.append(dict(point(names[0],'D'),semantic_source=root,
                    merged_valid_alias=field=='s1_v' and not names[0].startswith(root),
                    synthesized_synchronous_reset_mux_before_D='$_SDFF_' in names[0]))
            fields[field]=pp
        operands={}
        for field in ['w_q','x_q']:
            operands[field]=[point(roots[prefix+field+f'[{lane*16+bit}]'][0],'QN') for bit in range(16)]
        vname=roots[prefix+'v_q'][0]
        operands['v_q']=[point(vname,'QN')]
        result.append(dict(lane=lane,consumers=fields,operand_Q_anchors=operands,
            field_bindings={'da[17:10]':'s1_a[7:0] D','db[17:10]':'s1_b[7:0] D',
                'da[9:0],db[9:0]':'signed eleven-bit add -> s1_e[10:0] D; not direct pin aliases',
                'sign':'s1_s D','zero':'s1_z D','nonfinite':'s1_nf D','valid':'s1_v D'},
            actual_decode_output_coordinates='NEEDS_SAME_JOB_SYNTHESIS_SEMANTIC_NET_MAP',
            operand_mapping='a=valid-bubble-masked w_q; b=x_q; source000 RTL'))
    alignment=[]
    for unit,bit in [('u_f',5),('u_v',5),('u_l',12)]:
        n=roots[prefix+unit+f'.line[{bit}]'][0];alignment.append(point(n,'QN'))
    for bit in range(16):
        n=roots[prefix+f'u_t.genblk1.g_line.line[{176+bit}]'][0];alignment.append(point(n,'QN'))
    return result,alignment


def propose(edge,side,budget,semantics,alignment,policy=POLICY):
    horizontal=edge in ('N','S');inner=policy['boundary_power_guard_um'];guard=policy['outer_row_margin_um'];seam=policy['seam_channel_reservation_um']
    long=side-2*guard
    depth=ceilgrid(budget['total_cell_area_cap_um2']/(policy['utilization']*long)+inner+guard+seam,SY if horizontal else SX)
    outline=[side,side+depth] if horizontal else [side+depth,side]
    core_offset=[depth if edge=='W' else 0,depth if edge=='S' else 0]
    base=side if edge in ('N','E') else 0
    short_lo=base+seam+inner if edge in ('N','E') else guard
    short_hi=side+depth-guard if edge in ('N','E') else depth-seam-inner
    if short_hi<=short_lo:raise ValueError('no cell strip')
    tangent=0 if horizontal else 1
    order=sorted(semantics,key=lambda l:sum(p['first_access_center_um'][tangent] for ps in l['consumers'].values() for p in ps)/31)
    bands=[];start=guard
    for lane in order:
        end=start+long*40/budget['FF_count']
        rect=[start,short_lo,end,short_hi] if horizontal else [short_lo,start,short_hi,end]
        center=[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2]
        translated=lambda p:[p[i]+core_offset[i] for i in (0,1)]
        cons=[dict(p,translated_D_um=translated(p['first_access_center_um'])) for ps in lane['consumers'].values() for p in ps]
        sources=[dict(p,translated_Q_um=translated(p['first_access_center_um'])) for ps in lane['operand_Q_anchors'].values() for p in ps]
        # Conservative bank extent vs actual retained pin coordinates. These
        # are geometric bounds, not proof of where anonymous decode gates sit.
        corners=[[rect[0],rect[1]],[rect[0],rect[3]],[rect[2],rect[1]],[rect[2],rect[3]]]
        return_lengths=[l1(c,p['translated_D_um']) for c in corners for p in cons]
        input_lengths=[l1(c,p['translated_Q_um']) for c in corners for p in sources]
        reach=[]
        for ratio in policy['route_length_ratio_cases']:
            before=max(1,math.ceil(max(input_lengths)*ratio/504));after=max(1,math.ceil(max(return_lengths)*ratio/504))
            reach.append(dict(route_length_ratio_policy=ratio,predecode_input_reference_stages=before,return_transport_stages=after,
                extra_TC_cycles_reference=before+after-1,
                extra_FF_stage_count_above_base=before+after-2,
                interpretation='conditional route contract on operand-Q envelope and bank-to-D transport, excludes unbound decode/adder delay; not actual SS closure'))
        first_x,first_y=ceilgrid(rect[0],.054),ceilgrid(rect[1],.27)
        ff_capacity=math.floor((rect[2]-first_x)/1.404)*math.floor((rect[3]-first_y)/.27)
        if ff_capacity<40:raise ValueError('bank cannot pack forty largest FFs')
        bands.append(dict(lane=lane['lane'],bank_rect_um=rect,bank_center_um=center,FF_bits=40,
            largest_FF_rectangular_packing_capacity=ff_capacity,
            field_bindings=lane['field_bindings'],existing_semantic_D_pins=cons,existing_operand_Q_pins=sources,
            operand_Q_to_bank_Manhattan_interval_um=[min(input_lengths),max(input_lengths)],
            bank_to_semantic_D_Manhattan_interval_um=[min(return_lengths),max(return_lengths)],transport_cases=reach,
            semantic_decode_output_location=lane['actual_decode_output_coordinates']))
        start=end
    alignrect=[start,short_lo,side-guard,short_hi] if horizontal else [short_lo,start,short_hi,side-guard]
    aligncenter=[(alignrect[0]+alignrect[2])/2,(alignrect[1]+alignrect[3])/2]
    alignpaths=[dict(p,new_bank_center_um=aligncenter,old_Q_translated_um=[p['first_access_center_um'][i]+core_offset[i] for i in (0,1)],
        Manhattan_to_new_bank_um=l1(aligncenter,[p['first_access_center_um'][i]+core_offset[i] for i in (0,1)])) for p in alignment]
    return dict(id=edge,edge=edge,old_core_side_um=side,depth_um=depth,boundary_extensions_um={edge:depth},outline_um=outline,old_core_translation_um=core_offset,
        strip_cell_rect_um=[guard,short_lo,side-guard,short_hi] if horizontal else [short_lo,guard,short_hi,side-guard],
        strip_area_added_um2=side*depth,cell_area_cap_um2=budget['total_cell_area_cap_um2'],
        bank_cell_area_capacity_at_policy_um2=(short_hi-short_lo)*long*policy['utilization'],
        banks=bands,alignment_bank_rect_um=alignrect,alignment_FF_bits=19,alignment_paths=alignpaths,
        maximum_reference_TC_delta_by_ratio={str(r):max(b['transport_cases'][i]['predecode_input_reference_stages'] for b in bands)+max(b['transport_cases'][i]['return_transport_stages'] for b in bands)-1 for i,r in enumerate(policy['route_length_ratio_cases'])},
        extra_stage_rule='If a case exceeds +1, add (40L+19) FF per balanced extra stage, reprice CTS/hold/strip and prove intermediate-stage locations; current base outline cannot admit that contingency.',
        actual_latency_status='MINIMUM_ONE_ADDED_CUT; FINAL_MINMAX_AND_PARENT_READY_COSTS_UNBOUND')


def setup_reference(text,proposal,d,masters,policy=POLICY):
    start=re.search(r'Startpoint: (\S+)',text)[1];end=re.search(r'Endpoint: (\S+)',text)[1]
    lane=int(re.search(r'g_lane\[(\d+)\]',end)[1]);bank=next(b for b in proposal['banks'] if b['lane']==lane)['bank_rect_um']
    comps={norm(c[0]):c for c in d['components']};delta=proposal['old_core_translation_um']
    point=lambda n,p:[v+delta[i] for i,v in enumerate(pin_position(comps[n],masters[comps[n][1]],p))]
    src=point(start,'QN');dst=point(end,'D')
    numbers=lambda line:list(map(float,re.findall(r'-?\d+\.\d+',line)))
    cq=next(numbers(line)[-2] for line in text.splitlines() if start+'/QN ' in line)
    setup=abs(next(numbers(line)[-2] for line in text.splitlines() if 'library setup time' in line))
    corners=[[bank[0],bank[1]],[bank[0],bank[3]],[bank[2],bank[1]],[bank[2],bank[3]]]
    cases=[]
    for ratio in policy['route_length_ratio_cases']:
        lengths=[max(l1(src,c) for c in corners)*ratio,max(l1(c,dst) for c in corners)*ratio]
        allowance=833-60-cq-setup-policy['new_clock_skew_guard_ps']
        cases.append(dict(route_length_ratio_policy=ratio,critical_launch_to_bank_um=lengths[0],bank_to_critical_D_um=lengths[1],
            remaining_logic_allowance_ps_using_old_CQ_setup_and_wire_fit=[round(allowance-.5997*l,6) for l in lengths],
            bound_applies_only_to_this_retained_critical_path=True,
            eligibility='conditional per-leg allowance, not successor delay; decode/adder split mapping and new SS clocks/library still needed'))
    return dict(startpoint=start,endpoint=end,old_clkq_ps_rounded_report=cq,old_setup_ps_rounded_report=setup,
        source_Q_anchor_um=src,target_D_anchor_um=dst,cases=cases,new_clock_skew_guard_is_policy_not_measurement=True)


def seam_tracks(d,proposal,lanes,metals,rails):
    horizontal=proposal['edge'] in ('N','S');layers=['M3','M5'] if horizontal else ['M4','M6'];axis='X' if horizontal else 'Y'
    side=proposal['old_core_side_um'];lo=POLICY['outer_row_margin_um'];hi=side-lo;grid=[]
    for layer in layers:
        s=next(s for s in d['header'] if re.fullmatch(r'TRACKS '+axis+r' \d+ DO \d+ STEP \d+ LAYER '+layer+r' ;',s))
        offset,count,pitch=map(int,re.search(r'TRACKS \w (\d+) DO (\d+) STEP (\d+)',s).groups())
        # New outline keeps the declared local grid phase; original declaration
        # is the source, not proof of available tracks inside the old core.
        n=max(0,math.floor((hi*1000-offset)/pitch)-math.ceil((lo*1000-offset)/pitch)+1)
        grid.append(dict(layer=layer,source_DEF_TRACKS=s,span_um=[lo,hi],nominal_geometric_tracks=n,
            preferred_direction='VERTICAL' if horizontal else 'HORIZONTAL',available_track_lower_bound=0))
    return dict(directional_grid=grid,nominal_sum=sum(g['nominal_geometric_tracks'] for g in grid),
        full_seam_50pct_PDN_policy_reservation=capacity(hi-lo,'VERTICAL' if horizontal else 'HORIZONTAL',{k:metals[k] for k in layers},rails),
        includes_M3_inside_existing_M2_M6_routing_constraint=horizontal,
        required_new_signal_and_PDN_via_reservation=True,source_matched_parent_occupancy_available=False,
        no_track_fit_admission=True,per_lane_base_declared_crossing_bits=80,
        geometric_ceiling_not_free_tracks=True)


def project_abstract(tc,proposal):
    out=copy.deepcopy(tc);side=tc['size_um'][0];dx,dy=proposal['old_core_translation_um']
    out['size_um']=proposal['outline_um']
    for entry in out['pins'].values():
        for r in entry['rectangles']:
            a,b,c,d=r['rect_um'];center=[(a+c)/2,(b+d)/2]
            oldedge=min({'W':center[0],'E':side-center[0],'S':center[1],'N':side-center[1]},key=lambda k:{'W':center[0],'E':side-center[0],'S':center[1],'N':side-center[1]}[k])
            delta=[dx,dy]
            if entry['use'] not in ('POWER','GROUND') and oldedge in proposal['boundary_extensions_um']:
                depth=proposal['boundary_extensions_um'][oldedge]
                delta[0 if oldedge in ('E','W') else 1]+=depth if oldedge in ('E','N') else -depth
            r['rect_um']=[round(v+delta[i%2],6) for i,v in enumerate(r['rect_um'])]
    # Never issue a successor LEF or claim PDN/OBS is qualified. The entire
    # outline is an opaque external M1-M6 envelope for geometric composition.
    out['OBS']=[dict(layer='M'+str(i),rect_um=[0,0,*out['size_um']]) for i in range(1,7)]
    return out


def resident_capacity(name, proposal, stock, sources, historical, arithmetic):
    """Subtract all opaque hard outlines and halos before any resident credit.

    Disjoint halo rectangles make the area sum exact for this proposal. It is
    an upper ceiling on placeable capacity, not a free-row or channel claim.
    RTL declarations are priced explicitly; optimization is not guessed.
    """
    q=name=='qwen';NC=16 if q else 8;LEV=5 if q else 4
    halo=6 if q else 4;W,H=proposal['parent']['inventory_slot_cost_um']
    rows=proposal['parent']['placements'];core=[2.,2.,W-2.,H-2.]
    occupied=sum((min(W-2,r['x']+r['w']+halo)-max(2,r['x']-halo))*
                 (min(H-2,r['y']+r['h']+halo)-max(2,r['y']-halo)) for r in rows)
    hard=sum(r['w']*r['h'] for r in rows);ceiling=(W-4)*(H-4)-occupied
    # These exact source-width reservations exclude all hard column registers.
    # DS iwq has constant/multiplexed bits; never call declared bits a mapped
    # FF lower bound. Q double buffers and ix both exist, not one shared bank.
    terms=[('s1_w',1024 if q else 1088,'ot_gpu_sm_q.sv' if q else 'ot_gpu_sm_v.sv'),
           ('s1_tag/control',20 if q else 19,'ot_gpu_sm_q.sv' if q else 'ot_gpu_sm_v.sv'),
           ('ix',32768 if q else 25216,'ot_gpu_sm_q.sv' if q else 'ot_gpu_sm_v.sv'),
           ('decoded_weight_and_stage2_control',2067 if q else 3173,'ot_gpu_sm_q.sv' if q else 'ot_gpu_sm_v.sv'),
           ('stack_pending_data_and_seen',NC*LEV*8*34,'ot_gpu_stack.sv'),
           ('stack_metadata_delay',NC*LEV*7*16,'ot_gpu_stack.sv'),
           ('stack_valid_delay',NC*LEV*7,'ot_gpu_stack.sv'),
           ('stack_registered_outputs',NC*46,'ot_gpu_stack.sv'),
           ('combine_tag_valid_delay',NC*14*17,'ot_gpu_tree.sv'),
           ('result_registers',NC*32+14,'ot_gpu_sm_q.sv' if q else 'ot_gpu_sm_v.sv')]
    if q:terms += [('xstore_buf0_buf1',65536,'ot_gpu_xstore.sv'),('row_scale_input_and_bypass_delay',(512+12+1)+7*(512+12+1),'ot_gpu_sm_q.sv'),('scale_q',1,'ot_gpu_sm_q.sv')]
    ledger=[]
    for label,count,f in terms:
        text=sources[f];needle={'s1_w':'s1_w;', 's1_tag/control':'s1_tag;', 'ix':'ix;', 'decoded_weight_and_stage2_control':'itag;', 'stack_pending_data_and_seen':'pend_v, seen;', 'stack_metadata_delay':'u_meta', 'stack_valid_delay':'u_gv', 'stack_registered_outputs':'output reg               ov', 'combine_tag_valid_delay':'u_tag', 'result_registers':'rdata,', 'xstore_buf0_buf1':'buf0, buf1;', 'row_scale_input_and_bypass_delay':'ky_q;', 'scale_q':'scale_q;'}[label]
        loc=next(i for i,l in enumerate(text.splitlines(),1) if needle in l)
        ledger.append(dict(term=label,declared_register_bits=count,source_git=SOURCE,source_path='rtl/gpu/'+f,source_anchor_line=loc))
    bits=sum(t['declared_register_bits'] for t in ledger)
    ffmin=min(a for n,a in stock.items() if n.startswith('DFF'))
    ffmax=max(a for n,a in stock.items() if n.startswith('DFF'))
    add_count=NC*(3+LEV);mul_count=NC if q else 0
    arithmetic_proxy=add_count*arithmetic['add']['synthesis']['cell_area_um2']+mul_count*arithmetic['mul']['synthesis']['cell_area_um2']
    synth=next(v['metrics'] for k,v in historical['files'].items() if k.endswith('/1_synth.json'))
    return dict(slot_um=[W,H],core_margin_policy_um=2,hard_macro_area_um2=hard,
        hard_outline_and_halo_union_clipped_to_core_um2=occupied,
        residual_geometric_area_ceiling_um2=ceiling,usable_row_area_verified_um2=0,
        residual_cell_area_ceiling_at_50pct_policy_um2=ceiling*.5,
        resident_declaration_ledger=ledger,resident_declared_register_bits=bits,
        declaration_cell_area_interval_stock_DFF_um2=[bits*ffmin,bits*ffmax],
        declaration_interval_is_not_synthesis_or_physical_lower_bound=True,
        arithmetic_instances_outside_columns=dict(combine_FP32_add=NC*3,stack_FP32_add=NC*LEV,row_scale_FP32_mul=NC if q else 0),
        old_TT_arithmetic_area_counterfactual_um2=arithmetic_proxy,
        old_TT_arithmetic_counterfactual_qualification_transfer=False,
        declaration_plus_old_TT_arithmetic_cell_area_interval_um2=[bits*ffmin+arithmetic_proxy,bits*ffmax+arithmetic_proxy],
        residual_at_50pct_policy_after_declarations_and_TT_arithmetic_interval_um2=[ceiling*.5-bits*ffmax-arithmetic_proxy,ceiling*.5-bits*ffmin-arithmetic_proxy],
        counterfactual_is_not_actual_nonfit_or_architectural_impossibility=True,
        mapped_arithmetic_area_status='REQUIRES_PARENT_QUALIFIED_PACKAGE_BINDING; declaration FF subtotal excludes arithmetic internal FF/logic',
        historical_DS_mapped_stdcell_area_um2=synth['synth__design__instance__area__stdcell'] if not q else None,
        historical_DS_mapped_stdcell_count=synth['synth__design__instance__count__stdcell'] if not q else None,
        historical_DS_only_conditional_residual_at_50pct_um2=ceiling*.5-synth['synth__design__instance__area__stdcell'] if not q else None,
        historical_metrics_not_current_source_fit=True,
        other_residents_required=['bulk_copy non-SRAM control/tag/ring metadata','issue sequencer/barrier','mux/demux/weight decode/retirement glue','parent CTS/hold/tap/filler/PDN-via exclusions','qualified combine/stack/scale arithmetic replacements'],
        SIMD_RF_scope='128 SIMD lanes and scratch/RF are system uarch obligations; absent as instances in pinned sm_q/v tops. Parent must bind their separate macro/slot or co-resident area, ports and routes; this inventory grants no RF/SIMD credit.',
        fit_inequality='mapped_resident_cells + parent_CTS_hold_tap_reservation <= utilization * (core_area - hard_halo_union - unavailable_rows_and_channel_PDN_exclusions)',
        actual_fit_verified=False,route_readiness_verified=False,
        minimal_bounded_provider=dict(source=SOURCE,required=['hash-matched SM top/dependency sources and exact arithmetic package commits/parameters','mapped nonmacro cell histogram by hierarchy with LEF master/area and clocks, no checkpoint payload','parent ROW/site and hard/soft placement/blockage rectangles; PDN stripe/via layer bboxes','unique net_id driver/load semantic pins and placed pin rectangles for ix/iw/tag/first/last/result plus CTS insertion/minmax path summaries','97 DS and 434 Qwen graph event IDs bound to ready/commit endpoints and prior stage counts'],
            extraction_scope='existing retained text reports/DEF only; bounded streaming extraction, omit signal-route payload unrelated to named boundary families; no new synthesis, RTL or P&R',
            absent_current_parent_route_paths=['sm_q15/6_final.def','sm_v15/6_final.def'],
            sm_v12_limitation='floorplan/PDN only, no final route and mismatched TC abstract'))


def build():
    pins=[]
    def raw(path,rev=PRIOR):
        b=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT);pins.append(dict(git=rev,path=path,sha256=hashlib.sha256(b).hexdigest()));return b
    def record(path):return json.loads(raw(path))
    for helper in ['hbm_tc_retained_placement_model.py','hbm_tc_unique_net_sourceplan.py','hbm_tc_reservation_attribution.py','hbm_tc_geometry_prerequisite.py']:
        if (ROOT/'tools'/helper).read_bytes()!=raw('tools/'+helper):raise ValueError('pinned helper drift '+helper)
    retained=record(RETAINED+'/model.json');prior=record(UNIQUE+'/model.json');attribution=record(ATTR+'/model.json');geom=record(GEOM+'/model.json')
    services=record('results/uarch/hbm_tc_nested_dot_delta_20261001_r2/summary.json')
    ds_service_by_pc={r['pc']:r for r in services['explicit_BF16_matrix_events']+services['nested_compressor_projection_events']}
    platform=record(GEOM+'/platform_source.json');text=platform['files']['lef/asap7sc7p5t_28_R_1x_220121a.lef']['text']
    metals=copy.deepcopy(geom['ASAP7_directional_grid'])
    tech=platform['files']['lef/asap7_tech_1x_201209.lef']['text'];m3=re.search(r'LAYER M3\b(.*?)END M3',tech,re.S)[1]
    direction=re.search(r'DIRECTION (\w+)',m3)[1];pitch=float(re.search(r'PITCH ([\d.]+)',m3)[1]);width=float(re.search(r'WIDTH ([\d.]+)',m3)[1])
    if direction!='VERTICAL' or pitch!=.036:raise ValueError('M3 preferred-grid binding')
    metals['M3']=dict(direction=direction,pitch=pitch,width=width)
    masters={n:full_lef('MACRO '+n+body) for n,body in re.findall(r'MACRO\s+(\S+)(.*?)END\s+\1',text,re.S)}
    stock={n:math.prod(v['size_um']) for n,v in masters.items()}
    # Pin the actual model constants, without importing its large execution graph.
    uarch=raw('tools/uarch_model.py',BASE).decode()
    if not re.search(r'WIRE_REACH_SS_UM\s*=\s*504\.0',uarch):raise ValueError('wire reach drift')
    semsource=raw('rtl/v41rom/ot_v41_bmul2.sv',SOURCE).decode();tcsource=raw('rtl/gpu/ot_gpu_tc_col.sv',SOURCE).decode()
    checks=["s1_a <= da[17:10]; s1_b <= db[17:10];",'s1_e <= $signed(da[9:0]) + $signed(db[9:0]);',".a({wg, 16'd0})",'.b({x_q[16*l +: 16]']
    if not all(s in semsource+tcsource for s in checks):raise ValueError('semantic source drift')
    bd=full_lef(raw('results/physical_abi3/asap7/chip/abstracts/ot_gpu_bd_col/ot_gpu_bd_col.lef','283c3d1d9e71a3727acace329ff322ce14a928a5').decode())
    arithmetic={k:json.loads(raw('results/physical_abi3/asap7/hdc/w11_fp/'+n+'/physical.json',BASE)) for k,n in [('add','nm_fadd7'),('mul','nm_fmul7')]}
    resident_sources={f:raw('rtl/gpu/'+f,SOURCE).decode() for f in ['ot_gpu_sm_q.sv','ot_gpu_sm_v.sv','ot_gpu_stack.sv','ot_gpu_tree.sv','ot_gpu_xstore.sv']}
    historical_bytes=(ROOT/DEST/'parent_metrics_observation.json').read_bytes()
    if hashlib.sha256(historical_bytes).hexdigest()!='4bf6b4ad398cdc3e3a5042e6588585b845786b3a12696517c01d39abe7a224f3':raise ValueError('retained parent observation drift')
    historical=json.loads(historical_bytes)
    pins.append(dict(path=DEST+'/parent_metrics_observation.json',sha256=hashlib.sha256(historical_bytes).hexdigest(),kind='bounded read-only retained metrics observation'))
    manifests={};models={}
    for name,label,L in [('qwen','Qwen',32),('deepseek_v41','DS',16)]:
        d=json.loads(gzip.decompress(raw(RETAINED+'/'+label+'_placement.json.gz')));a=attribution['models'][name];side=a['failed_source_TC_outline_um'][0]
        sem,alignment=semantic_endpoints(d,masters,L);budget=strip_budget(L,stock);oldrows=a['compact_unchanged_column_placement'];grid=[(r['name'],r['x'],r['y']) for r in oldrows]
        term='w13_tc_col_terminal_20261001T2112Z' if L==32 else 'w13_tc16_terminal_20261001T120346Z';block='ot_gpu_tc_col' if L==32 else 'ot_gpu_tc16'
        tc=full_lef(raw(f'results/physical_abi3/asap7/gpu/{term}/records/results/physical_abi3/asap7/chip/abstracts/{block}/{block}.lef').decode())
        alternatives=[]
        ss_path=('results/physical_abi3/asap7/gpu/w13_tc_col_signoff_failure_20261001T2110Z/run/corner_ss_max.rpt' if L==32 else 'results/physical_abi3/asap7/gpu/w13_tc16_terminal_20261001T120346Z/corner_sessions/corner_ss_max.rpt')
        ss_text=raw(ss_path).decode()
        proposals=[propose(edge,side,budget,sem,alignment) for edge in ['W','E','N','S']]
        if L==32:
            hybrid=copy.deepcopy(proposals[2]);tabdepth=ceilgrid(2*masters['BUFx2_ASAP7_75t_R']['size_um'][0]+POLICY['boundary_power_guard_um']+POLICY['outer_row_margin_um']+POLICY['seam_channel_reservation_um'],SX)
            hybrid.update(id='N_PLUS_E_HOLD_TAB',hold_tab_edge='E',hold_tab_depth_um=tabdepth,
                hold_tab_cell_count_cap=2,hold_tab_clock_loads=0,
                hold_tab_is_dedicated_empty_outer_reservation_not_core_whitespace=True)
            hybrid['outline_um'][0]+=tabdepth;hybrid['boundary_extensions_um']['E']=tabdepth
            hybrid['strip_area_added_um2']=math.prod(hybrid['outline_um'])-side*side
            proposals.append(hybrid)
        for p in proposals:
            edge=p['edge'];halo=a['mandatory_halo_each_side_um'];slot=a['existing_slot_um']
            pitch=ceilgrid(p['outline_um'][0]+2*halo,SX)
            width=max(slot[0],ceilgrid(ceilgrid(halo,SX)+7*pitch+p['outline_um'][0]+2*halo,SX))
            rows,box=compact(p['outline_um'],bd['size_um'],{k:v['size_um'] for k,v in geom['memory_abstracts'].items()},grid,width,halo)
            if conflicts(rows,halo):raise ValueError('strip parent halo collision')
            pricedslot=[max(slot[i],box[i]) for i in (0,1)];area=math.prod(pricedslot)-math.prod(slot)
            p['parent']=dict(placements=[dict(r,kind='modeled_successor_TC' if r['kind']=='failed_source_TC' else r['kind']) for r in rows],
                bounding_box_um=box,existing_slot_um=slot,inventory_fits_existing_slot=all(box[i]<=slot[i] for i in (0,1)),
                halo_each_side_um=halo,hard_overlaps=0,halo_overlaps=0,
                inventory_slot_cost_um=pricedslot,inventory_slot_area_delta_um2=area,
                candidate_32SM_die_slot_area_delta_mm2=32*area/1e6,
                slot_cost_is='minimum contained box for this eight-column inventory policy, not global minimum or full SM; RF/glue and routed channels unbound')
            p['setup_critical_path_reference']=setup_reference(ss_text,p,d,masters)
            p['seam_directional_track_ceiling']=seam_tracks(d,p,L,metals,geom['PDN_source_parameters'])
            if L==32:
                ff=retained['models']['Qwen']['placement']['critical_paths']['ff_min']['placed_path_pins']
                add=lambda v:[v[i]+p['old_core_translation_um'][i] for i in (0,1)]
                gate=add(ff[2]['first_access_center_um']);sink=add(ff[3]['first_access_center_um']);ar=p['alignment_bank_rect_um'];repair=[(ar[0]+ar[2])/2,(ar[1]+ar[3])/2]
                if p.get('hold_tab_edge')=='E':
                    repair=[ceilgrid(side+POLICY['seam_channel_reservation_um']+POLICY['boundary_power_guard_um'],.054)+.27,ceilgrid((gate[1]+sink[1])/2-.135,.27)+.135]
                    p['hold_tab_two_BUF_cell_rect_um']=[repair[0]-.27,repair[1]-.135,repair[0]+.27,repair[1]+.135]
                direct=l1(gate,sink);detour=l1(gate,repair)+l1(repair,sink)
                p['old_tree_hold_strip_candidate']=dict(old_gate_Y_um=gate,old_sink_D_um=sink,proposed_hold_cell_bank_center_um=repair,
                    direct_Manhattan_um=direct,via_strip_Manhattan_um=detour,wire_fit_setup_cost_sensitivity_ps=(detour-direct)*.5997,
                    hold_FF_min_delay_gain='UNBOUND; geometry is not a min-delay guarantee',
                    old_tree_setup_and_new_skew_provider_required=True,hold_cells_cap=2,
                    cap_only_covers_known_endpoint_not_complete_old_min_path_inventory=True)
            alternatives.append(p)
        filtered=[p for p in alternatives if p.get('old_tree_hold_strip_candidate',{}).get('wire_fit_setup_cost_sensitivity_ps',0)<=POLICY['old_tree_hold_wire_fit_setup_limit_ps']]
        if not filtered:raise ValueError('no alternative satisfies declared hold-wire sensitivity cap; recompose')
        chosen=min(filtered,key=lambda p:(p['parent']['inventory_slot_area_delta_um2'],max(b['bank_to_semantic_D_Manhattan_interval_um'][1] for b in p['banks'])))
        rows=[dict(r,kind='failed_source_TC' if r['kind']=='modeled_successor_TC' else r['kind']) for r in chosen['parent']['placements']]
        proposed_tc=project_abstract(tc,chosen);groups,nets,unused=netgroups(name,rows,{'tc':proposed_tc,'bd':bd})
        manifests[name]=dict(groups=groups,nets=nets,unconsumed_output_ports=unused,selected_edge=chosen['edge'],selected_alternative_id=chosen['id'],abstract_is_proposed_not_qualified=True)
        moves=[];oldlut={r['name']:r for r in oldrows}
        for r in rows:
            if r['kind']!='failed_source_TC':continue
            o=oldlut[r['name']];dxy=[r['x']-o['x'],r['y']-o['y']]
            moves.append(dict(instance=r['name'],old_compact_origin_um=[o['x'],o['y']],new_proposed_origin_um=[r['x'],r['y']],
                origin_shift_um=dxy,core_translation_um=chosen['old_core_translation_um'],
                port_endpoint_displacement_upper_um=abs(dxy[0])+abs(dxy[1])+sum(chosen['old_core_translation_um'])+max(chosen['boundary_extensions_um'].values()),
                parent_readiness_credit='UNBOUND_NO_CREDIT_ADMISSIBLE'))
        seams=80*L+38+2
        # External signals moved to the new outside edge also cross its seam.
        extended={e:[n for n,entry in tc['pins'].items() if entry['use'] not in ('POWER','GROUND') and pin_edge(entry,side)==e] for e in chosen['boundary_extensions_um']}
        models[name]=dict(co_resident_parent_capacity=resident_capacity(name,chosen,stock,resident_sources,historical,arithmetic),lanes=L,replicated_columns_per_SM=64 if L==32 else 32,area_budget=budget,
            compute_and_port_contract=dict(MACs_per_cycle_per_column=L,MACs_per_cycle_per_SM=L*(64 if L==32 else 32),
                proposed_input_II_cycles=1,II_qualification_pending=True,input_w_bytes_per_cycle=2*L,input_x_bytes_per_cycle=2*L,
                input_payload_and_metadata_bits=32*L+19,output_payload_and_metadata_bits=50,
                strip_predecode_bits_per_cycle_each_direction=40*L,alignment_bits_per_cycle=19,
                byte_and_MAC_service_change=0,issue_body_cycles_change=0,IL=8,ALAT=7,mul_latency_base_proposal=6,LL_base_proposal=13,
                old_column_drain_cycles=49 if L==32 else 42,new_column_drain_base_cycles=50 if L==32 else 43),
            new_FF_per_SM=budget['FF_count']*(64 if L==32 else 32),alternatives=alternatives,
            selected_model_alternative_edge=chosen['edge'],selection_is_not_adoption=True,
            selected_model_alternative_id=chosen['id'],
            modeled_abstract=dict(size_um=chosen['outline_um'],old_signal_pins_are_projected_to_new_outer_edge=True,
                extended_signal_pins_by_edge=extended,old_M1_M6_OBS_not_removed=True,new_LEF_not_generated=True,old_power_qualification_not_transferred=True),
            seam_declared_net_demand=dict(predecode_to_D_fields=40*L,FF_Q_to_original_stage1=40*L,alignment_D_and_Q=38,clock_reset=2,
                relocated_external_boundary_pins=len(extended[chosen['edge']]),total_declared_net_incidence_cap=seams+len(extended[chosen['edge']]),
                east_hold_tab_seam_declared_incidence_cap=len(extended.get('E',[]))+2 if chosen.get('hold_tab_edge')=='E' else 0,
                local_bit_families_are_not_parent_broadcasts=True,capacity_available_lower_bound=0,
                source_status='40-bit successor port/cell reservation cap; synthesis aliases/merging not credited; parent net census separately source-unique'),
            parent_partition_channel_demand=channel_census(nets,rows,name),macro_endpoint_deltas=moves,
            maximum_proposed_port_displacement_um=max(v['port_endpoint_displacement_upper_um'] for v in moves),
            parent_PDN_occupancy=retained['parent']['occupancy'],no_parent_wire_or_ready_cost_dropped=True)
    events=[]
    for e in prior['event_dependency_plan']:
        m=models[e['model']];selected=next(a for a in m['alternatives'] if a['id']==m['selected_model_alternative_id'])
        events.append(dict(e,strip_model_ref=e['model']+'.'+selected['id'],
            source_service_binding=ds_service_by_pc[e['pc']] if e['model']=='deepseek_v41' else dict(source_event_ids=e['source_event_ids'],mapping_source=e['mapping_source'],issue_II_and_body_unchanged_by_strip=True),
            TC_delta_cases=selected['maximum_reference_TC_delta_by_ratio'],
            parent_drain_cycles_by_case={r:e['old_parent_drain_cycles']+c for r,c in selected['maximum_reference_TC_delta_by_ratio'].items()} if 'old_parent_drain_cycles' in e else {},
            composed_delta_expression='TC_STRIP_DELTA(case) + EXPOSED_INPUT_READY_SHIFT(event) + OUTPUT_COMMIT_STAGE_SHIFT(event)',
            parent_endpoint_shift_budget_um=m['maximum_proposed_port_displacement_um'],
            parent_wire_stage_delta_interval_given_fixed_unknown_other_endpoint=[-math.ceil(m['maximum_proposed_port_displacement_um']/504),math.ceil(m['maximum_proposed_port_displacement_um']/504)],
            parent_readiness_status='MISSING_PROVIDER_BLOCKS_COMPOSITION; NO_FREE_READY_SLACK',
            stage_costs_are_per_result_dependency=True,TC_plus1_replaced_not_added_twice=True))
    return dict(schema='hbm-tc-perimeter-strip-prerequisite-v1',tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        parent_evidence_git=PRIOR,source_git=SOURCE,pins=pins,policy=POLICY,models=models,event_dependency_plan=events,
        DS_event_count=sum(e['model']=='deepseek_v41' for e in events),Qwen_event_count=sum(e['model']=='qwen' for e in events),
        timing=dict(period_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,SS_transport_reference_um=504,
            wire_fit_ps_per_um=.5997,wire_fit_is_express_link_sensitivity_not_internal_TC_characterization=True,
            geometry_never_closes_logic_or_hold=True,
            setup_formula='Tclkq_SS + Tdecode_or_expadd_SS + Tnet_SS + Tsetup_SS + 60ps + (launch-capture skew) <= 833ps',
            hold_formula='Tclkq_FF_min + Tlogic_FF_min + Tnet_FF_min >= Thold_FF + 25ps + (capture-launch skew) - CRPR',
            old_Q_SS_setup_ps=-102.65510663742816,old_Q_FF_hold_ps=-0.9053036098549683,
            old_Q_hold_min_added_delay_expression='0.9053036098549683ps + delta(capture-launch skew) + explicit guard; buffer count unqualified',
            remaining='same-job semantic decode net mapping, per-leg logic delay/min-clock data and parent endpoints; no universal worst-logic budget substituted'),
        decap_plan_remains_conditional=True,no_decap_removal_or_PDN_credit=True,
        power_guard_basis='Inner 1.08um is snapped policy around source ring .3 core offset + two .288 M6 rails + .096 spacing = .972um. Outer 2.16um preserves source CORE_AREA 2um margin and retained ROW start x2.052/y2.160. Via enclosure/connection/IR/EM still need reservation/qualification. No old PDN is modified by this model.',
        failed_unchanged=prior['failed_unchanged'],previous_nonfit_upper_policy_preserved=True,
        no_admission=True,no_RTL_PnR=True,no_die_or_architecture_adoption=True,
        review_gate='Fully compose all Qwen/DS event endpoint ready/commit costs, CTS/minmax/hold and strip PDN/track reservation before any RTL/P&R.') ,manifests


def artifacts():
    model,nets=build();packed=gzip.compress(json.dumps(nets,sort_keys=True,separators=(',',':')).encode(),mtime=0)
    model['net_manifest_sha256']=hashlib.sha256(packed).hexdigest()
    return (json.dumps(model,sort_keys=True,indent=2)+'\n').encode(),packed


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    if (out/'model.json').exists():raise SystemExit('refuse committed evidence overwrite')
    model,nets=artifacts();(out/'model.json').write_bytes(model);(out/'net_manifest.json.gz').write_bytes(nets)
