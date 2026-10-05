#!/usr/bin/env python3
"""Source-exact balanced quota/stable compaction successor analytical G0 model.

No RTL, synthesis, simulation or P&R. Integer ordering only; FP key code unchanged.
"""
import hashlib
import json
import math
from pathlib import Path
import uarch_topk_integer_tree_model as T
import uarch_topk_service_model as S

BASE=Path(__file__).resolve().parents[1]/'results/uarch/topk_balanced_filter_successor_model_20261002'

def exclusive_binary_prefix(bits):
    """Hillis/Steele inclusive network, registered width l+2 after level l."""
    if not bits or len(bits)&(len(bits)-1):raise ValueError('power-of-two lanes')
    if any(x not in (0,1) for x in bits):raise ValueError('binary masks')
    v=list(bits)
    for l in range(T.clog2(len(bits))):
        step=1<<l;mask=(1<<(l+2))-1
        v=[(x+(v[i-step] if i>=step else 0))&mask for i,x in enumerate(v)]
    return [0]+v[:-1],v[-1]

def serial_row(gt,eq,ids,quota,cb):
    e=0;out=[]
    for g,q,id in zip(gt,eq,ids):
        if g or (q and e<quota):out.append(id&0xffffffff)
        e+=q
    return out,max(0,quota-e)&((1<<cb)-1)

def bitonic_stages(P):
    if P<2 or P&(P-1):raise ValueError('power-of-two lanes')
    stages=[];k=2
    while k<=P:
        j=k//2
        while j:
            stages.append([(i,i^j,(i&k)==0) for i in range(P) if (i^j)>i]);j//=2
        k*=2
    return stages

def stable_compact(take,ids,mutant=None):
    P=len(take);h=T.clog2(P)
    if len(ids)!=P:raise ValueError('payload lanes')
    records=[(((0 if t else 1)<<h)|(P-1-i if mutant=='reverse_lane' else i),id&0xffffffff) for i,(t,id) in enumerate(zip(take,ids))]
    for stage in bitonic_stages(P):
        nxt=list(records)
        for a,b,ascending in stage:
            x,y=records[a],records[b]
            if (x[0]>y[0]) if ascending else (x[0]<y[0]):x,y=y,x
            nxt[a],nxt[b]=x,y
        records=nxt
    # Invalid payload is explicitly zeroed, like original OR compactor's x=0.
    return [v if not (key>>h) else 0 for key,v in records],sum(take)

def balanced_row(gt,eq,ids,quota,cb):
    pref,total=exclusive_binary_prefix(eq)
    take=[bool(g or (q and p<quota)) for g,q,p in zip(gt,eq,pref)]
    compact,n=stable_compact(take,ids)
    return compact[:n],max(0,quota-total)&((1<<cb)-1)

def public_words(row_outputs,PF,LW=16):
    """Same staged PF-ID full groups and final LW-zero-padding, no FP operations."""
    pending=[];words=[]
    for _,ids in row_outputs:
        pending.extend(ids)
        if len(pending)>=PF:
            block,pending=pending[:PF],pending[PF:]
            words.extend([block[i:i+LW] for i in range(0,PF,LW)])
        if len(pending)>=PF:raise ValueError('more than one row per emitter edge')
    if pending:
        pending.extend([0]*((-len(pending))%LW))
        words.extend([pending[i:i+LW] for i in range(0,len(pending),LW)])
    return words

def row_pipeline(rows,initial_quota,cb):
    """Exact row-order quota consumer after fixed prefix latency; valid bubbles.

    Quota is sampled at consumption, never speculatively at upstream row issue.
    Rows are (gt,eq,ids) or None. Output event includes causal input ordinal.
    """
    P=len(next(r for r in rows if r is not None)[0]);h=T.clog2(P)
    depth=len(bitonic_stages(P));q=initial_quota;pending={};outputs={};trace=[]
    for cycle in range(len(rows)+h+depth+3):
        if cycle<len(rows) and rows[cycle] is not None:pending[cycle+h]=cycle
        if cycle in pending:
            i=pending[cycle];before=q;result,q=balanced_row(*rows[i],q,cb)
            outputs[cycle+depth+1]=(i,result)
            trace.append({'input_ordinal':i,'quota_cycle':cycle,'quota_before':before,'quota_after':q,'output_cycle':cycle+depth+1})
    return [outputs[c] for c in sorted(outputs)],q,trace

