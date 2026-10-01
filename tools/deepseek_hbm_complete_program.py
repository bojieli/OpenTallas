#!/usr/bin/env python3
"""Full TP96 DeepSeek program companion, with explicit numerical-lowering coverage.

This graph is executable in software. Reference-semantic bindings never count as
ordinary GPU instruction, timing, or DUT qualification. No retained activation
is an instruction operand other than initial checkpoint embedding/KV fixtures.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import w19_hbm_tp96_isa as H

ROOT=Path(__file__).resolve().parents[1]
SOURCE='results/rtl/w19_hbm_tp96_program_oreduce.json'
RESIDENT='results/rtl/w19_checkpoint_production_20261001/resident-service-candidate-r1.json'
LOCAL=('hc_mixes hc_pre_norm q_norm_kv_row q_rope compressor index_q index_scores cand_local cand_apply '
       'cand_mask topk_local attend hc_post router_act route swiglu moe_sum engram_fetch engram_mix final_norm argmax_local').split()
MATRIX=['linear_q','mv','linear_bf16','wo_a_part']
KINDS=['local','mv','all_gather','all_reduce','topk_merge','kv_gather','expert_fetch']
RECIPES={
 'hc_mixes':['tools/w19_gpu_simd_contract.py','tools/w19_gpu_compare_lowering.py'],
 'hc_pre_norm':['tools/w19_gpu_norm_calendar.py'], 'hc_post':['tools/w19_gpu_norm_calendar.py'],
 'final_norm':['tools/w19_gpu_norm_calendar.py'],
 'swiglu':['tools/deepseek_hbm_complete_isa.py'],
 'attend':['tools/w19_attention_lowered_proof.py','tools/w19_gpu_compare_lowering.py','tools/w19_gpu_attention_dots.py'],
 'index_scores':['tools/w19_index32_integer_kernel.py'],
}
STEPS={
 'hc_mixes':['HC_NORM_CHUNK8','FP32_HC_MATVEC_CHUNK8','AFFINE_PRE_POST_COMB','EXP_POLYNOMIAL_COMPARE_WRAPPER','SIGMOID_DIV','SINKHORN_20_ORDERED'],
 'hc_pre_norm':['HC_PRE_SEQ4_BF16','NORM_CHUNK8','RSQRT_THREE_NEWTON','NORM_SCALE_BF16'],
 'q_norm_kv_row':['QA_NORM','KV_NORM_BF16','ROPE_TABLE_LOAD','ROPE_F32_BF16','QDQ8','WINDOW_WRITE_COMMIT'],
 'q_rope':['ROPE_TABLE_LOAD','ROPE_F32_BF16'],
 'compressor':['OPEN_GROUP_WRITE','GROUP_MAX','EXP_POLYNOMIAL_COMPARE_WRAPPER','SEQ_DEN_DIV','POOL_SEQ','COMPRESSOR_NORM_BF16','INDEX_WK_MATRIX','INDEX_NORM_BF16','ROPE_TABLE_LOAD','QDQ4_UE8M0','QDQ4_E4M3','PAIRED_APPEND_COMMIT'],
 'index_q':['ROPE_TABLE_LOAD','ROPE_F32_BF16','QDQ4_UE8M0','WEIGHTS_SCALE_BF16'],
 'index_scores':['FINITE_ROW_OWNER_LOOP','INDEX32_INTEGER_DOT_SINGLE_ROUND','FOUR_BLOCK_CSUM8','BF16','EXACT_MAX_POSZERO','WEIGHTS_FMUL_BF16','HEAD32_CHUNK8_TREE_BF16'],
 'cand_local':['BLOCK_MAX8','PIN_NEWEST','ORDERED_TOPK'], 'cand_apply':['CANDIDATE_PUBLISH'],
 'cand_mask':['CANDIDATE_INDEX_LOOKUP','SELECT_NEG_INF'], 'topk_local':['ORDERED_TOPK'],
 'attend':['QK_CHUNK8_TREE','SCALE','EXACT_MAX_TREE','EXP_POLYNOMIAL_COMPARE_WRAPPER','UNROUNDED_DEN_CHUNK8','SINK_EXP','PV_BF16_CHUNK8_TREE','DIV_BF16','INVERSE_ROPE_F32_BF16'],
 'hc_post':['HC_POST_SEQ4','BF16_RESIDUAL'],
 'router_act':['SOFTPLUS_LOG1P_POLYNOMIAL','SQRT_F32_RNE_SERVICE_UNBOUND'],
 'route':['FADD_BIAS','ORDERED_TOP6','SEQ_ROUTE_DEN','DIV_FMUL_WEIGHTS'],
 'swiglu':['EXACT_MIN_MAX_WRAPPERS','SILU_EXP_DIV','FMUL_UP','ROUTE_FMUL','BF16'],
 'moe_sum':['SEQ7_FROM_POSZERO','BF16'],
 'engram_fetch':['TOKEN_HISTORY_HASH','ROWID_MOD96','FINITE_TABLE_FETCH','E4M3_UE8M0_DECODE_BF16'],
 'engram_mix':['QUERY_KEY_WEIGHT_FMUL','TWO_NORM_RSQRTS','CHUNK8_DOT','ABS_MAX_EPS','SQRT','SIGNED_SIGMOID','RESIDUAL_FMUL_FADD_BF16'],
 'final_norm':['HC_PRE_SEQ4_BF16','NORM_CHUNK8','RSQRT_THREE_NEWTON','NORM_SCALE_BF16'],
 'argmax_local':['F32_SCORE_COMPARE','LOWEST_GLOBAL_ID_TIE'],
}


def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()


def validate(g):
    if (g['tp'],g['head_dies'],g['key_block'],g['variant'])!=(96,64,8,'oreduce'):raise ValueError('TP96 source contract')
    if [l['layer'] for l in g['layers']]!=list(range(40))+['head']:raise ValueError('whole40+head required')
    for layer in g['layers']:
        for pc,o in enumerate(layer['ops']):
            if pc!=o['id'] or o['kind'] not in KINDS:raise ValueError('instruction identity/kind')
            if o['kind']=='local' and (o['fn'] not in LOCAL or not hasattr(H.Executor,'f_'+o['fn'])):raise ValueError('unbound local kernel')
            if o['kind']=='mv' and (o['fn'] not in MATRIX or len(o['rows'])!=96):raise ValueError('matrix binding')
    return g


def compile_program(graph=None):
    g=validate(json.loads((ROOT/SOURCE).read_text()) if graph is None else graph)
    lowered=[];counts=Counter()
    for l in g['layers']:
        for o in l['ops']:
            fn=o.get('fn',o['kind']);counts[fn]+=1
            handler='f_'+fn if o['kind']=='local' else {'mv':'op_mv','all_gather':'op_gather','all_reduce':'op_reduce','topk_merge':'op_merge','kv_gather':'op_kv_gather','expert_fetch':'op_fetch'}[o['kind']]
            typed=o['kind']=='local' and fn in ['attend','hc_pre_norm','hc_post','final_norm','swiglu']
            lowered.append({'pc':len(lowered),'layer':l['layer'],'source_op_id':o['id'],'kind':o['kind'],'function':fn,
              'semantic_handler':handler,'software_executable':True,
              'numerical_backend':'TYPED_GPU_RECIPE_CPU' if typed else 'TYPED_SCALAR_RECIPES_WITH_REFERENCE_MACRO_GAPS_CPU',
              'lowering_steps':STEPS.get(fn,['EXACT_MATRIX_SOURCE_ORDER'] if o['kind']=='mv' else ['FINITE_SERVICE_CALLBACK']),
              'recipe_sources':RECIPES.get(fn,[]),
              'costs':{'issue_cycles':None,'RF_read_ports':2,'RF_write_ports':1,'registers_per_thread':None,
                       'shared_bytes':None,'shared_clock_GHz_candidate':0.9,'shared_bytes_per_fast_1p2GHz_cycle_limit':96,'shared_bytes_per_SM_cycle_limit':128,'shared_capacity_per_SM':65536,
                       'dependency_stall_cycles':None,'HBM_service_cycles':None,'collective_cycles':None,
                       'ordinary_INT_SFU_area_mm2':None,'routes_fit':None},
              'cost_status':'REQUIRES_RAM_COMPOSITION_AND_FULL_KERNEL_LOWERING','op':o})
    pins=[SOURCE,RESIDENT,'tools/w19_hbm_tp96_isa.py','tools/hdc_golden_v41.py','tools/hdc_golden.py',
          'tools/rtl_v41_fullshape_layer_campaign.py','tools/deepseek_hbm_complete_program.py','tools/deepseek_hbm_complete_executor.py','tools/deepseek_hbm_complete_memory.py','tools/deepseek_hbm_complete_isa.py','compiler/models/deepseek-v4.1-flash/inference_config.json','results/rtl/w17_v41_1m_reference_token.json']
    pins+=sorted({p for v in RECIPES.values() for p in v})
    return {'schema':'opentallas.deepseek.hbm.complete-program.v1','tp':96,'SMs_per_rank':32,'F32_lanes_per_SM':128,
       'position':g['position'],'variant':g['variant'],'instructions':lowered,'source_pins':{p:digest(p) for p in pins},
       'coverage':{'layers':40,'head':True,'operations':len(lowered),'functions':dict(counts),
                   'software_handlers_bound':len(lowered),'ordinary_GPU_numerical_operator_bindings':sum(counts[f] for f in ['attend','hc_pre_norm','hc_post','final_norm','swiglu']),
                   'full_GPU_instruction_lowering_complete':False},
       'entry':'checkpoint embedding current token + explicit initialKV only; never perlayer reference activation',
       'DUT_RTL_qualified':False,'full_token_software_executed':False,'full_token_physical_qualified':False,
       'provider_status':'software finite logical providers; actual DRAM/NoC/CDC provider timing not bound'}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise SystemExit('refuse overwrite evidence')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(compile_program(),indent=2)+'\n')
