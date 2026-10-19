#!/usr/bin/env python3
"""Bounded source/analytical ledger. Does not simulate RTL or qualify timing."""
import collections, gzip, hashlib, json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent
WT = pathlib.Path('/home/ubuntu/wt/codex-kv-health-plane-model-1019')
OUT = ROOT if (ROOT/'historical357_successor.json.gz').exists() else WT/'results/arch/kv_health_plane_model_1019'
OUT.mkdir(parents=True, exist_ok=True)
def read(p): return json.loads(pathlib.Path(p).read_text())
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def emit(n, v): (OUT/n).write_text(json.dumps(v, indent=2)+'\n')
diepath=pathlib.Path('/home/ubuntu/artifacts/kv-pc-health-join-1019/die_bound.v')
die=diepath.read_text()
def instance(name):
    m=re.search(r'^\s*(\w+)\s+(?:#\(([^\n]*?)\)\s+)?'+re.escape(name)+r'\s*\(([^\n]*)\);', die, re.M)
    assert m, name
    return {'instance':name,'master':m[1],'parameters_text':m[2],
            'ports':dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[3]))}
old=read(ROOT/'basis/out/successor.json') if (ROOT/'basis/out/successor.json').exists() else json.loads(gzip.decompress((ROOT/'historical357_successor.json.gz').read_bytes()))
pc=read(ROOT/'PC_producer_basis.json') if (ROOT/'PC_producer_basis.json').exists() else read('/home/ubuntu/artifacts/kv-pc-fault-export-1019/producer_ledger.json')
sources=[]
for x in old['sources']:
    y={k:x.get(k) for k in ('id','instance','port','clock','reset','sticky','signal')}
    y['role']='historical export/aggregate membership, reconciled source identity; not primitive count'
    y['selected']=instance(x['instance'])
    assert x['clock'] in y['selected']['ports'].values(),x['id']
    sources.append(y)
for name in sorted({r['group'] for r in pc['records']}):
    x=instance(name); p=x['ports']; members=[r for r in pc['records'] if r['group']==name]
    assert len(members)==4
    sources.append({'id':name+'.local_fault','instance':name,'port':'o_ctl[17]',
                    'clock':p['ck'],'reset':p['rst_n'],'sticky':True,'selected':x,
                    'role':'existing group local sticky output; PC candidate preserves registered field301',
                    'PC_members':[r['selected_instance'] for r in members],
                    'candidate_causes':[c['id'] for r in members for c in r['causes']]})
assert len({r['id'] for r in sources})==len(sources)
buckets=[]
groups=collections.defaultdict(list)
for x in sources: groups[(x['clock'],x['reset'])].append(x)
# Cap30 leaves leaves room for two bucket-state loads on one stage2 reset copy.
for (clock,reset),rows in sorted(groups.items()):
    for start in range(0,len(rows),30):
        buckets.append({'id':'health_bucket_'+str(len(buckets)), 'clock':clock,
                        'source_reset_owner':reset,'members':[r['id'] for r in rows[start:start+30]],
                        'retention_clear':'pad_por_n only; source reset is observed, never clears retained bad',
                        'registered_input_bits':len(rows[start:start+30]),
                        'output_bundle':{'bad':1,'armed':1},
                        'source_reset_release_two_actual_clock_edges':True,
                        'physical_cluster_qualified':False})
clocks=sorted({r['clock'] for r in sources})
byclock=collections.Counter(b['clock'] for b in buckets)
joins=sum(n-1 for n in byclock.values())
cost={'fault_input_pin_FF':len(sources), 'bucket_bad_and_armed_FF':2*len(buckets),
      'bucket_reset_landing_FF':2*len(buckets),
      'regional_binary_join_bad_armed_and_reset_FF':4*joins,
      'four_cross_clock_ring_minimum_FF':4*20,
      'central_five_root_binary_join_bad_armed_and_reset_FF':4*4,
      'host_final_input_bad_armed_plus_state_and_reset_FF':6,
      'endpoint_retained_bad_FF':1}
