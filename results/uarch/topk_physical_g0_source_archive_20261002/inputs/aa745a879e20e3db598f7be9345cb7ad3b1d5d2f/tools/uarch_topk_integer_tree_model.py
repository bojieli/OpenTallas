#!/usr/bin/env python3
"""Source-bound supplement to unified uarch_model dedicated-unit ledger.

Models only: no HDL/tool build/physical launch. Existing pinned model is read,
not edited. Structural gate areas are sums of SS library master areas, not STA
or a mapped-area prediction. Missing composed slot/timing authority refuses PR.
"""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]/'results/uarch/topk_integer_tree_revision_model_20261002'
def clog2(n):return (n-1).bit_length()
def serial_suffix(counts,width):
    mask=(1<<width)-1;a=0;out=[0]*len(counts)
    for i in range(len(counts)-1,-1,-1):out[i]=a;a=(a+counts[i])&mask
    return out

def tree_suffix(counts,width):
    """Balanced up/down tree: each CB-width addition is independently truncated."""
    if not counts or len(counts)&(len(counts)-1):raise ValueError('power-of-two bin count')
    mask=(1<<width)-1
    levels=[[x&mask for x in counts]]
    while len(levels[-1])>1:
        v=levels[-1];levels.append([(v[i]+v[i+1])&mask for i in range(0,len(v),2)])
    prefixes=[0]
    for values in reversed(levels[:-1]):
        nxt=[]
        for i,prefix in enumerate(prefixes):nxt.extend([(prefix+values[2*i+1])&mask,prefix])
        prefixes=nxt
    return prefixes

def serial_choose(counts,suffix,rr,width):
    mask=(1<<width)-1
    for b in reversed(range(len(counts))):
        if suffix[b]<rr<=((suffix[b]+counts[b])&mask):return (True,b,suffix[b])
    return (False,0,0)

def tree_choose(counts,suffix,rr,width):
    mask=(1<<width)-1
    v=[(suffix[i]<rr<=((suffix[i]+x)&mask),i,suffix[i]) for i,x in enumerate(counts)]
    while len(v)>1:v=[v[i+1] if v[i+1][0] else v[i] for i in range(0,len(v),2)]
    return v[0] if v[0][0] else (False,0,0)

def popcount_tree(bits):
    v=list(bits)
    while len(v)>1:v=[v[i]+v[i+1] for i in range(0,len(v),2)]
    return v[0]

def constants(path):
    wanted={'DFF_UM2','PRODUCT_CLOCK_HZ','UNCERTAINTY_PS','WIRE_PS_PER_UM','WIRE_OVERHEAD_PS'};out={}
    for n in ast.parse(path.read_text()).body:
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in wanted:
            out[n.targets[0].id]=ast.literal_eval(n.value)
    if set(out)!=wanted:raise ValueError('unified-model constants missing')
    return out

def gate_prices(area):
    a=area['AND2x2_ASAP7_75t_R'];o=area['OR2x2_ASAP7_75t_R'];x=area['XOR2x1_ASAP7_75t_R'];inv=area['INVx1_ASAP7_75t_R'];ff=area['DFFHQNx1_ASAP7_75t_R']
    def cla(width):
        """Explicit unbuffered parallel-carry construction; modulo-width result."""
        nodes=sum(width-(1<<i) for i in range(clog2(width)))
        # p_i XOR, g_i AND; prefix (G,P) uses AND,OR,AND; sum bits1..W-1 XOR
        return (2*width-1)*x+(width+2*nodes)*a+nodes*o
    return {'mux_bit':2*a+o+inv,'ff':ff,'AND':a,'OR':o,'XOR':x,'cla':cla}