def filter_price(PF,cb,prices,buf):
    h=T.clog2(PF);fb=h+1;stages=h*(h+1)//2;rw=32+fb
    eq_counts=PF*sum(range(2,h+2));eq_payload=34*PF*h
    eq_valid=h
    sort_record=(stages-1)*PF*rw
    count_internal=sum((PF>>l)*(l+1) for l in range(1,h))
    count_carrier=(stages-h)*fb
    sort_valid=stages-1
    extra=eq_counts+eq_payload+eq_valid+sort_record+count_internal+count_carrier+sort_valid
    prefix_logic=sum((PF-(1<<l))*prices['cla'](l+2) for l in range(h))
    quota_logic=PF*(prices['cla'](cb)+prices['AND']+prices['OR'])
    comparisons=(PF//2)*stages
    compare_mux=comparisons*(prices['cla'](fb)+2*rw*prices['mux_bit'])
    count_logic=sum((PF>>l)*prices['cla'](l+1) for l in range(1,h+1))
    buffers=comparisons*S.buffer_tree_nodes(2*rw)
    final_gate=32*PF*prices['AND']+PF*0.04374
    return {'PF':PF,'FB':fb,'equal_prefix_stages':h,'quota_consume_stages':1,
        'prepare_stages_reuses_f3':1,'sort_stages':stages,'extra_filter_cycles':h+stages-1,'initiation_interval_rows':1,
        'additional_bits':{'equal_prefix_count_vectors':eq_counts,'equal_prefix_ID_gt_eq_carriers':eq_payload,'equal_prefix_valid':eq_valid,
            'sort_internal_records':sort_record,'parallel_take_popcount_internal':count_internal,'sort_total_count_carrier':count_carrier,'sort_valid':sort_valid,'total':extra},
        'reused_registers':{'f2_id_take':'quota output','f3_id_take_tp':'prepare ID/take/key; f3_tp FB bits become valid/lane key','f4_c_n_v':'final sorted zero-padded IDs/count/valid'},
        'old_retained_state_credit':0,
        'logic_area_um2':{'equal_prefix_network':prefix_logic,'quota_lane_compare':quota_logic,'key_comparator_and_two_record_muxes':compare_mux,
            'parallel_take_popcount':count_logic,'sort_fanout4_buffer_construction':buffers*buf,'final_invalid_payload_zero':final_gate},
        'network_counts':{'prefix_add_nodes':sum(PF-(1<<l) for l in range(h)),'sort_compare_exchange_nodes':comparisons,'sort_buffers':buffers},
        'new_combinational_stage_scope':{'prefix':'one narrow integer CLA per registered level','quota':'CB comparison and saturating subtraction in parallel; one feedback edge, actual SS/FF unknown',
            'sort':'one FB key comparison then two record muxes per edge; no FP compare or ID arithmetic','final':'one comparison/mux plus explicit invalid-output zero'},
        'bounds':{'largest_prefix_adder_width':fb,'quota_feedback_width':cb,'sort_compare_width':fb,
            'comparator_select_fanout_sinks':2*rw,'record_source_fanout':'constant-neighbor compare/mux consumers per stage, replacing triangular PF fanout',
            'record_stage_payload_bits':PF*rw,'clock_or_SS_FF_qualification':False}}

def complete_logic_allowances(row,prices,buf):
    """Explicit source cones omitted by prior partial ledger; not mapped estimate."""
    p=row['compiled'];cap=p['N']*p['NMAX'];pf=p['PF'];cb=p['CB'];wb=T.clog2(cap//16)
    eq=lambda w:w*prices['XOR']+(w-1)*prices['OR']
    # Selection-control widths, address arithmetic, masks, load-key coding.
    control_bits=row['base_state_bits']-64*cap
    rrb=max(1,T.clog2(cap//p['P']));fb=T.clog2(pf+1);sb=T.clog2(2*pf+1)
    # Individually identified source control arithmetic outside already priced
    # histogram accumulators, filter quota/ID add, and prefix/sort networks.
    operations={
        'go_n_gt_NMAX':cb,'go_k_gt_nN':32,'go_n_times_N':32,
        'hist_row_increment':rrb+1,'pick_rr_minus_pgt':cb,
        'pick_pass_increment':T.clog2(5),'pick_sh_and_sh_minus_DIG':6,
        'filter_frow_increment':rrb+9,'filter_frr_increment':rrb+9,
        'filter_fpr_minus_one':rrb+9,'filter_rank_base_plus_stride':32,
        'output_k_plus_LW_minus_one':cb,'append_m_plus_f4_n':sb,
        'emit_m_ge_PF':sb,'emit_m_plus_LW_minus_one':sb,
        'emit_outw_left_minus_w':cb,'emit_m_minus_wLW':sb,
        'emit_m_ge_wLW':sb,
    }
    predicates={'go_k_zero':cb,'go_n_zero':cb,'go_nN_mod_P_zero':T.clog2(p['P']),
        'go_n_mod_PF_zero':T.clog2(pf),'hist_row_equals_nrow':rrb+1,
        'pick_pk_zero':2,'pick_pk_one':2,'pick_pk_two':2,'pick_pass_last':T.clog2(5),
        'filter_frow_equals_nfch':rrb+9,'filter_frr_equals_fpr_minus_one':rrb+9,
        'append_f4_n_zero':fb,'append_f4_n_equals_PF':fb,'emit_outw_left_equals_w':cb,
        'drain_stn_zero':sb}
    return {'candidate_word_address_decode':(cap//16)*(eq(wb)+2*prices['AND']),
        'load_order_key_and_NaN_detection':p['LDW']*16*(64*prices['mux_bit']+32*0.04374+eq(32)+eq(8)+22*prices['OR']),
        'load_variable_rank_stride_address':p['LDW']*((T.clog2(p['N'])+1)*prices['cla'](wb+T.clog2(p['N'])+1)),
        'candidate_data_buffer_tree':512*p['LDW']*S.buffer_tree_nodes(cap//(16*p['LDW']))*buf,
        'staging_and_output_masks':(64*pf+32*pf)*(T.clog2(2*pf)+1)*prices['mux_bit']+96*pf*prices['AND'],
        'other_declared_register_hold_allowance':(control_bits-cb)*prices['mux_bit'], # eq_left hold already in shared cone
        'control_compare_add_and_counter_construction':sum(prices['cla'](w) for w in operations.values()),
        'control_zero_equal_and_mode_predicates':sum(eq(w) for w in predicates.values())}

def build(base=BASE):
    base=Path(base);pins=json.loads((base/'sourcepins.json').read_text())
    raw=(S.BASE/'artifact_manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=pins['prior_service_artifact_manifest_sha256']:raise ValueError('service manifest changed')
    for p,h in json.loads(raw).items():
        if hashlib.sha256((S.BASE.parents[2]/p).read_bytes()).hexdigest()!=h:raise ValueError('service artifact changed '+p)
    if hashlib.sha256((base/'no_ROM_ECC_calendar_handoff.json').read_bytes()).hexdigest()!=pins['no_ROM_ECC_calendar_handoff_sha256']:raise ValueError('no ECC policy pin changed')
    source=S.build();rawprices=json.loads((S.BASE/'inputs/cell_prices.json').read_text())['cells_um2'];prices=T.gate_prices(rawprices);buf=rawprices['BUFx4_ASAP7_75t_R']
    rows=[]
    for prior in source['shapes']:
        if prior['kind']!='DIG8_staged':continue
        p=prior['compiled'];f=filter_price(p['PF'],p['CB'],prices,buf)
        old=prior['area']['shared_source_construction']['area_um2_by_cone']
        replaced=['filter_equal_quota_serial_prefix_and_compare','filter_take_serial_prefix','filter_triangular_compactor']
        retained={k:v for k,v in old.items() if k not in replaced}
        # Prior compactor-only ID fanout tree is removed exactly once.
        old_nodes=prior['area']['shared_source_construction']['buffer_nodes_by_cone']['compactor_ID']
        retained['explicit_fanout4_buffer_construction']-=old_nodes*buf
        extra=f['additional_bits']['total'];ff_bits=prior['base_state_bits']+prior['additional_state_bits']+extra
        allowances=complete_logic_allowances(prior,prices,buf)
        logic=prior['area']['integer_logic_construction_um2']+sum(retained.values())+sum(f['logic_area_um2'].values())+sum(allowances.values())
        holds=prior['area']['extra_pipeline_hold_mux_um2']+extra*prices['mux_bit']
        cell=ff_bits*prices['ff']+holds+logic
        # Proposed reservation is a 50% construction proxy, not actual hardened fit.
        proposed=cell/0.5/1e6
        rows.append({'compiled':p,'runtime':prior['runtime'],'filter':f,'state_bits':ff_bits,'added_state_bits_vs_original':prior['additional_state_bits']+extra,
            'cycle_envelope':prior['source_select_cycle_upper_envelope']+f['extra_filter_cycles'],
            'extra_cycles_vs_original_DIG8':prior['added_cycles_vs_same_DIG8_baseline']+f['extra_filter_cycles'],
            'ports':prior['ports'],'area':{'FF_um2':ff_bits*prices['ff'],'hold_mux_um2':holds,'integer_hist_suffix_choice_logic_um2':prior['area']['integer_logic_construction_um2'],
                'retained_shared_cones_um2':retained,'replaced_prior_cones':replaced,'other_source_construction_allowances_um2':allowances,
                'accounted_cell_master_sum_um2':cell,'proposed_source_50pct_proxy_core_mm2':proposed,
                'basis':'explicit source gate/FF construction, not mapped area. Allowances are declared rather than hidden; no embedded/alias credit. Clock/PG/repair and final whole-instance netlist audit remain open.'},
            'replicas_per_participating_group':p['N'],'system_replicas':None,
            'routing':{'sort_stage_distributed_bits':p['PF']*(32+f['FB']),'equal_prefix_max_distributed_bits':p['PF']*(34+f['FB']),
                'external_load_and_output_tracks':prior['ports']['load_bits_per_edge']+prior['ports']['result_bits_per_edge'],
                'histogram_256bin_decode_fanout':'same explicit source construction remains priced; no clock exemption',
                'actual_translated_channel_capacity':None,'scope':'distributed buses and external boundary bits; not an asserted physical bisection or routed fit'},
            'clock':{'period_ps':833,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,'SS_FF_closed':False,
                'open_context':'hist decode/carry, quota feedback, key compare+mux, RF read, staging mask/append, CTS/hold all require source-sized context'}})
    totals={}
    for N in [4,96]:
        selected=[x for x in rows if x['compiled']['N']==N];by_n={x['runtime']['n']:x for x in selected}
        calls=source['source_service_binding']['ROM']['calendar_calls'] if N==4 else source['source_service_binding']['HBM']['calendar_calls']
        delta=sum(by_n[x['runtime_n'] if N==4 else x['k']]['extra_cycles_vs_original_DIG8'] for x in calls)
        totals['ROM' if N==4 else 'HBM_conditional_same_provider']={'calls':len(calls),'added_cycles_per_position':delta,'added_ns_at_policy_1p2GHz':delta/1.2,
            'cost_relative_to_existing_DIG4_cycles':delta-source['service_composition']['DIG4_existing']['ROM_added_serial_service_cycles_per_position' if N==4 else 'HBM_added_serial_service_cycles_per_position_if_same_provider'],
            'full_token_latency_credit':False}
    slot=source['slot_binding']['reservation'];bbox=slot['bbox_DBU'];width=(bbox[2]-bbox[0])/1000
    rom=next(x for x in rows if x['compiled']['N']==4)
    required_height=rom['area']['proposed_source_50pct_proxy_core_mm2']*1e6/width
    slotplan={'existing':slot,'proposed_same_width_um':width,'proposed_proxy_height_um':required_height,
        'proposed_bbox_DBU':[bbox[0],bbox[1],bbox[2],bbox[1]+math.ceil(required_height*1000)],
        'additional_proxy_area_mm2':rom['area']['proposed_source_50pct_proxy_core_mm2']-slot['area_mm2'],
        'additional_height_um':required_height-(bbox[3]-bbox[1])/1000,'already_included_candidate_memory_bits':524288,
        'containment_rule':'replace whole existing selector rectangle once, not add candidate storage twice; move/reconcile affected adjacent controller and attention/hub route reservations',
        'owner_accepted':False,'translated_routing_clock_PG_fit':False}
    # Check the concrete revised rectangles against all retained known services.
    reticle=json.loads((S.BASE/'inputs/reticle_model_r4.json').read_text())
    controller=next(x for x in reticle['source_service_rectangles'] if x['name']=='PROSPECTIVE_COMMON_CONTROLLER_CUT')
    cbbox=controller['bbox_DBU'];new_bottom=slotplan['proposed_bbox_DBU'][3]
    moved_controller=dict(controller,bbox_DBU=[cbbox[0],new_bottom,cbbox[2],new_bottom+cbbox[3]-cbbox[1]])
    changed=[dict(slot,name='PROPOSED_COMPLETE_TOPK_SELECTOR',bbox_DBU=slotplan['proposed_bbox_DBU'],area_mm2=rom['area']['proposed_source_50pct_proxy_core_mm2']),moved_controller]
    others=[x for x in reticle['source_service_rectangles'] if x['name'] not in ['X_SEL_TOPK_STORE','PROSPECTIVE_COMMON_CONTROLLER_CUT']]
    overlaps=[]
    for a in changed:
        for b in others:
            aa=a['bbox_DBU'];bb=b['bbox_DBU'];dx=min(aa[2],bb[2])-max(aa[0],bb[0]);dy=min(aa[3],bb[3])-max(aa[1],bb[1])
            if dx>0 and dy>0:overlaps.append({'a':a['name'],'b':b['name'],'area_mm2':dx*dy/1e12})
    slotplan['known_service_overlay']={'revised_rectangles':changed,'positive_area_overlaps':overlaps,
        'known_service_only_no_overlap':not overlaps,'ownership_scope':'source retained service rectangles only; unknown outside-service allocations are NOT assumed free. Owner must bind containment/exclusions, channels and clock/PG.',
        'selector_budget_delta_mm2_per_die':slotplan['additional_proxy_area_mm2'],
        'TP4_group_area_delta_mm2_if_four_services':4*slotplan['additional_proxy_area_mm2'],
        'whole_system_area_delta_mm2':None}
    return {'schema':'TOPK_BALANCED_FILTER_STAGED_DIG8_SUCCESSOR_G0_V1','sourcepins':'sourcepins.json','shapes':rows,'slot_proposal':slotplan,'composition':totals,
        'exact_contract':{'quota':'consume all row equal flags in source row order after prefix pipeline; saturate eq_left by row total, valid bubbles do not consume quota',
            'compaction':'sort unsigned(valid-first,original-lane) key; preserve original rank-major lane order, ID payload unchanged modulo32. Invalid payload zero.',
            'FP':'original signedzero/NaN/Inf/key conversion and threshold equality unchanged','row_II':1,'drain':'all new prefix/sort/count valid carriers included in fpipe; no done before last public output and empty staging',
            'reset':'reset every new valid carrier; no phantom quota or output after async reset; old busy/fault/public contract preserved','tag':'no new external tag/port; row ordinal internal causal order, no extra command contexts'},
        'no_ROM_ECC_source_calendar':json.loads((base/'no_ROM_ECC_calendar_handoff.json').read_text()),
        'four_design_scope':source['source_service_binding']['Qwen_ROM_and_HBM'],
        'G0':{'engine_RTL_admitted':False,'PR_admitted':False,'decision':'MODEL_SIZED_SUCCESSOR_WAIT_FULL_SLOT_AND_CONTEXT_REVIEW',
            'next_action':'Archimedes reconciles this complete proposed selector rectangle, adjacent displacement and translated routes/clock/PG; Maxwell binds serial caller residence; independently review feedback/pipeline exactness then source-bound G0. No RTL before that decision.',
            'missing':['accepted full selector reservation/slot and routed channel allocation','source-construction whole-instance and SS-stage arc/context review','HBM full2048 GPU provider ownership/ACK leases'],
            'mandatory_correctness_scope':'repair original unclosing comb chains; no optimization/adoption/frequency credit'},
        'RTL_or_PR_launched':False,'original_records_unchanged':True,'PVE2_PVE3':'drain-only, no new jobs/restarts'}

if __name__=='__main__':
    r=build();(BASE/'model.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps({'slot':r['slot_proposal'],'composition':r['composition'],'G0':r['G0']},indent=2))