emit('collector_model.json',{
 'status':'SOURCE_READY_INTERFACE_CANDIDATE_NOT_IMPLEMENTED_OR_NATIVE_QUALIFIED',
 'selected_die_sha256':sha(diepath),'primitive_count_qualified':None,
 'membership_semantics':'357 old export/aggregate records plus32 group output taps; not389 primitive causes',
 'clock_reset_groups':len(groups),'sources':sources,'buckets':buckets,
 'regional_bucket_counts':dict(byclock),'registered_binary_joins':joins,
 'proposed_ABI':{'source_input':'fault_i (registered face input)',
   'source_lifetime':'retain raw source events before source reset/start can erase them',
   'transport_bundle':'{armed,bad}:2 bits; continuous, POR-to-POR monotone bad; no credits or cutoff mask',
   'receive_ports':['health_bad_i','health_armed_i','health_por_n'],
   'clear':'raw pad_por_n only; never host_rst_n, PLL-qualified POR, layer start, STATUS, recovery or CQ pop',
   'ready':'AND actual reset-release/image/epoch readiness; fixed compiler start, no conditional health wait',
   'identity':'health is die-global; result existing59-bit identity/2-bit generation and per-user owner remain checked',
   'nonadopted':'new source paths and register ancestry required; existing spare payload bits not presumed usable'},
 'FF_analytical_lower_bound_components':cost,'FF_analytical_lower_bound_sum':sum(cost.values()),
 'new_PC_export_restored_FF_excluded_from_above':1280,
 'cross_clock_ring_cost_basis':'Per2-bit four-slot ring:8payload+4pointer+4pinIO+4reset landing FF. Lower bound only; actual epoch/checker/control and clock/reset copies additional.',
 'cost_exclusions':['physical subdivision within a clock/reset group','long-wire forwarded half-cycle stations',
 'POR/arming and every-source reset-loss/PLL capture','BUF/INV-transparent copy fixed point',
 'all actual ring fault/epoch/first-use circuitry','poison return forest and final host mirrors','combinational mapping, clock capacitance, PG/OBS and native reach'],
 'model_area_um2':None,'clock_cap_fF':None,'native_reach_um':None,
 'four_clock_crossings':[(c,'n_clk_core_c[0]') for c in clocks if c!='n_clk_core_c[0]'],
 'reset_policy_blocker':'Actual supplied native por_n=por_n&&pll_locked clears old sticky state. No known independent running clock/async loss-capture implementation yet retains every event through PLL stop.',
 'absolute_deadline_edges':None,'STATUS_edge':None,'SU_token_edges':None,'MU_frame_edges':None,
 'source_to_STATUS_recurrence':'T_join=max(T_left,T_right)+1 on actual local clock; T_land=calendar_map(T_source,K_epoch,forwarded phase,ring read slot)+capture stages; T_STATUS>=max_i(F_i+L_i)+codec/link/host tail',
 'source_horizon':'F_i is actual final causal producer predicate per layer, including late reset, arithmetic/landing errors and memory returns; no invented quiet window',
 'price':'For40 layers: extra_SU=40*max(0,new_critical_layer_edges-old_critical_layer_edges). Rate_ratio=old_token_edges/(old_token_edges+extra_SU). Recompute static4-user calendar and each occupied resource independently.',
 'historical_only':{'old_STATUS':1982,'old_sources':357,'old_model_tail':197,'old_provisional_extra_token':7680},
 'no_historical_deadline_or_geometry_transferred':True})
