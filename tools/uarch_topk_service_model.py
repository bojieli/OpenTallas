#!/usr/bin/env python3
"""Added source/caller supplement: structural G0 decision, never hardware credit."""
import ast
import hashlib
import json
import math
from pathlib import Path
import uarch_topk_integer_tree_model as T

BASE = Path(__file__).resolve().parents[1] / 'results/uarch/topk_integer_tree_service_model_20261002'

def assignment(path, name):
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Tuple):
            names=[t.id for t in node.targets[0].elts if isinstance(t,ast.Name)]
            if name in names:return ast.literal_eval(node.value)[names.index(name)]
    raise ValueError('source assignment absent: '+name)

def buffer_tree_nodes(sinks, radix=4):
    """One explicit fanout<=4 replication topology; no drive/delay qualification."""
    total=0
    while sinks>radix:
        sinks=math.ceil(sinks/radix);total+=sinks
    return total

def shared_logic(N,nmax,P,PF,DIG,prices,buf):
    cap=N*nmax; cb=T.clog2(cap+1);fb=T.clog2(PF+1);nr=cap//P;bins=1<<DIG
    eq=lambda w: w*prices['XOR']+(w-1)*prices['OR']
    pairs=PF*(PF+1)//2
    # Each listed cone has its own declared source consumer. No sharing/alias credit.
    areas={
        'candidate_write_hold_muxes':64*cap*prices['mux_bit'],
        'hist_RF_score_read_mux':32*P*(nr-1)*prices['mux_bit'],
        'filter_RF_score_and_ID_read_mux':64*PF*(cap//PF-1)*prices['mux_bit'],
        'hist_key_two_32bit_barrels':2*32*5*P*prices['mux_bit'],
        'hist_prefix_match':P*eq(32),
        'hist_bin_decode':P*bins*(eq(DIG)+prices['AND']),
        'hist_accumulate':bins*prices['cla'](cb),
        'filter_compare_and_global_ID_add':PF*(prices['cla'](32)+eq(32)+prices['cla'](32)),
        'filter_equal_quota_serial_prefix_and_compare':PF*(prices['cla'](fb)+prices['cla'](cb)+prices['AND']+prices['OR']),
        'filter_equal_quota_subtract_and_hold':prices['cla'](cb)+cb*prices['mux_bit'],
        'filter_take_serial_prefix':PF*prices['cla'](fb),
        'filter_triangular_compactor':pairs*(eq(fb)+prices['AND']+32*prices['AND'])+32*(pairs-PF)*prices['OR'],
        'staging_variable_word_append_and_shift':64*PF*(T.clog2(2*PF)+T.clog2(PF//16+1))*prices['mux_bit']+64*PF*prices['OR'],
    }
    fanouts={'hist_digit_bit_sinks':bins,'filter_threshold_bit_sinks':2*PF,
             'filter_prefix_bit_sinks_max':PF,'compactor_ID_bit_sinks_max':PF,
             'candidate_load_enable_sinks_max':32*16,'candidate_address_row_sinks':nr}
    trees={'hist_digit':P*DIG*buffer_tree_nodes(bins),
           'filter_threshold':32*buffer_tree_nodes(2*PF),
           'compactor_ID':32*sum(buffer_tree_nodes(i+1) for i in range(PF)),
           'candidate_write_enable':(cap//16)*buffer_tree_nodes(32*16)}
    areas['explicit_fanout4_buffer_construction']=sum(trees.values())*buf
    return {'area_um2_by_cone':areas,'sum_um2':sum(areas.values()),'compactor_lane_slot_pairs':pairs,
            'fanout_sinks':fanouts,'buffer_nodes_by_cone':trees,
            'unchanged_filter_depth':{'equal_quota_serial_additions':PF,'take_prefix_serial_additions':PF,
                                      'OR_reduction_can_balance_depth':T.clog2(PF),'stages_added':0},
            'scope':'explicit unoptimized gate constructions, not mapped area or an area lower bound. Candidate memory FF bits alone give the rigorous state lower bound.',
            'still_excluded':['row/bank/address and NaN/control decode','other register enables and reset trees','clock/PDN/route/timing repair','variable masks and output padding/control'],
            'buffer_scope':'fanout4 topology using retained SS BUFx4 master; actual slew/load/capacity and full fanout audit remain unqualified'}

def variant(N,nmax,n,P,PF,ldw,kind,prices,u,buf):
    dig=4 if kind=='DIG4_existing' else 8
    s=T.price_shape(N,nmax,P,PF,dig,prices,u)
    extra=s['extra_bits']['total'] if kind=='DIG8_staged' else 0
    delta=s['pipeline']['extra_cycles_command'] if kind=='DIG8_staged' else 0
    inv=s['storage']; a=s['area']; shared=shared_logic(N,nmax,P,PF,dig,prices,buf)
    integer_logic=sum(a[k] for k in ['hist_explicit_adder_construction_um2','suffix_explicit_adder_construction_um2','choose_explicit_construction_um2'])
    # DIG4 keeps serial source topology: separate serial adder chains, not the balanced replacement.
    if kind=='DIG4_existing':
        bins=1<<dig;cb=s['parameters']['CB']
        integer_logic=bins*(P-1)*prices['cla'](T.clog2(P+1))+(bins-1)*prices['cla'](cb)+bins*3*prices['cla'](cb)+(bins-1)*(dig+cb)*prices['mux_bit']
    bound=(32//dig)*(N*n//P+7)+N*n//PF+9+delta
    return {'kind':kind,'compiled':dict(s['parameters'],LDW=ldw),'runtime':{'n':n,'k_for_this_service':n},
        'base_state_bits':inv['storage_bits'],'additional_state_bits':extra,'candidate_memory_bits':64*N*nmax,
        'added_cycles_vs_same_DIG8_baseline':delta if dig==8 else bound-(4*(N*n//P+7)+N*n//PF+9),
        'source_select_cycle_upper_envelope':bound,'absolute_latency_scope':'uninterrupted source state-machine envelope; filter tail depends on selected-lane positions, not a measured candidate runtime',
        'stages':{'hist':T.clog2(P) if kind=='DIG8_staged' else 1,'suffix':2*dig if kind=='DIG8_staged' else 1,'choose':dig+2 if kind=='DIG8_staged' else 1,'filter':6},
        'ports':{'load_bits_per_edge':512*ldw,'load_B_per_edge':64*ldw,'minimum_accepted_load_edges_scores_plus_IDs':2*N*n//(16*ldw),
                 'result_bits_per_edge':32*PF,'result_B_per_edge':4*PF,'hist_read_B_per_edge':4*P,'filter_read_B_per_edge':8*PF,'MACs_per_cycle':0,'new_ports':0},
        'area':{'FF_master_um2':(inv['storage_bits']+extra)*prices['ff'],
                'integer_logic_construction_um2':integer_logic,'extra_pipeline_hold_mux_um2':extra*prices['mux_bit'],
                'shared_source_construction':shared,
                'accounted_construction_cell_um2':(inv['storage_bits']+extra)*prices['ff']+integer_logic+extra*prices['mux_bit']+shared['sum_um2'],
                'candidate_memory_only_core_mm2_at_35pct':64*N*nmax*prices['ff']/0.35/1e6,
                'retained_state_core_mm2_at_source_50pct':(inv['storage_bits']+extra)*prices['ff']/0.50/1e6,
                'retained_state_core_mm2_at_35pct':(inv['storage_bits']+extra)*prices['ff']/0.35/1e6},
        'combinational_depth':{'suffix_CB_add_levels':2*dig if kind=='DIG8_balanced_comb' else (1 if kind=='DIG8_staged' else (1<<dig)-1),
                              'hist_add_levels':T.clog2(P) if kind!='DIG4_existing' else P-1,
                              'winner_mux_levels':dig if kind=='DIG8_balanced_comb' else (1 if kind=='DIG8_staged' else (1<<dig)-1)},
        'clock':{'target_period_ps':1e12/u['PRODUCT_CLOCK_HZ'],'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,'closed':False,
                 'filter_context':'unchanged serial quota/prefix and triangular compaction prevent suffix-only SS/FF claims'},
        'tracks':dict(s['boundary_and_tracks'],external_load_data_tracks=512*ldw),'system_replicas':None}

def build(base=BASE):
    base=Path(base);pins=json.loads((base/'sourcepins.json').read_text())
    for p,h in pins['inputs_sha256'].items():
        if hashlib.sha256((base/p).read_bytes()).hexdigest()!=h:raise ValueError('pin mismatch '+p)
    if hashlib.sha256(Path(T.__file__).read_bytes()).hexdigest()!=pins['structural_generator_sha256']:raise ValueError('structural generator changed')
    if hashlib.sha256((T.BASE/'model.json').read_bytes()).hexdigest()!=pins['structural_model_sha256']:raise ValueError('structural model changed')
    T.build() # verifies retained structural package pins
    prices_raw=json.loads((base/'inputs/cell_prices.json').read_text())['cells_um2'];prices=T.gate_prices(prices_raw)
    u=T.constants(T.BASE/'inputs/tools/uarch_model.py');buf=prices_raw['BUFx4_ASAP7_75t_R']
    dma=(base/'inputs/rtl/chip/ot_w15_coll_dma.sv').read_text()
    die=(base/'inputs/rtl/chip/ckvsel/ot_chip_v41x_die.sv').read_text()
    core=(base/'inputs/rtl/hdc/v41x/ckvsel/ot_hdc_core_v41x.sv').read_text()
    for text,fragments in [(dma,['TK_NMAX = 2048','TK_DIG = 8','LDW(GW == 4 ? N : 1)','if (tk_done) begin busy <= 0']),
                           (die,['CL_GW = FULL_SHAPE ? 4 : 1','.TOPK(FULL_SHAPE)','.clk(clk), .rst_n(rn)']),
                           (core,['S_COLL_WAIT: if (!coll_busy)','(&idles) && !coll_busy'])]:
        if not all(f in text for f in fragments):raise ValueError('caller binding changed')
    shapes=[variant(N,2048,n,P,PF,ldw,k,prices,u,buf) for N,P,PF,ldw in [(4,64,64,4),(96,1024,256,1)] for n in [512,2048] for k in ['DIG8_balanced_comb','DIG8_staged','DIG4_existing']]
    reticle=json.loads((base/'inputs/reticle_model_r4.json').read_text())
    slot=next(x for x in reticle['source_service_rectangles'] if x['name']=='X_SEL_TOPK_STORE')
    hierarchical=json.loads((base/'inputs/reticle_hierarchical.json').read_text())
    if 'at50pct placement' not in json.dumps(hierarchical):raise ValueError('reticle placement basis changed')
    if hashlib.sha256((base/'inputs/rtl/chip/ot_coll_topk_merge.sv').read_bytes()).hexdigest()!=hashlib.sha256((T.BASE/'inputs/rtl/chip/ot_coll_topk_merge.sv').read_bytes()).hexdigest():raise ValueError('selector source changed')
    rom=[s for s in shapes if s['compiled']['N']==4]
    comparisons=[{'kind':s['kind'],'runtime_n':s['runtime']['n'],'slot_mm2':slot['area_mm2'],
                  'candidate_memory_only_required_core_mm2_at_35pct':s['area']['candidate_memory_only_core_mm2_at_35pct'],
                  'shortfall_mm2_at_35pct':s['area']['candidate_memory_only_core_mm2_at_35pct']-slot['area_mm2'],
                  'state_only_utilization_required':s['area']['FF_master_um2']/1e6/slot['area_mm2'],
                  'retained_state_required_core_mm2_at_source_50pct':s['area']['retained_state_core_mm2_at_source_50pct'],
                  'shortfall_state_only_mm2_at_source_50pct':s['area']['retained_state_core_mm2_at_source_50pct']-slot['area_mm2'],
                  'fit_source_50pct':s['area']['retained_state_core_mm2_at_source_50pct']<=slot['area_mm2'],
                  'state_only_required_height_um_at_reserved_width_source_50pct':s['area']['retained_state_core_mm2_at_source_50pct']*1e6/((slot['bbox_DBU'][2]-slot['bbox_DBU'][0])/1000),
                  'fit_35pct':False} for s in rom]
    program=json.loads((base/'inputs/hbm_source_program.json').read_text())
    calls=[o for layer in program['layers'] for o in layer['ops'] if o['kind']=='topk_merge' and o['what']!='argmax']
    if len(calls)!=9 or [o['k'] for o in calls].count(2048)!=1:raise ValueError('program service demand changed')
    idx=assignment(base/'inputs/tools/hdc_replay_v41.py','IDX_SRC')
    if idx!=[2,8,14,20,24,28,32,36]:raise ValueError('ROM source index calendar changed')
    calendar=json.loads((base/'inputs/hbm_calendar_projection.json').read_text())
    if [x['source_op'] for x in calendar['instructions'] if x['source_op']['what']!='argmax']!=calls:raise ValueError('native calendar/source call join changed')
    rom_calls=[{'layer':l,'runtime_n':512,'k':512,'producer':'local top-512 selected scores and local IDs','consumer':'SELG -> selected KV gather','dependency':'blocking COLL request; successor fetch waits for coll_busy low'} for l in idx]
    rom_calls.append({'layer':20,'runtime_n':2048,'k':2048,'producer':'local candidate block maxima/scores and IDs','consumer':'CAND -> mask at subsequent layers','dependency':'same blocking COLL request'})
    rom_calls.sort(key=lambda c:c['layer']) # stable: source L20 indexer precedes candidates
    totals={}
    for kind in ['DIG8_balanced_comb','DIG8_staged','DIG4_existing']:
        rom_by_n={s['runtime']['n']:s for s in rom if s['kind']==kind}
        hbm_by_n={s['runtime']['n']:s for s in shapes if s['compiled']['N']==96 and s['kind']==kind}
        rd=sum(rom_by_n[c['runtime_n']]['added_cycles_vs_same_DIG8_baseline'] for c in rom_calls)
        hd=sum(hbm_by_n[c['k']]['added_cycles_vs_same_DIG8_baseline'] for c in calls)
        totals[kind]={'ROM_added_serial_service_cycles_per_position':rd,'ROM_added_ns_at_policy_1p2GHz':rd/1.2,
                      'HBM_added_serial_service_cycles_per_position_if_same_provider':hd,'HBM_added_ns_at_policy_1p2GHz_if_same_provider':hd/1.2,
                      'HBM_six_verify_positions_added_ns_if_serial_same_provider':6*hd/1.2,
                      'scope':'source service residence increments; transport/load gaps and actual overlap are not measured, no full-token rate claim'}
    return {'schema':'TOPK_FULL_COMPILED_SERVICE_G0_V1','sourcepins':'sourcepins.json','structural_dependency_commit':pins['structural_dependency_commit'],
        'shapes':shapes,'source_service_binding':{'ROM':{'compiled_N':4,'compiled_NMAX':2048,'LDW':4,'P':64,'PF':64,'DIG':8,'replicas_per_TP_group':4,
             'runtime_counts':[512,2048],'calendar_calls':rom_calls,'command_contexts':1,
             'storage_lifetime':'one command: accepted gathered scores/IDs remain resident through all radix passes and final filter/drain; release after tk_done. Next command overwrites only after previous busy clears; no inter-command alias credit' ,'release':'tk_done clears DMA busy; core waits coll_busy low; output pulses write VM4 synchronously, no downstream ACK port',
             'deadline':'consumer dependent and blocking; no independent numerical cycle deadline encoded. +cycles delays successor fetch. Full transport/source-image legality remains separate.',
             'command_legality_scope':'source descriptors use static512 and2048; live extent/padding, image and full transport legality are not qualified by this structural model',
             'clock':'same die clk, streaming policy1.2GHz; no physical frequency credit'},
             'HBM':{'N':96,'P':1024,'PF':256,'compiled_NMAX2048':'model obligation for ONE shared provider covering candidate2048; measured512 standalone does not establish this provider',
             'calendar_calls':calls,'native_calendar':calendar,'hardware_provider_bound':False,'replicas_per_TP_group_if_replicated_provider':96,
             'deadline':'retire all writes ACK and all consumers done per Dewey calendar; finite RF/transport leases still required'},
             'Qwen_ROM_and_HBM':'existing argmax provider unchanged; this selector does not implement current ROM op3; no automatic replacement'},
        'service_composition':totals,'slot_binding':{'reticle_source':'inputs/reticle_model_r4.json','reservation':slot,'comparisons':comparisons,
             'placement_basis':'source hierarchical ledger proxy50pct, not hardened;35pct retained only as historical physical comparison',
             'meaning':'Source X_SEL reserve reassigns524288bits only at50pct. Candidate memory fits that storage-only reserve; complete retained selector state exceeds it even before logic. No hidden selector logic credit from other rectangles; reconcile contained instances once.',
             'physical_owner_action':'Keep524288bit store charge already included once; add missing histogram/filter/control/pipeline state plus explicit logic/hold/read/fanout construction. Growing selector rectangle displaces adjacent PROSPECTIVE_COMMON_CONTROLLER_CUT and attention/hub corridors; no free outside-area credit.',
             'HBM_full_provider_slot':None},
        'exactness':{'suffix':'exclusive greater-bin sums modulo2^CB; up/down recurrence preserves every word','choice':'unchanged predicate and highest-bin winner; retain old pbin/pgt on no-match',
             'ties':'unchanged rank-major ascending-global-ID filter, signedzero canonicalization, NaN fault, Inf behavior, equal quota, padding; no FP reordering',
             'filter_changes':False,'hist_drain':'freeze prefix/rr until all histogram valid tokens drained; no overlapping commands'},
        'G0':{'engine_RTL_admitted':False,'PR_admitted':False,'decision':'REFUSE_CURRENT_RESERVED_SLOT_AND_UNCLOSED_FILTER',
             'reasons':['compiled ROM2048 full retained FF state exceeds storage-only X_SEL_TOPK_STORE at source50pct before integer/filter logic',
                        'staged suffix does not remove source PF64/256 serial filter quota/prefix paths; actual SS/FF bounds absent',
                        'HBM full2048 hardware provider/slot and ACK leases unbound'],
             'next_engineering_action':'Reconcile ONE full N4/NMAX2048/LDW4 selector reservation with physical owner using FF lower bound and shared decode/filter construction. Price balanced filter quota/prefix and compaction alongside staged histogram/suffix/choice before opt-in RTL; reject this suffix-only pipeline as a build-ready revision.',
             'topology_preference_for_next_model':'staged DIG8 is lower serial residence than DIG4 at both full runtime lengths, but no adoption until area/slot/filter/clock admission; balanced combinational has zero added cycles and unqualified multi-adder stage delay'},
        'experiments_launched':0,'baseline_changed':False,'PVE2_PVE3':'no new jobs; old route untouched'}

if __name__=='__main__':
    model=build();(BASE/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'G0':model['G0'],'composition':model['service_composition'],'ROM_slot':model['slot_binding']['comparisons']},indent=2))
