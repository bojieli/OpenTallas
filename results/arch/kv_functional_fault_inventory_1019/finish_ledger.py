#!/usr/bin/env python3
import collections,gzip,json,pathlib
O=pathlib.Path(__file__).parent
op=json.loads((O/'open_ports.json').read_text())
raw=json.load(gzip.open(O/'unread_outputs.json.gz'))['outputs']
land=[r for r in raw if r['master'].startswith(('qkd_landsh_','qkd_landsh0_')) and r['port']=='fault']
assert len(land)==351
kc=[r for r in op['open_instances'] if r['master']=='qkd_ctrl_kc' and r['port']=='kf'];assert len(kc)==4
dcal=[r for r in op['open_instances'] if r['master']=='qkd_d2d_cal_seq_pin_bc' and r['port']=='fault'];assert len(dcal)==1
rules=[]
internal_host={'record_fault','peer_protocol_fault','coordinator_fault','service_faults','service_abort','service_ready','ingest_permission','local_service_epoch','service_diag_raw','service_status','package_abort','recovery_complete','hc','marker','marker_v','issued','landed','program_auth_digest','program_auth_epoch','program_auth_v','program_authorized_footer64','program_authorized_footer_v','program_expected_dw','program_expected_pw','sys_ready','program_consensus'}
for x in op['open_types']:
 m,p=x['master'],x['port'];row=dict(x,release_admitted=False,physical_native_phase_proven=False)
 if m=='qkd_ctrl_kc':
  row.update(classification='FUNCTIONAL_FAULT_GAP_ALREADY_IN_356_CANDIDATE',semantics='kf<=two-core-edge synchronized fi OR sticky command FIFO overflow; reset rs_q captures rsi on ck. Native output kf[0].')
 elif m=='qkd_d2d_cal_seq_pin_bc':
  if p=='fault':row.update(classification='ADDITIONAL_FUNCTIONAL_FAULT_GAP',semantics='Registered sticky s_fault OR boot/sequencer write collision OR boot-write-during-run/admission OR stale segment2 base OR start-before-both-base-writes. Not folded anywhere in actual die.')
  elif p in ('adm_done','cal_ready'):row.update(classification='ADMISSION_CERTIFICATE_OBLIGATION',semantics='Output-register copy of sequencer completion/readiness. No die consumer; actual schedule/boot authorization must prove the equivalent prerequisite, or price an explicit fixed-edge observation. Never convert to an unpriced wait.')
  else:row.update(classification='SEQUENCER_CONTEXT_OBSERVATION_UNRESOLVED',semantics='Output-register running/layer copy; absence of an external consumer is not a diagnostic waiver.')
 elif m=='qkd_host_root_admission':
  if p in internal_host:row.update(classification='INTERNAL_CONSUMER_PRESENT_NOT_RELEASE_PROOF',semantics='Exact source contains internal consumer chain retained in semantic_sources.json; requires terminal STATUS/reset/admission proof. No external duplicate waiver granted.')
  else:row.update(classification='HOST_OBSERVATION_OR_HANDSHAKE_UNRESOLVED',semantics='No die consumer. Native request/result/record/ownership paths exist, but equivalence, external-observer necessity, and supported-profile semantics require explicit review; no waiver.')
 elif m=='qkd_host_pc_slice_die':
  row.update(classification='CHAIN_TAIL_OR_LEGACY_PAYLOAD_UNRESOLVED',semantics='Four per-stack tail pins. bgo is registered boot-chain continuation; fo is legacy ingest payload chain. Actual fault_o/status sfo are distinct outputs. Require exact chain endpoint/legacy-profile proof, never fold payload fo by name.')
 elif m=='qkd_kvs_ctl':
  row.update(classification='DUPLICATED_PROGRAMME_CONTEXT_REVIEW_REQUIRED',semantics='kg={w_lprg__layer,w_lprg__epoch,w_lprg__kgo}; same source signals also feed local consumers. NOT a fault bit and not an OR candidate.')
 elif m.startswith('qkd_kvs_pc'):
  row.update(classification='LEGACY_CONTROLLER_PORT_REVIEW_REQUIRED',semantics='pc__er[260] also appears in o_grp; all other er bits lack that equivalence. Legacy completion_v/we differ from hcompletion_v/we; pc__ko four actual chain-tail pins require endpoint proof. No blanket bus waiver.')
 elif m.startswith('qkd_kvs_grp'):
  row.update(classification='FORWARDED_CONTEXT_OR_DUPLICATE_BUNDLE_REVIEW_REQUIRED',semantics='y__tok/y__tep copy x__tok/x__tep. grp_h.o_dn slices i_ctl and duplicates internal downstream context. Need exact endpoint and bitwise-use proof; no health OR.')
 else:
  row.update(classification='LINK_IDENTITY_OR_RECOVERY_OBSERVATION_UNRESOLVED',semantics='att_rx_slot/kvn_word_slot/kvn_word_index are registered identity metadata; recovery_cycles is counter observation. Missing consumer requires current static identity/slot proof and recovery deadline pricing, not a name-based diagnostic waiver.')
 rules.append(row)
ledger=dict(schema='opentallas.kv_functional_fault_semantics.v1',evidence_only=True,qualified_release=False,strict_failures_unchanged={'unread_net_bits':45863,'output_open_ports':69},open_port_types=rules,known_candidate_sources={'landing_fault':351,'kc_kf':4,'ufh':1,'total':356,'candidate_adopted':False},additional_required_fault_sources=[{'instance':'dcal','master':'qkd_d2d_cal_seq_pin_bc','port':'fault','bits':[0],'minimum_augmented_candidate_count':357,'root_semantic_approval_required':True}],admission_obligations=['dcal.cal_ready and dcal.adm_done fixed-edge prerequisites, actual target11 image/segment writes','host package_abort/service_abort propagation through terminal result, cancellation and reset','host service_ready/program_ready/ownership/current-certificate admissibility','exact AHUB source reset/clear and hf relay drain34/37, all landing and KC clear','loaded native clock/reset phase/skew, every source-to-join-to-AFR-to-TX/LAND/consumer deadline','STATUS and POR fixed schedule/counter-width pricing; never mask sticky health or wait on it'],native_measurements={'new_sources_loaded_phase_or_skew':None,'reset_source_clear':None,'whole_path_status_latency':None},classification_counts=dict(collections.Counter(r['classification'] for r in rules)))
(O/'semantic_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
with gzip.open(O/'exact_fault_native_pins.json.gz','wt') as f:json.dump({'landing_faults':land,'kc_faults':kc,'additional_dcal_fault':dcal,'ufh_note':'Consumed ahub.hf is not a no-reader output. Existing UFH candidate remains a separate functional source; new routing/pricing not admitted.'},f)
assert len(rules)==69 and sum(x['instances'] for x in rules)==521
print(json.dumps({'types':69,'open_instance_pins':521,'landing_faults':len(land),'kc':len(kc),'additional_dcal':len(dcal),'classifications':ledger['classification_counts']}))
