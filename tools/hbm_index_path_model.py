#!/usr/bin/env python3
"""Source-preserving HBM index composition; immutable unified-model constants."""
import ast, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def model():
    tree=ast.parse((ROOT/'tools/uarch_model.py').read_text())
    dff=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='DFF_UM2')
    unit=json.loads((ROOT/'results/arch/arch_budget_v41.json').read_text())['unit_areas_um2']
    # Same source element geometry as DEDICATED.indexer, with existing _l cuts.
    keys,heads,dim,slices,nk=64,32,128,16,4
    fpl,fml,ql=7,5,5
    late=(1+ql+fpl*3+1+fml+fpl*7+1)+(1+fpl*2+1)
    depth=1<<(late+3).bit_length()
    base_area=slices*(16*32*unit['blockdot_um2']+4*17310.0)
    # Positive conservative pipeline allowances: no zero-cost inherited cuts.
    adds=keys*(heads*3+heads-1)
    extra_ff=adds*(fpl-3)*128+keys*heads*4*(ql-3)*128+keys*heads*(fml-3)*64
    q_ff=32*(512+32+16)+128+13*7+8+6+3
    metadata=slices*depth*((20+nk+1)+nk*18)
    ctrl_ff=64+7+4+4*21+32+4+1
    query_logic_nand2=32*544*4+128*6+1024
    # Positive allowance for constant96 ownership and per-quarter source order checks.
    source_checks_nand2=2*64*2048+64*20*12
    rows=dict(local_topk=4*256*16*37,candidate=4*1024*2*34)
    return dict(schema='opentallas.hbm_index_path_prebuild.v1',default_ENABLE=0,
      canonical_source=dict(TP=96,block_keys=8,global_ID='8*(96*local_block+rank)+offset',global_context=1048576,local_keys_rank0=10928,local_keys_max=10928,
        quarter_partition='Hardware requires quarter=floor(owned_block_ordinal/342), owned_block_ordinal=floor(global_ID/8/96); globally ordered block8 ranges. Reject malformed assignment before ingress acceptance. Native reader still must supply those source-selected ranges.',quarter_max_blocks=342,quarter_max_keys=2736,quarter_max_score_lines=171,quarter_max_candidate_lines=171,logical_partition_bound_implemented=True,fullshape_partition_numerical_qualified=False),
      datapath=dict(scorer='ot_hdc_v41x_idx_array_l',selector='ot_hdc_v41x_sel',query_quantiser='ot_hdc_actquant',heads=heads,head_dim=dim,slices=slices,keys_per_slice=nk,MACs_per_cycle=keys*heads*dim,FPL=fpl,FML=fml,QL=ql,metadata_depth=depth,source_score_latency_formula_cycles=late,exact_rounding='Unchanged FP4 block dots/BF16 score/relu*weight/chunk8 head sum; only existing latency parameters.',source_keep_and_refusal_preserved=True),
      ports=dict(key_B_per_edge=keys*68,key_bits_per_edge=keys*544,query_FP32_block_B_per_edge=128,query_load_bits_per_head=560,score_and_globalID_bits_per_edge=keys*36,metadata_valid_keep_ref_bits_per_edge=keys*3,selector_memory=rows,local_topk_memory_words_per_quarter=256,local_topk_memory_word_bits=592,local_topk_1R1W_ports=4,candidate_memory_owner='Confucius source48d9512f6; consume existing prebuild_maxima_export.json exactly once, no local repricing' ,physical_macro_instances_and_LEF=None),
      area=dict(unified_base_scorer_cell_estimate_um2=base_area,extra_pipeline_FF_allowance=extra_ff,extra_pipeline_FF_um2=extra_ff*dff,query_assembly_FF=q_ff,metadata_and_engine_fifo_FF=metadata,control_FF=ctrl_ff,source_checks_NAND2_allowance=source_checks_nand2,source_checks_area_um2=source_checks_nand2*.08748,query_logic_NAND2_allowance=query_logic_nand2,query_logic_um2=query_logic_nand2*.08748,
        native_query_source_read_join_FF_allowance=1800,native_query_source_read_join_logic_NAND2_allowance=8192,native_query_source_read_join_area_um2=1800*dff+8192*.08748,scorer_and_join_cell_estimate_um2=base_area+(extra_ff+q_ff+metadata+ctrl_ff)*dff+(query_logic_nand2+source_checks_nand2)*.08748,
        selector_logic_physical_delta=None,quantiser_physical_cell_cost=None,selector_SRAM_physical_area=None,
        rule='Positive source-selected sizing, not exact synthesized FF count. Existing hardened element bases plus positive cut/control allowance. Existing quantiser/selector bodies reused exactly once; physical costs/slot require their source-selected records before P&R.',context_slot_fit=False),
      routing=dict(query_broadcast_replicas=slices,query_bits_aggregate=560*slices,key_tracks=keys*544,score_tracks=keys*36,selector_memory_tracks=4*(2*8+2+2*592),actual_channel_capacity=None,loaded_route_and_clock_qualified=False),
      calendar=dict(query_blocks=128,quantiser_fixed_latency=13,query_load_heads=32,existing_scorer_query_settle_edges=3,candidate_output_bits_per_beat=8*(17+16+1),candidate_output='Actual BF16 maxima/global block IDs from native u_cand_local; frame retained until both selector outputs and external consumer drain, no host score reconstruction.',query_capture_last_block_and_load='After 128 accepted FP32 blocks +13 quantiser edges, all 32 query-head receipts; stall and source movement measured, no free overlap.',scorer_latency_cycles=late,local_rank0_ingest_min_cycles=171,local_selector_tail='Measure composed real score stream, including overflow replay requests and source retention.',source_SU_index_q_rope_scale='Einstein actual shared SU instance/hooks required; no host quantise/restore',query_source_VM_read_request_bits=109,query_source_VM_read_response_bits=1095,query_source_VM_outstanding_reads=1,query_source_VM_response_buffer_bits=1024,query_source_VM_reads=129,query_source_VM_min_serial_edges=386,query_source_VM_clock_and_CDC_qualified=False,query_source_VM_input='Original Q prefix plus REAL native rotated O tails; scaled IWo native BF16 landing. Descriptor/source pins from retained two-op SU program; never expected iqf.',source_SU_movement_and_CDC_cycles=None,final_select='BLOCKED: rank-major TP96 global-ID order violates ot_coll_topk_merge tie/filter contract; Claude ordered-gather redesign required. Do NOT credit419cycles.',full_token_composed_latency=None),
      replicas=dict(per_die_scorer_slices=16,HBM_target_dies=96,full_target_not_built=True),
      source_pins={p:sha(p) for p in ['tools/uarch_model.py','results/arch/arch_budget_v41.json','rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv','rtl/hdc/v41x/ot_hdc_v41x_sel.sv','rtl/hdc/v41/ot_hdc_actquant.sv','rtl/hbm_accel/index/ot_hbm_accel_index_query_source.sv','rtl/hbm_accel/index/ot_hbm_accel_index_candidate.sv','results/rtl/hbm_index_candidate_20261005/prebuild_maxima_export.json']},
      numerical_component_build_only=True,physical_build_admitted=False,context_SS_FF_closed=False,complete_index_qualified=False,adopted=False)
if __name__=='__main__': print(json.dumps(model(),indent=2))