host=instance('host')
base=ROOT/'host_source' if (ROOT/'host_source').exists() else WT/'rtl/qwen_sys/host_integrated_20261014'
hostp=base/'ot_host_if_pb2_observed.sv'
assert sha(hostp)==sha(ROOT/('host_selected.sv' if (ROOT/'host_selected.sv').exists() else 'host_selected_snapshot.sv'))
packet=(base/'qkd_host_control_packet_observed.sv').read_text()
assert '.MU(' not in packet
assert 'NSLOT   = 1' in (base/'qkd_host_fullcontrol_observed.sv').read_text()
assert 'NW      = 18' in (base/'qkd_host_fullcontrol_observed.sv').read_text()
hostmodel={
 'status':'ROOT_PREFERRED_SPECULATIVE_AND_COMMITTED_MODEL_SOURCE_GRANT_NOT_ISSUED',
 'actual_selected':{'root':host,'path':'host.u_rank.u_control.u_control.u_control.u_host.u_core',
  'MODE':0,'HOST_MU':0,'NSLOT':1,'ENG_CTX':1,'NW':18,'PLB':13,'EVQ':4,'EQD':16,
  'reason':'packet wrapper has no MU parameter/forwarding; prompt defaults MU=0 and binds NSLOT1; distinct MU files do not alter selection',
  'scheduler_clock':host['ports']['ck_host'],'native_clock':host['ports']['ck_native'],
  'scheduler_reset':'host_rst_n','native_POR_actual':'por_n&&pll_locked',
  'scheduler_source_sha256':sha(hostp)},
 'actual_irreversible_operations':{
  'rawdone':'step_done updates sl_pos/sl_tok/sl_ngen at I_RUN or MU retire before CQ generation/offer',
  'success_event':'ep_v/ep_d from step_done and (d_gen||eng_fault)',
  'CQ_word1_offer':'D_IDLE->D_CQ1 writes cq_entry+8; AW/W asserted together, independent acceptance',
  'CQ_word0_offer':'D_CQ1_B with m_bvalid writes cq_entry and cq_w0, including phase/status; transition D_CQ0',
  'external_visibility':'AXI may accept AW and W independently; irrevocability starts at VALID offer, before B or observer cq_commit_v',
  'release':'D_CQ0_B response pops event, advances tail/phase, may free SL_DRAIN user; this must also satisfy abort/cache/link drain ownership'},
 'proposed_state_split':{
  'raw_retire_consume':'Consume an actually completed engine response and maintain mq_r/mq_n/sl_inf; preserve existing abort release/exception drain. Never simply AND health into step_done.',
  'speculative_working':'Existing sl_pos/sl_tok/sl_ngen drive next static token while healthy; all effects owned by the current retained context',
  'architectural_mirror':'Add3*NW+2 bits/user for committed position, token, generated count and user state; CSR/public completion state reads mirror',
  'generated_commit':'At actual success word0 VALID offer only, snapshot then update mirror from immutable event head; bad/!armed converts a not-yet-offered word0 to ST_FAULT and poisons context',
  'prompt_commit_candidate':'No CQ exists for non-generated prompt steps. Add fixed per-step internal commit at the actual full source-health horizon, independent of DMA; current output token remains speculative before this edge. Exact horizon/snapshot and compiler receipt prerequisite, not guessed/adopted.',
  'failure':'Poison invalidates speculative state/cache ownership; retain committed mirror. Do not roll back already-offered success transactions.',
  'future_admission':'Block I_IDLE pick, I_GO start, D_ERR descriptor admission, final D_PR_W->SL_RUN and endpoint accept/issue whenever bad or !armed; preserve error transactions and drain already launched DMA',
  'event_capacity':'16existing events remain finite; add per-user failure_pending bitmap and report-once state. Reuse a mutable queued record as ST_FAULT where possible; otherwise stage at mostNSLOT failure reports until queue space. No engine credit or healthy-case conditional wait added.',
  'context_reuse':'Only after native KV/VM/collective/host and abort-drained ownership checks plus required fault CQ completion; no SL_FREE solely on observer/pop',
  'after_success_offer':'Freeze AW/W VALID/address/data until ready; drain word0/B and any committed MSI. A later fault poisons subsequent work and admission, never edits offered payload.',
  'PLL_warm':'Committed/poison/failure-pending lifetime must be rawPOR or explicit drained context recovery. Existing host_rst_n reset is insufficient; preserving these bits requires preserving/matching CQ pointers, owner/tag/generation and DMA lifecycle too.'},
 'analytical_user_state_FF':{'formula':'(3*NW+2 + poison1 + failure_pending1 + report_once1)*NSLOT =59*NSLOT, before retained owner/tag/DMA/reset/copy cost',
   'selected_SU_NSLOT1':59,'future_MU4_uninstantiated':236,'future_MU4_additional_over_selected':177},
 'healthy_schedule_cost':{'shadow_logic_edges_min':0,'actual_Su_edges':None,'actual_MU_edges':None,
   'queue_pressure':'Public retirement follows CQword0; speculative engine progress remains under finite existing queue/outstanding admission. Full production CQ bandwidth and queue occupancy still must be measured.',
   'rejected_model':'Hold each next token until host DMA acceptance: unbounded external AW/W/B latency, no finite SU token cost'},
 'cache_poison_distribution':{
   'roots':['kvs_ctl','kvs_attn','host.u_rank.u_native','32slg_* group roots','128kvpc_* memory/return endpoints'],
   'actual_ABI_gap':'Selected CTL/ATTN/PC have no health_bad/armed input; cf_root__fault/ufh are existing causes, not certified new poison distribution paths',
   'new_candidate_ports':['health_bad_i','health_armed_i','health_por_n'],
   'distribution':'registered2-bit root ->4regional trees ->8groups/region ->4PC/group; fanout<=8 at these hierarchy splits, actual face/geometry transport additional',
   'local_actions':'At landed poison inhibit NEW cache read/write commands, request decode/launch, generated-success return and context reuse. Already offered HBM/link writes retain stable protocol and drain into invalid poisoned context; no further cache use after local cut.',
   'return_distribution_endpoint_FF_floor':'(32groups+128PC)*[2registered input bits+1retained poison+2reset landing] =800FF, excludes regional relays, memory-command copies, arming and asynchronous loss capture',
   'return_distribution_endpoint_FF_min':800,
   'release_rule':'No valid/owner reassertion until all launched commands/returns drain and explicit context reinitialization under qualified epoch; no cache data erased or reused merely by clearing health'},
 'whole_parent_source_ready':False,'native_qualified':False,'exactness_qualified':False,
 'ROOT_decisions_remaining':['prompt internal fixed health-commit horizon and ownership boundary','rawPOR/PLL-loss retained lifetime with actual clock stoppage','which postcommit failures poison global die versus retained user contexts; no selective user clear by default']}
