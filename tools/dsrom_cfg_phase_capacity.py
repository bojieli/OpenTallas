#!/usr/bin/env python3
"""Source-sized cfg/dispatcher debt for the sole shared candidate; no build."""
import json,math,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/uarch/dsrom_cfg_phase_capacity_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 receipt=json.loads((OUT/'input_receipt.json').read_text());inp={}
 for n,r in receipt['inputs'].items():
  p=OUT/'inputs'/n;assert sha(p)==r['sha256'];inp[n]=p.read_text()
 a=json.loads(inp['allocator_attempt4.json']);later=json.loads(inp['allocator_attempt8.json']);s=a['stage_stats'][0];macro=json.loads(inp['ot_rom_4096x72_m8.json']);corr=json.loads(inp['corridor_correction.json'])
 pair=inp['ot_v41_pair_w17w10.sv'];adapt=inp['ot_v41_rom_adapt.sv'];spine=inp['ot_v41_spine_w17w10.sv']
 for t in ['CW = 3 * NSEG + 1','DEPTH = CW << PHW','reg [47:0] cm [0:DEPTH-1]','reg [AW-1:0] ld_a','reg [47:0]  c_d']:assert t in pair,t
 assert 'for (k = (1 << PHW) - 1; k >= 0; k = k - 1)' in adapt
 assert 'keyrom[k][29:0] == 30\'(key)' in adapt
 assert 'reg [63:0] phrom [0:(2 << PHW)-1]' in spine
 assert a['candidate_id']==later['candidate_id']==corr['candidate_id']=='DS4096-TP4-S58-PAIR1'
 phw=s['required_PHW'];cw=25;depth=cw*(1<<phw);np=s['compiled_NP'];active=s['active_capacity_pairs'];assert phw==10 and np==4096 and active==3375
 assert active*depth*48==s['pair_cfg_bits_if_required_PHW']==4147200000
 macroarea=macro['area']['macro_area_um2'];bitcell=macro['area']['cell_area_um2'];chunks=math.ceil(depth/4096)
 assert chunks==7
 counts={}
 for name,n in [('active_conditional',active),('compiled_declared',np)]:
  bits=n*depth*48;macros=n*chunks;body=macros*macroarea/1e6
  # Source-equivalent independent48-bit reads:7deepexisting72-bit ROMs per pair.
  # Six48bit 2:1 muxes form an explicit binary selection construction proxy.
  mux_nand2=n*6*48*3; muxcell=mux_nand2*.08748/1e6
  counts[name]=dict(pairs=n,cfg_bits=bits,bytes=bits//8,payload_bitcell_area_mm2=bits*bitcell/1e6,FF_storage_area_at50pct_mm2=bits*.37908*2/1e6,existing_ROM4096x72_count=macros,ROM_body_mm2=body,ROM_body_extra_vs_one_per_pair_mm2=n*(chunks-1)*macroarea/1e6,word_mux_NAND2_construction=mux_nand2,word_mux_cell_proxy_mm2=muxcell,word_mux_placement_at50pct_mm2=2*muxcell,ROM_plus_word_mux_screen_mm2=body+2*muxcell,ROM_mapping_scope='Prospective source-equivalent depth mapping; one48-bit word/read/cycle/pair. Actual mask ROM mapping/decoder/clock/halo/SSFF not implemented. Width24bits unused; no assumed multiport packing.',cfg_read_bits_per_cycle=n*48,cfg_read_bytes_per_cycle=n*6,cfg_clock_sinks=n*chunks)
 perstage=[]
 for z in a['stage_stats']:
  q=max(1,z['required_PHW']);d=cw*(1<<q)
  perstage.append(dict(stage=z['stage'],phase_count=z['phase_count'],required_PHW=q,compiled_NP=z['compiled_NP'],active_pairs=z['active_capacity_pairs'],active_cfg_bits=z['active_capacity_pairs']*d*48,compiled_cfg_bits=z['compiled_NP']*d*48,compiled_existing4096x72_count=z['compiled_NP']*math.ceil(d/4096)))
 full=counts['compiled_declared'];bitsdelta=np*(depth-25*64)*48
 # Local loader state:ld_run1,ld_k5,ld_aAW,ld_np3,c_v1,c_a5,c_d48,act1.
 aw=math.ceil(math.log2(depth));oldaw=math.ceil(math.log2(25*64));loader=np*(1+5+aw+3+1+5+48+1)
 phases=1<<phw;keybits=32*phases
 smallmacro=json.loads(inp['ot_rom_1024x72_m8.json'])
 state=dict(phase_descriptor_existing_2ROM1024x72_body_mm2=2*smallmacro['area']['macro_area_um2']/1e6,phase_descriptor_port_contract='Two independent64-bit reads on op accept (pw and rsplit);2one-port72bit macros proposed, or proven equivalent128bit-wide entry. No free second port.',stream_existing_4ROM4096x72_body_mm2=4*macroarea/1e6,stream_ROM_local_wordmux_3x48_NAND2_placement_mm2=3*48*3*.08748*2/1e6,loader_bits=loader,loader_AW=aw,old_loader_AW=oldaw,added_loader_address_bits=np*(aw-oldaw),phase_descriptor_bits=128*phases,phase_descriptor_bits_delta=128*(phases-64),stream_ROM_bits_retained_SAW14=48*(1<<14),stream_storage_not_expanded_without_emitted_schedule=True)
 eq_ops=phases*31; reduction=phases*30;keyfanout=phases
 # General AND-of-XNOR comparators3NAND2 per XNOR, then30 reductions.
 compare_nand=eq_ops*3+reduction
 dispatch=dict(key_declared_bits=keybits,key_width=32,key_compare_bits_per_entry=31,entries=phases,keys_actually_present=s['phase_count'],eq_bit_comparisons=eq_ops,comparison_reduction_2input_ops=reduction,comparison_NAND2_construction=compare_nand,comparison_cell_proxy_mm2=compare_nand*.08748/1e6,unbalanced_source_priority_assignments=phases,lowest_matching_phase_wins=True,priority_network_area_not_in_comparison_proxy=True,key_and_family_input_fanout=keyfanout,lookup_reads_all_entries_in_parallel=True,ordinary_1R_ROM_cannot_implement_parallel_lookup=True,prospective_FF_key_storage_at50pct_mm2=keybits*.37908*2/1e6,priority_10bit_mux_construction_upper_NAND2=phases*phw*3,priority_construction_not_qualified_as_synthesized=False,combinational_1024_compare_and_priority_timing_closed=False,compare_AND_tree_depth_lowerbound=5,source_priority_assignment_depth_possible_up_to=phases,priority_depth_scope='Source loop implies lowestmatchpriority. Actual synthesis can restructure; no physical timing or implementation tree assumed.',serial_ROM_scan_alternative_would_add_up_to_cycles=phases,serial_scan_not_selected=True)
 bw=sum([1,phw,3,1,1,1,8,3,2,256,10,256,10,3,3,1,3,4,32,1024]);control=1+phw+3
 x=dict(schema='opentallas.DSROM.cfg-phase-source-priced.v1',candidate_id=a['candidate_id'],inputs=receipt['inputs'],allocator_snapshot=dict(attempt4_sha256=receipt['inputs']['allocator_attempt4.json']['sha256'],capacity_verdict=a['capacity_verdict'],allocation_failure_count=len(a['allocation_failures']),stage0=s,later_attempt8_stage0=later['stage_stats'][0],later_attempt8_verdict=later['capacity_verdict'],final_record_confirmed=False,original_failure_preserved=True),
  stage_source_storage_census=perstage,stage_census_scope='Same58 actual allocator rows, not independent count/parameter sweep. PHW per stage is required contract, not source-plumbed hardware.',sum_cfg_bits_all58_four_ranks_compiled=4*sum(z['compiled_cfg_bits'] for z in perstage),config_words_per_pair=cw,PHW_source_default=6,PHW_required=phw,phase_capacity=phases,cfg_words_per_pair=depth,additional_compiled_cfg_bits_vs_PHW6=bitsdelta,storage_cases=counts,source_state=state,dispatcher=dispatch,
  ports_and_clocks=dict(cfg_word48bits=48,cfg_word_bytes_per_pair_cycle=6,cfg_address_bits=aw,cfg_macro_OBS_layers=['M1','M2','M3','M4'],cfg_macro_OBS_scope='Actual LEF snapshot; detailed translated pin escape and halo inventory not completed.',config_field_broadcast_bits=control,config_broadcast_extra_bits=4,broadcast_total_bits=bw,spine_BST=2,extra_BST_state_bits_for_PHW10=8,phase_fanout_pairs=np,phase_fanout_not_single_serial_count=True,loader_local48bit_cfg_never_broadcast_to_other_pairs=True,return_regions_retained=128,stream_GHz=1.2,serial_GHz=.9,actual_source_single_clk=True,physical_CDC_clockPG_provider_missing=True,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,control_routes_require='10phase+cfg_go+3positions across all compiled pairs, branch repeaters and registered cuts priced; local48cfg output+15addr+depthselect/clock/OBS/halos must fit each frame. No free fanout or extra ports.'),
  service_delta=dict(old_corrected_S58_margin_mm2=corr['corrected_margin_mm2'],full_no_embedding_cfg_ROM_plus_mux_screen_mm2=full['ROM_plus_word_mux_screen_mm2'],resulting_same_basis_margin_if_full_cfg_charge_added_mm2=corr['corrected_margin_mm2']-full['ROM_plus_word_mux_screen_mm2'],placement_fit=False,embedded_cfg_credit_proven=False,increment_vs_PHW6_reported_separately=True,scope='Full incremental ledger owed; frame residual may already reserve some cfg but no charge exclusion allowed without source placement proof. ROM body+wordmux screen excludes decoder, clocks, halo, CAM, priority, PHROM and streams; not a final full-goal area.'),
  token_latency=dict(CW_plus2_cfg_cycles=27,at1p2GHz_cfg_ns=22.5,phase_lookup_source_nonindexed_path_cycles=2,indexed_lookup_extra_VM_wait_and_key_calc_cycles=2,cfg_spine_BST_wire_stages=2,configuration_service_parallel_across_pairs=True,total_phase_count_not_token_event_count=True,per_token_phase_events_required='Maxwell must bind actually selected QE/ME accepted ops and source cfg_go/phase changes per token;910 distinct resident phases is not910 executed phases.',macro_SS_clk_to_q_requires_check=True,source_priority_lookup_may_require_priced_cut_or_fail=True,no_full_token_upper_bound=True),
  coordinated_next=['Nash freezes exact final allocator/program binding record and emitted cfg extent for declared/padding pairs','Archimedes/Kepler reserve cfg macros/localmux/dispatcher/PHROM/streams/clockPG with whole element frames; no physical gate before actual fit','Maxwell binds exact token cfg/lookup events and physical cut costs; stagehop and TPcollectives separate'],no_new_candidate_count_or_sweep=True,compiler_run=False,RTL_PnR_builds=0,physical_GO=False,checkpoint_payload_reads=0,generator_sha256=sha(Path(__file__)))
 raw=(json.dumps(x,indent=2,sort_keys=True)+'\n').encode();p=OUT/'model.json'
 if p.exists():assert p.read_bytes()==raw
 else:p.write_bytes(raw)
 print(json.dumps(dict(cfgbits_conditional=4147200000,cfgbits_compiled=full['cfg_bits'],cfg_ROM_body_mm2=full['ROM_body_mm2'],cfg_wordmux_placement_mm2=full['word_mux_placement_at50pct_mm2'],postcharge_margin=x['service_delta']['resulting_same_basis_margin_if_full_cfg_charge_added_mm2'],sha256=hashlib.sha256(raw).hexdigest())))
if __name__=='__main__':main()
