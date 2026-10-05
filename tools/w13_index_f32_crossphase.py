"""Source-bound index lifetime candidate, explicit missing runtime/service evidence."""
import ast,hashlib,json,subprocess
from pathlib import Path


def blob(rev,path):return subprocess.check_output(['git','show',rev+':'+path])

def layout():
    return {'query_units':[0,16384],'keys_or_block_results':[16384,49152],'descriptors':[49152,51200],
      'transpose_or_score_output':[51200,59392],'query_exponents':[59392,59904],
      'key_exponents':[59904,60928],'return_slots':[60928,61440]}


def phases():
    out=[{'id':'ingress','deps':[],'scratch_live_bytes':4224,'requires':['actual producer bytes','format/epoch read lease','matching controller return','scatter visible'], 'tick':None},
         {'id':'decode','deps':['ingress'],'scratch_live_bytes':0,'requires':['all max scan loads before same word overwrite','complete decode branch choice for actual source bits','query/key exponent visible'],'tick':None}]
    for b in range(4):
        start=16384+b*8192
        out.append({'id':f'score{b}','deps':['decode'] if b==0 else [f'copy{b-1}'],'input_region':[start,start+8192],
           'output_region':[51200,59392],'warp_count':64,'resident_wave_size_max':32,'minimum_waves':2,
           'requires':['all input key consumers done before copy overwrites units','all64 warp output stores visible','query and exponent leases remain live'],'tick':None})
        out.append({'id':f'copy{b}','deps':[f'score{b}'],'from_region':[51200,59392],'to_region':[start,start+8192],
           'shared_read_bytes':8192,'shared_write_bytes':8192,'ordinary_LOAD_STORE_warp_issues':128,
           'requires':['RF import before store','store visible before scratch reuse'],'tick':None})
    out.append({'id':'head_finish','deps':['copy3'],'requires':['four block results visible','source eight ordered FADD including four zero-adds','BF16 then MAX(+0) then FMUL weights then BF16','source shuffle reduction and BF16','actual final score store visible','reader consumer done then credit return'],'tick':None})
    return out


def build():
    path='tools/deepseek_hbm_complete_index.py';src=blob('bb38a691e',path);tree=ast.parse(src)
    score=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='scores')
    graphpath='results/rtl/deepseek_hbm_complete_20261001/whole-program-calendar-r2.json';gb=blob('1c37cdaa9',graphpath);g=json.loads(gb)
    rawpath='results/rtl/deepseek_hbm_complete_20261001/checkpoint-full-40-head-r1.json';rb=blob('9b1db53f5',rawpath);raw=json.loads(rb)
    ops=[o for o in g['operations'] if o['function']=='index_scores']
    receipts={r['pc']:r for r in raw['operator_receipts']}
    callbacks=[]
    for o in ops:
        r=receipts[o['pc']]
        for key in ['pc','layer','source_op_id','function']:assert r[key]==o[key]
        cb=o['actual_software_callbacks']
        assert r['completed']==cb['completed'] and r['CPU_wall_s']==cb['CPU_wall_s']
        assert r['numerical_backend']==cb['numerical_backend_at_execution']
        callbacks.append({'pc':o['pc'],'layer':o['layer'],'dependencies':o['dependencies'],'source_op_id':o['source_op_id'],
          'raw_callback':r,'instruction_branch_trace':None,'RF_shared_service_ticks':None,'per_key_source_bits':None,
          'callback_scope':'whole reference handler completion; NOT candidate ordinary instruction runtime path'})
    copies=[]
    for b in range(4):
      for warp in range(64):
        copies.append({'id':f'copy{b}:{warp}','op_pair':['LOAD32','STORE32'],'source_words':[12800+warp*32+j for j in range(32)],
           'destination_words':[4096+b*2048+warp*32+j for j in range(32)],'banks':list(range(32)),
           'deps':[f'score{b}:all_output_stores_visible'],'RF_reads_per_lane':1,'RF_write_ports':1,'RF_write_read_copies':2,
           'launch':None,'RF_ready':None,'store_visible':None})
    return {'schema':'w13.index-f32-crossphase.v1','source_pins':{path:{'git':'bb38a691e','sha256':hashlib.sha256(src).hexdigest()},graphpath:{'git':'1c37cdaa9','sha256':hashlib.sha256(gb).hexdigest()},rawpath:{'git':'9b1db53f5','sha256':hashlib.sha256(rb).hexdigest()}},
      'scores_source_AST_sha256':hashlib.sha256(ast.dump(score,include_attributes=False).encode()).hexdigest(),
      'actual_callbacks':callbacks,'candidate_source_matches_actual_instruction_backend':False,
      'layout':layout(),'allocation_end_bytes':61440,'capacity_bytes':65536,
      'earlier_57472_allocation_excludes_score_output_scratch':True,
      'without_phase_reuse_peak_bytes':65664,'without_phase_reuse_fits':False,
      'lifetime_plan':phases(),'source_input_to_units_same_word_aliasing_verified':False,
      'ordinary_copy_events':copies,'score_copy_extra_shared_read_write_bytes':65536,
      'score_copy_extra_LOAD_STORE_warp_issues':512,
      'resident_geometry':{'lanes':128,'warps':32,'registers_per_thread':32,'RF_read_ports':2,'RF_write_ports':1},
      'runtime_branch_choices':None,'whole_score_operand_liveness_allocation':None,
      'warp_residency_schedule':None,'other_client_bank_interference':None,'unknown_instruction_variants_latency':None,
      'source_nonfinite_consumer_domain':'existing decode rejects Inf/NaN; source semantic fallback consumer pending',
      'clock_target_GHz':{'fabric':1.2,'serial':0.9},'physical_SS_FF':None,
      'physical_admission':'FAIL_CLOSED','rate_credit':0,'hardware_launch':False,'baseline_066_preserved':True}

if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(json.dumps(build(),indent=2)+'\n')