emit('host_commit_model.json',hostmodel)
manifest={str(p):sha(p) for p in [diepath,(ROOT/'basis/out/successor.json' if (ROOT/'basis/out/successor.json').exists() else ROOT/'historical357_successor.json.gz'),pathlib.Path('/home/ubuntu/artifacts/kv-pc-fault-export-1019/producer_ledger.json'),hostp]}
for p in [base/'qkd_host_control_packet_observed.sv',base/'qkd_host_control_prompt_observed.sv',base/'qkd_host_fullcontrol_observed.sv',base/'qkd_host_if_pins_observed.sv',base/'qkd_host_rank_services.sv']:
    manifest[str(p)]=sha(p)
emit('input_manifest.json',manifest)
emit('static_checks.json',{'selected_host_source_exact':True,'selected_nested_HOST_MU':0,'selected_NSLOT':1,'selected_NW':18,
 'old_membership_unique':len(old['sources'])==len({x['id']for x in old['sources']}),
 'PC_group_membership_exact':len(sources)-len(old['sources'])==32,
 'one_owner_per_input':sum(len(x['members'])for x in buckets)==len(sources),
 'bucket_loads_at_most30':max(len(x['members'])for x in buckets)<=30,
 'groups_unchanged_by_PC_taps':len(groups)==104,'clock_roots':len(clocks),
 'all_physical_and_deadline_claims_withheld':True,
 'checks_scope':'Deterministic bounded source/membership arithmetic only, not RTL simulation or proof'})
print(json.dumps({'collector_buckets':len(buckets),'regional_joins':joins,'collector_FF_lower_bound':sum(cost.values()),'output':str(OUT)}))