def state_inventory(N,nmax,P,PF,DIG):
    cap=N*nmax;cb=clog2(cap+1);rb=max(1,clog2(N));wb=clog2(cap//16);rrb=max(1,clog2(cap//P));pb=clog2(P+1);fb=clog2(PF+1);sb=clog2(2*PF+1);ow=PF//16;bins=1<<DIG
    # Only retained sequential declarations, excludes automatic loop temporaries.
    rows={'candidate_score_and_ID':64*cap,'hist_input_keys':32*P,'hist_onehot':bins*P,'hist_popcounts':bins*pb,
        'hist_counts':bins*cb,'suffix_counts':bins*cb,'filter_keys_ID_pipeline':160*PF,'filter_masks':4*PF,
        'filter_prefix_counts':PF*fb,'filter_compacted_IDs':32*PF,'staging_IDs':64*PF,'public_IDs':32*PF,
        'control_and_output':1+(wb+1)+3+2*cb+32+32+clog2(32//DIG+1)+cb+3*(rrb+1)+3+2+DIG+cb+5+64+4*(rrb+9)+2*fb+cb+sb+cb+clog2(ow+1)+6+32}
    return {'CB':cb,'bits_by_register_group':rows,'storage_bits':sum(rows.values())}

def price_shape(N,nmax,P,PF,DIG,prices,u):
    if P&(P-1) or not 0<PF<=P or P%PF or N*nmax%P or nmax%16:raise ValueError('unsupported source geometry')
    bins=1<<DIG;h=clog2(P);cb=clog2(N*nmax+1);passes=32//DIG
    inventory=state_inventory(N,nmax,P,PF,DIG)
    # Register each binary popcount level; final level replaces original h2_pc.
    hist_extra_per_bin=sum((P>>l)*(l+1) for l in range(1,h))
    hist_extra=bins*hist_extra_per_bin+(h-1) # h_v replaces h2_v, account added valid stages
    # Upward sums: B-1 registers; downward internal prefixes B-2. Existing leaf suf kept.
    suffix_extra=(2*bins-3)*cb
    # Leaf predicate regs + tree payload (valid,index,pgt); final pbin/pgt reused.
    choose_width=1+DIG+cb
    choose_extra=bins*(cb+1)+bins+(bins-1)*choose_width-(DIG+cb)
    control_extra=clog2(2*DIG+DIG+3)-2
    extra=hist_extra+suffix_extra+choose_extra+control_extra
    # One level/edge throughout. Up/down latency2DIG; split sum/lower comparator then upper predicate + winner latency2+DIG.
    hist_delta=h-1;suffix_delta=2*DIG-1;choose_delta=DIG+1
    delta_per_pass=hist_delta+suffix_delta+choose_delta
    delta=passes*delta_per_pass
    hist_add_area=bins*sum((P>>l)*prices['cla'](l+1) for l in range(1,h+1))
    suffix_add_area=2*(bins-1)*prices['cla'](cb)
    choose_area=bins*3*prices['cla'](cb)+(bins-1)*(DIG+cb)*prices['mux_bit']+(bins-1)*prices['OR']
    staged_area=extra*(prices['ff']+prices['mux_bit']) # explicit DFF + hold mux, not implicit embedded memory credit
    known_area=inventory['storage_bits']*prices['ff']+staged_area+hist_add_area+suffix_add_area+choose_area
    # Entire storage instance, no lifetime alias/compiled shape reduction assumed.
    ports={'score_or_ID_load_Bpc':64,'load_ldw':1,'result_Bpc':PF*4,'command_bits':2*cb+32+1,
        'load_metadata_bits':1+max(1,clog2(N))+clog2(N*nmax//16)+1,
        'result_status_bits':clog2(PF//16+1)+2,'MACs_per_cycle':0,
        'hist_candidates_per_cycle':P,'hist_candidate_RF_read_Bpc':P*4,
        'filter_score_ID_RF_read_Bpc':PF*8,'result_words_per_cycle':PF//16,'candidate_payload_total_bytes':N*nmax*8,
        'minimum_candidate_load_cycles_at_declared_port':N*nmax//8,
        'hist_integer_add_nodes_per_active_cycle':bins*(P-1),
        'suffix_integer_add_nodes_per_command_per_pass':2*(bins-1),
        'select_key_decode_logical_fanout_per_lane':bins,
        'winner_muxes':bins-1,'winner_mux_payload_width':DIG+cb}
    tracks={'suffix_max_stage_payload_bits':bins*cb,'up_tree_first_cut_bits':(bins//2)*cb,
        'winner_first_cut_bits':(bins//2)*choose_width,'hist_first_registered_payload_bits':bins*(P//2)*2,
        'external_load_data_tracks':512,'external_result_data_tracks':PF*32,
        'actual_local_channel_capacity_tracks':None,'fit':None,'payload_count_scope':'sum of distributed stage buses, not one proven physical bisection/channel',
        'routing_layer_check':'OPEN: need source-matched fulltarget outline/channel allocation, no credit from ROM spine or historical GRT outline'}
    rows=N*nmax//P;frows=N*nmax//PF
    base_comment_cycles=passes*(rows+7)+frows+9
    dig4_comment_cycles=8*(rows+7)+frows+9
    return {'parameters':{'N':N,'NMAX':nmax,'P':P,'PF':PF,'DIG':DIG,'LDW':1,'CB':cb,'NBIN':bins},
        'replicas':1,'replica_scope':'one select instance per participating die, as source contract',
        'tensor_group_replicas':N,'whole_system_replicas':None,'replication_binding':'each die repeats gathered select; layer/stage ownership and sharing require Dewey binding, no automatic extra contexts',
        'storage':inventory,'extra_bits':{'hist':hist_extra,'suffix':suffix_extra,'choose':choose_extra,'control':control_extra,'total':extra},
        'pipeline':{'hist_levels':h,'suffix_up_down_levels':2*DIG,'choose_predicate_and_tree_levels':2+DIG,'extra_cycles_each_pass':delta_per_pass,'extra_cycles_command':delta,'no_added_external_ports':True},
        'ports':ports,'boundary_and_tracks':tracks,
        'area':{'extra_register_DFF_um2':extra*prices['ff'],'extra_register_hold_mux_um2':extra*prices['mux_bit'],
            'hist_explicit_adder_construction_um2':hist_add_area,'suffix_explicit_adder_construction_um2':suffix_add_area,'choose_explicit_construction_um2':choose_area,
            'accounted_cell_master_sum_um2':known_area,'full_instance_area_um2':None,'physical_outline_slot':None,
            'minimum_core_area_at_35pct_from_retained_state_only_um2':(inventory['storage_bits']+extra)*prices['ff']/0.35,
            'excluded_from_accounted_sum':['RF write hold muxes/decoders and read multiplexers','key barrel/equality/decode fanout','filter compare/compaction/staging muxes','clock/reset/PDN/buffers/IO/timing repair'],
            'basis':'SS master areas of explicit gate/FF constructions, structural accounting only; excludes stated whole-element costs, not mapped area/slot-fit claim'},
        'latency':{'old_source_comment_cycles':base_comment_cycles,'tree_source_comment_plus_exact_increment':base_comment_cycles+delta,'DIG4_source_comment_cycles':dig4_comment_cycles,
            'DIG4_extra_vs_DIG8':dig4_comment_cycles-base_comment_cycles,'tree_minus_DIG4_cycles':base_comment_cycles+delta-dig4_comment_cycles,
            'absolute_cycle_status':'comment formula, not measured exact command cycles; incremental pipeline counts derive from retained state sequencing, require RTL calibration',
            'delta_ns_at_1p2GHz':delta/1.2,'delta_ns_at_0p9GHz':delta/0.9,
            'per_user_token_delta':'sum(calls_on_critical_path * exact incremental cycles / actual service clock); source-program callback binding OPEN'},
        'clock':{'target_period_ps':1e12/u['PRODUCT_CLOCK_HZ'],'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,
            'CB_adder_parallel_carry_combinational_logic_levels':2*clog2(cb)+3,'hist_largest_adder_width':h+1,
            'choose_leaf':'stage0 CB modular add and lower comparator in parallel; stage1 upper comparator/predicate; delay OPEN, no chained add+compare in one stage',
            'choose_internal':'one priority mux level per edge, highest bin wins','filter_path':'unchanged source PF-sized prefix/compactor; OPEN, no suffix-only clock qualification',
            'SS_stage_delay_ps':None,'FF_hold_ps':None,'clock_or_frequency_credit':False}}

def build(base=BASE):
    base=Path(base);pins=json.loads((base/'sourcepins.json').read_text())
    for p,h in pins['inputs_sha256'].items():
        if hashlib.sha256((base/p).read_bytes()).hexdigest()!=h:raise ValueError('pin mismatch '+p)
    u=constants(base/'inputs/tools/uarch_model.py');area=json.loads((base/'inputs/liberty_cell_area_extract.json').read_text())['cells_um2'];prices=gate_prices(area)
    if prices['ff']!=u['DFF_UM2']:raise ValueError('DFF unified/library mismatch')
    shapes=[price_shape(N,n,P,PF,8,prices,u) for N,P,PF in [(4,64,64),(96,1024,256)] for n in [512,2048]]
    old=json.loads((base/'inputs/topk_endpoints.json').read_text())
    return {'schema':'UNIFIED_UARCH_TOPK_INTEGER_TREE_SUPPLEMENT_V1','sourcepins':'sourcepins.json','unified_model_binding':{'entrypoint':'tools/uarch_model.py:dedicated_ledger','constants':u,'pinned_model_unchanged':True,
            'four_design_scope':{'DeepSeek_ROM':'N4 full512/2048 select','DeepSeek_HBM':'N96 full512/2048 select; existing GPU collectives organization','Qwen_ROM':'no automatic substitution for argmax provider; preserve current compiler binding','Qwen_HBM':'same; no ROM novelty introduced'}},
        'actual_failure':{'source_commit':'0ea194879d44b81c2fc4c623641c507d6dd17fe0','scope':'N4/NMAX128/P64/DIG8 GRT only','WS_ps':old['replay_ws_ps'],'path_source':'cnt254 -> suf0, one-cycle descending 256-bin suffix; histogram/choose/filter still require context measurement'},
        'contract':{'arithmetic':'unsigned Z/(2^CB) at every addition; modular addition associative for arbitrary input words. Legal histogram total<=N*n<=CAP<2^CB.',
            'suffix_invariant':'suffix[b] = sum(count[i] for i>b) mod2^CB; tree upper/lower recurrence preserves source value for every bin',
            'choose_invariant':'predicate unchanged including modular suf+cnt. Pairwise winner gives highest-bin match, including multiple matches in illegal/wrapped count vectors. When no match, keep existing pbin/pgt unchanged (valid=false), as original loop does.',
            'filter_invariant':'unchanged rank-major ascending-global-ID candidate order, signed-zero canonicalization, NaN fault, tie quota, compaction/staging/backpressure; no FP reordering',
            'control':'freeze cnt/prefix/rr until new valid histogram pipeline drained; suffix/choose reset and valid-token sequencing required. No overlapping commands or extra contexts.'},
        'checkpoint_scope':{'status':'STRUCTURAL_SIZING_ONLY_NOT_FULL_CALLER_G0', 'shape_rows':'parameterized structural comparisons; not a qualified caller binding', 'known_ROM_binding_gap':'actual full-shape ROM caller uses NMAX2048 for runtime512 and2048, LDW4; current LDW1 port rows require correction before service admission', 'pending_comparison':'balanced combinational zero-added-stage alternative must be priced alongside staged DIG8 and existing DIG4', 'next_engineering_action':'bind compiled NMAX2048/LDW4 ROM caller and its full slot to runtime512/2048; bind actual ROM/HBM call/dependency counts, then choose balanced or staged topology with all hist/choose/filter paths priced before any RTL'}, 'shapes':shapes,'admission':{'model_sized':True,'engine_RTL_admitted':False,'physical_PR_admitted':False,'reason':['full-instance area/slot and routing-channel ownership unbound','SS/FF stage bounds missing, especially predicate and unchanged filter','Dewey actual program/service-clock critical-path call counts not yet bound'],
            'next':'Use these exact shapes/state/stage/port counts to bind source-matched full-slot and composition; then opt-in source copy/equivalence, then actual fullshape SS/FF on an active host. No undersized proxy or guessed area/clock admission.'},
        'experiments_launched':0,'source_changed':False,'current_PVE2_DRT':'untouched; PVE2/PVE3 drain-only',
        'communication_intensity':{'weight_ports':0,'load_and_return_traffic':'retained load512bits/edge + PF*32 resultbits/edge; histogram rereads P*32bits/edge and filter PF*64bits/edge; no per-op external memory roundtrip added'}}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--base',type=Path,default=BASE);args=a.parse_args();r=build(args.base)
    (args.base/'model.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps([{'parameters':s['parameters'],'extra_bits':s['extra_bits']['total'],'extra_cycles':s['pipeline']['extra_cycles_command'],'vsDIG4':s['latency']['tree_minus_DIG4_cycles']} for s in r['shapes']],indent=2))
