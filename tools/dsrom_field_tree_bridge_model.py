#!/usr/bin/env python3
"""Current source/potential traffic/finite phase reservation model, no engine build.
Reuses retained source control calendar classes for an adversarial-port witness;
never treats offered schedules or proxy area as actual accepted timing/placed fit.
"""
import argparse,collections,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import uarch_model_dsrom_field_bridge as B
import model_dsrom_issue_return_calendar as C
OUT=ROOT/'results/uarch/dsrom_field_tree_bridge_20261003'
PHASES='results/uarch/dsrom_parallel_owner_binding_20261002/r1/phase_shard_bindings.jsonl.gz'
CALLS='results/uarch/dsrom_parallel_owner_binding_20261002/r1/native_shard_choices.jsonl.gz'
SOURCES=['tools/uarch_model.py','tools/uarch_model_dsrom_return_prepare.py','tools/model_dsrom_return_calendar.py','tools/model_dsrom_issue_return_calendar.py','rtl/v41die/ot_v41_field_w17w10.sv','rtl/v41die/ot_v41_retn_w17w10.sv','rtl/v41die/ot_v41_pair_w17w10.sv','rtl/v41rom/ot_v41_ret.sv','rtl/v41rom/ot_v41_rom_elem_w10.sv','rtl/w17_runtime/v41die/ot_v41_spine.sv','rtl/w17_runtime/hdc/v41x/ckvsel/ot_hdc_core_v41x.sv','rtl/w17_runtime/chip/ot_chip_v41x_tile.sv','rtl/test/v41_runtime/v41_die_rt.cpp',PHASES,CALLS,'results/uarch/dsrom_field_tree_bridge_20261003/inputs/R49_physical_union.json.gz']
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def readrows(path):
    with gzip.open(ROOT/path,'rt') as f:
        for line in f:yield json.loads(line)

def source_check():
    field=(ROOT/SOURCES[4]).read_text();ret=(ROOT/'rtl/v41rom/ot_v41_ret.sv').read_text();spine=(ROOT/'rtl/w17_runtime/v41die/ot_v41_spine.sv').read_text()
    for text in ['wire [NL-1:0] n_fault','n_fault[NL - (NL >> l) + g]','assign n_fault[NL-1] = 1\'b0','assign busy = |p_busy']:
        if text not in field:raise ValueError('field source changed: '+text)
    for text in ['if (a_v) begin at[aw]','if (i_v) begin qt[qw]','(a_v && ac == D && !pop_a)','i_v && qc == QD && !use_q']:
        if text not in ret:raise ValueError('return source changed')
    if 'else rows_left <= rows_left - 19\'($countones(r_v))' not in spine:raise ValueError('source completion changed')
    for name,path in [('field','rtl/v41die/ot_v41_field_w17w10.sv'),('node/root','rtl/v41rom/ot_v41_ret.sv')]:
        port=(ROOT/path).read_text()
        if 'input  wire        o_ready' in port or 'input  wire         r_ready' in port:raise ValueError('new handshaking source requires reprice')

