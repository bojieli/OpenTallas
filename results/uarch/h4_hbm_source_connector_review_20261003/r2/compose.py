#!/usr/bin/env python3
"""Bind frozen W2 owner costs to the connector receipt; no model/RTL changes."""
import argparse,hashlib,json,math
from pathlib import Path
BASE=Path(__file__).resolve().parent
MANIFEST_PIN='e235238dfdd7330ea6815f8eb00929994731b7638b1957a1ebb0910c81d0a5d2'
def require(x,m):
 if not x:raise ValueError(m)
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def outputs():
 raw=(BASE/'manifest.json').read_bytes();require(hashlib.sha256(raw).hexdigest()==MANIFEST_PIN,'manifest pin');manifest=json.loads(raw)
 for r in manifest['inputs']:
  p=(BASE/r['archive']).resolve();require(p.is_relative_to((BASE/'inputs').resolve()),'archive path');b=p.read_bytes();require(len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],'input pin '+r['path'])
 root=BASE/'inputs/results/uarch/w2_pc_exact_completion_20261003'
 m=json.loads((root/'model.json').read_bytes());handoff=json.loads((root/'handoff.json').read_bytes());rows={}
 for label,nc,rawbits,protected in [('successor',5,4145,7848),('full_wrapper_variant',6,4779,9144)]:
  p=m[label];require(p['geometry']==dict(AW=34,CTAGW=32,GENW=4,MAX_OUT=16,NC=nc,NPC=128,PTAGW=35,backend_tag_plus_generation_bits=39),'geometry')
  require(sum(p['state_bits_by_section'].values())==rawbits==p['state_bits_per_PC'],'raw section ledger')
  ps=p['protected_storage'];require(sum(ps['bits_by_section'].values())==protected==ps['bits_per_PC'],'protected section ledger')
  require(p['table_entries_per_PC']==nc*16 and p['table_entry_bits']==39,'implemented rows39')
  require(p['lookup_ports']==dict(request_nonreuse=1,read_return=1,write_return=1),'three lookups')
  require(p['port_signal_bits']['backend_request']==332 and p['port_signal_bits']['backend_read_return']==297 and p['port_signal_bits']['backend_write_completion']==41,'scoped signal widths')
  require(math.isclose(ps['gross_reservation50pct_mm2_all_PCs_ASSUMED'],ps['gross_body_mm2_per_PC_ASSUMED']*128/.5),'replication floorplan gross')
  rows[label]=dict(NC=nc,table_rows=nc*16,minimum38_row_bits=nc*16*38,implemented39_table_bits=nc*16*39,
   raw_state_bits_per_PC=rawbits,raw_state_bits_all128PC=rawbits*128,protected_state_bits_per_PC=protected,protected_state_bits_all128PC=protected*128,
   raw_state_by_section=p['state_bits_by_section'],protected_state_by_section=ps['bits_by_section'],
   gross_raw_cell_body_mm2_per_PC=p['gross_body_mm2_per_PC'],gross_protected_body_mm2_per_PC_ASSUMED=ps['gross_body_mm2_per_PC_ASSUMED'],gross128PC50pct_slot_mm2_ASSUMED=ps['gross_reservation50pct_mm2_all_PCs_ASSUMED'],
   three36bit_key_lookups=True,perclient16way_held_tag_gen_mux=True,slot4_client_implicit_only_at_actual_bank=True,
   protection_768NAND_equivalent_per_word_ASSUMED=ps['ECC_gate_equivalents_per_codeword_ASSUMED'],physical_admission=False)
 require('p_wr_done_ready' in m['interface']['backend_write'],'frozen backend-ready interface')
 source_meta=92;request547=455+source_meta;return561=465+source_meta+4
 result=dict(verdict='FAIL_CONNECTED_SOURCE_MODEL_ADMISSION',scope='W2 price/interface bound for Popper composition; no whole bridge admission',owner_commit=manifest['owner_commit'],owner_reference_tests_reported=handoff['tests'],owner_tests_rerun=False,
  supersedes_prior_pulse_only_compatibility=True,p_wr_done_ready_required=True,
  packet_identity=dict(scoped_PTAG35_plus_GEN4=39,aggregate_PC7_plus_scoped=46,direction_separate=True,DIE_scope='source R14 die1 remains external endpoint scope; crossing die requires explicit retained DIE, not owner46 alone',STACK_scope='PC7 encodes stack2/localPC5 and must agree with retained identity.stack2',legacy_identity192_preserved=True),
  actual_source_top_NC6_KV5_occupied=True,primary_NC5_is_parameter_instance_not_current_full_wrapper=True,new_directory_client=False,
  W2_model_costs=rows,
  once_only_composition=dict(rule='F0_old_total - exact_matched_old_W2_debit + bound_gross_NC6_W2; preserve unrelated private parent/provider/transport costs',matched_old_W2_debit=None,net_increment_mm2=None,existing_baseline_mux_counters_in_gross=True,do_not_subtract_private_parent_context_or_R14_lookup=True),
  chosen_endpoint_contract=dict(route='actual accepted caller -> lossless r17 address translator -> scoped W2 exact sector -> R14 accepted allocation -> physical return/restored full identity -> W2 held terminal -> complete RF assembly/W4 -> W6 reverse/drain',
   actual_caller_implementation_bound=False,one_W2_transaction_bytes=32,R14_LEN6_value_for_this_minimum_sector_route=1,R14_BEAT5_value_for_this_minimum_sector_route=0,
   retained_LEN6_BEAT5_fields=True,LEN_gt1_requires_explicit_child_beat_to_one_terminal_join_not_first_beat_retirement=True,
   producer_original_tag32_not_overwritten=True,producer_generation4_unchanged_echo=True,physical_backend16_distinct_from_source_owner46=True,
   proposed_R14_request_raw_bits=request547,proposed_R14_owned_raw_bits=return561,
   WR_terminal='Only matched backing-visible accepted completion; pulse cannot become physical visibility. Frozen p_wr_done_v/r must remain held or be captured by explicitly priced legacy adapter.',
   read_return='Exact backend16 plus direction/beat/legacy identity and saved child owner before W2 fulltag/gen completion',
   reverse='Validate saved DIE/STACK, full child and parent identity, beat, direction, consumer lease and all-copy source drain before physical-tag reuse'),
  boundary_signal_bits=dict(scoped_request=332,scoped_read=297,scoped_write=41,aggregated_request=339,aggregated_read=304,aggregated_write=48,
   channel_capacity=None,routes=None,W2_signal_counts_are_not_W10_packet_widths=True,W10_prior_389_353_raw_packets_include_LEN_and_SM_slot_parentref_not_W2_control_wires=True),
  latency=dict(L1_request_selection_to_backend_min_edges=1,L1_backend_read_capture_to_client_min_edges=2,L1_backend_write_event_to_client_min_edges=3,
   L1_no_bypass_request_II=2,L1_no_bypass_read_II=2,write_query_II=1,L2_L3_sensitivity=m['prospective_latency_sensitivity'],
   R14_lookup12_CORE_edges_retained=True,R14_return_arb7_CORE_edges_retained=True,source_clock_period=None,CDC_and_crossclock_conversion=None,whole_token_bound=None),
  pending_gates=['actual native/PC client producer and parent-child allocator','lossless accepted-tag receipt + full16 backend tag pipeline and generation restoration','R14 retirement/reverse/reset all-copy predicate and continuous reuse waits','RF assembly/codec/reader visibility and protected-state hold costs','once-only F0 debit, named slot/channel/clock/SSFF and whole service calendar'],build_allowed=False)
 return canonical(result)
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();raw=outputs()
 if a.verify:require((BASE/'composition.json').read_bytes()==raw,'byte exact composition')
 else:
  require(a.output is not None and not a.output.exists(),'fresh output');a.output.write_bytes(raw)
 print('PASS frozen W2 field/cost/port joins; FAIL_CONNECTED_SOURCE_MODEL_ADMISSION retained')
if __name__=='__main__':main()