def traffic():
    phases={};formats=collections.Counter();largest=None
    for p in readrows(PHASES):
        key=(p['stage'],p['phase'])
        if key in phases or p['row_cross_shard_K_reductions']!=0:raise ValueError('owner/topology changed')
        rows=p['rows_per_rank'];shards=[sum(B.root_rows(rows,r) for r in range(s*64,(s+1)*64)) for s in (0,1)]
        if shards!=[x['output_rows'] for x in p['shards']]:raise ValueError('source root row ownership mismatch')
        phases[key]=dict(rows=rows,shards=shards,format=p['format'],K=p['K'],alias=p['alias'],words=sum(x['physical_weight_words'] for x in p['shards']))
        formats[p['format']]+=1
        if largest is None or rows>largest['rows']:largest=dict(stage=p['stage'],phase=p['phase'],**phases[key])
    totals=collections.Counter();aliases=collections.defaultdict(collections.Counter);selected=[];alternatives=0;native_failures=[]
    for call in readrows(CALLS):
        choices=call['phase_choices'];alternatives+=len(choices)
        pp=[phases[(c['stage'],c['phase'])] for c in choices]
        if len({(p['rows'],tuple(p['shards']),p['words'],p['format'],p['K']) for p in pp})!=1:raise ValueError('choice dependent traffic requires explicit runtime binding')
        p=pp[0];totals['calls']+=1;totals['potential_rows']+=p['rows'];totals['potential_raw_root_bits']+=p['rows']*69;totals['potential_macro_words']+=p['words'];totals['remote_rows']+=p['shards'][1]
        alias=p['alias'].split('.',1)[-1] if p['alias'].startswith('exp') else p['alias'];aliases[alias]['calls']+=1;aliases[alias]['rows']+=p['rows']
        if call['native_admission_failures']:native_failures.append(dict(node=call['node'],failures=call['native_admission_failures']))
        if call['node'].startswith('L0.I') and 66<=int(call['node'][4:])<=105:
            selected.append(dict(node=call['node'],source_phase_example=choices[0]['phase'],stage_example=choices[0]['stage'],choices=len(choices),rows=p['rows'],per_shard_rows=p['shards'],native_W2=p['alias'].endswith('.w2')))
    return dict(phases=len(phases),formats=dict(formats),largest=largest,choice_alternatives=alternatives,potential_singleposition_perrank=dict(totals),per_alias={a:dict(b) for a,b in sorted(aliases.items())},selected18=selected,source_native_admission_failures=native_failures,actual_accepted_traffic=None,head_provider_not_included=True,
      cfg_words_per_phase_per_shard=2048*25,cfg_local_parallel_ports_per_shard=2048,cfg_parallel_cycles=25,cfg_bits_per_phase_per_shard=2048*25*48)

def adversarial_witness():
    n=C.ReturnNode();first=None
    for t in range(70):
        # Different complete row tags on both inputs: valid port trace, not a
        # certified compiled phase. A priority can starve B; inputwrites persist.
        n.step(t,{0:((0,2*t,0,0,1),('A',t)),1:((0,2*t+1,0,0,1),('B',t))})
        if n.faults and first is None:first=n.faults[0]
    return dict(kind='SOURCE_CONTROL_PORT_WITNESS_NOT_ACTUAL_COMPILED_PHASE',first_overflow=first,peak=n.peak,source_A_priority_starves_B=True,current_fullprogram_failure_proven=False,original_fault_and_writes_not_suppressed=True)

def model():
    source_check();r49=json.loads(gzip.decompress((OUT/'inputs/R49_physical_union.json.gz').read_bytes()));assert r49['raw_bit_width_DBU']==2970 and r49['raw_word_width_DBU']==204930
    t=traffic();cap=t['largest']['rows'];pin={p:sha(p) for p in SOURCES}
    return dict(candidate='DS4096-TP4-S58-PAR2-NP2048',source_sha256=pin,default_off=True,originals_untouched=True,
      fault_vector=[B.fault_coverage(4096,128),B.fault_coverage(2048,64)],runtime_scope='C++host ORs actual node/root/pair faults, not flat n_fault; localPASS cannot qualifyflat vector',
      boundary_ports={'cfg_local_word':48,'PHW':10,'full_broadcast':1632,'q_activation_includingvalid':549,'BF_activation_includingvalid':1067,'tree_record':65,'tree_record_includingvalid':66,'source_root':69,'root_ports_per_shard':64,'writer_per_port_address_data_valid':63,'actual_ready_ACK_ports':False},
      source_boundaries=['cfg_go -> ROMword register -> configcapture, generic lastcapture26 safeGO27','go&&act -> element walker;issue=w_run&&f_cnt&&!hazard&&!pp_block; no externalready','pair pv/tag32/value32/error -> node inputFIFO65bits; overflowfault does not suppresswrite','golden sibling add5cycles or bypass1 +RST1; eachnode output<=1/cycle','root i_v -> Q128; prioradderresult blocksQservice; held128sibling slots; no ready','root r_v -> spine w_we/data/address register -> original tile VMpostNBA nextedge; noACK','spine rows_left counts rawr_v,not acceptedVMdelivery;fieldbusy pairOR,not treedrain'],
      unified_additive_terms={'added_MACs_per_cycle':0,'arithmetic_and_reduction_unchanged':True,'root_bytes_per_edge_per_shard_peak':64*69/8,'all_root_bytes_per_edge_peak':128*69/8,'writer_address_data_valid_bits_per_edge_peak':128*63,'tracks_required_before_controls':128*69,'tracks_available':None,'floorplan_admitted':False,'compiled_site_count_per_die':2048,'clock_domain_CDC_latency':None},
      existing_return=B.existing_return_storage(),traffic=t,adversarial_witness=adversarial_witness(),
      successor={'name':'ONE_PHASE_RESERVED_NO_READY_OUTPUT_BRIDGE_DEFAULT_OFF','fault_fix':'bindonlyunusedR-1nodefault bits to0 inadditive selectedwrapper; noactualnode fault masked,0latency; originals pinned','acceptance':'reserve sameowner entirephase outputcapacity and exclusive nativewriter range BEFORE cfg/GO; no new ready inside golden tree','internal_queue_gate':'reuse current tagwalker/ReturnNode/ReturnRoot classes, current622 plans+actualacceptedLAT8 events; assert every64/128queue/holdslot/drain. Bridge cannotfix element/node/root overflow. Reject uncertifiedphase ratherthan assume safety.','output':'128 independentroot banks across2dies; phase-shared full169+physicalshard owner; retain rawrow/pos/fp32/bf16/error; reserve-before-launch avoidsmidphase backpressure. No crossdie readmux.','publication':'sourceformatter and exclusive all12writer exclusion, actualVMpostNBA completion; W2 nativeoutputs given actualphase-specific budget,never576seatassumption.','retirement':'no phase rearm untilallactualrows captured+published+positivecapturedcredits/packetdebts0; qualifiedpreF; VMversion lease separatelythrough actualSUreadR+2','CDC':'actual streaming1.2/serial.9 andresetphase timestamps missing; never use oldfailedratioFIFO as qualifiedservice','smallest_per_phase_required_seats':'sum positions*actual compiledrows; uniform fulltarget bound uses8192maxrows and6selectedpositions; source3bit positionraw8cap separate, not silentlyused','buffer_singleposition':B.buffer_price(cap,1),'buffer_verify6':B.buffer_price(cap,6),'positive_provider_contract':{'parallel_publish_ports':128,'grant_gap_cycles':1,'forward_data_cycles':None,'captured_credit_cycles':None,'actual_guarantee':False},'readmux_clockreset_routes_SSFF_not_qualified':True},
      latency={'actual_exposed_per_token':None,'event_join_equation':'For each actual phase, admission=max(activation/config_ready, reservation_ready); rearm=max(native_idle, last_VM_visible, captured_credit_and_packet_retired)+qualified_control_latency. Propagate these added dependencies in ordered program; only nonoverlapped critical-path displacement is token delta.', 'stall_policy':'Stall new cfg/GO while reservation or previous publication debt is unavailable; never stall an already admitted native tree.', 'stream_cycle_ns':5/6,'violation_set':'UNAVAILABLE','conditional_service8192_P6_parallel128':B.phase_service(cap,6,128,1,3,1),'conditional_service8192_P6_scalar1':B.phase_service(cap,6,1,1,3,1),'conditional_service576_P1_parallel128':B.phase_service(576,1,128,1,3,1),'conditional_service576_P1_scalar1':B.phase_service(576,1,1,1,3,1),'scope':'3forward+1positivecredit is a model minimum candidate, not characterized route/provider. Counts are work fromall-ready payload,not measured end-to-end or tokencriticalpath. ActualF/C/fullcontextmaxstayNone.'},
      parallel_plan={'Maxwell':'current fieldbridge source/fault/no-ready capacity/latency model; source/port contract; noengineRTL untilcomposedG0','Hubble':'onecurrentPHW10 passiveactualtrace: cfg/go/activationaccepted, pairpv/tags, nodeFIFOac/bc/ap/vp, rootqc/held/tag/errors, postNBAallwriters; samecompiledsource/rank/epoch; no duplicate run','Nash':'lifetime/addresslease/readR+2 constraints handoffonly; W2HBM activework notduplicated; consume immutable915selected bounds withoutcallingthemfullcontextcapacity','Archimedes':'parallel fixedclockPGsolve/context endpoint cuts remainscurrent; no q/BF reframe or placement authority change','Claude':'disjoint qreframe/PAR2boundaryproposal only; noadoption'},
      model_before_engine_RTL=True,engine_RTL_written=False,new_jobs=[],build_admitted=False,physical_fit=False,fulltoken=False,rate_adopted=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.write_text(json.dumps(model(),sort_keys=True,indent=2)+'\n')
