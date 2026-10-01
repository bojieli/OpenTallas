"""Source-bound production-shape software proof and finite operation costs."""
import argparse,gzip,hashlib,json,subprocess
from collections import Counter
from pathlib import Path
import numpy as np
import deepseek_hbm_complete_index_blas as B
import deepseek_hbm_complete_index_consumer as C
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fixture(count,offset):
    rows=[];rawrows=[]
    specials=[0x7fc10001,0xffc20002,0x7f800000,0xff800000,0x7fff8000,0x7f7fffff,0,0x80000000]
    for index in range(count):
        raw=np.linspace(-3-index/128,5+index/64,128,dtype=np.float32)
        bits=raw.view(np.uint32)
        for block in range(4):bits[block*32+(index+block*7)%32]=specials[(index+block+offset)%len(specials)]
        rawrows.append(bits.copy());produced,_=B.E.produce(raw)
        with np.errstate(invalid='ignore',over='ignore'):expected=B.E.C.V.qdq_fp4_e8m0(raw)
        if not np.array_equal(produced.view(np.uint32),expected.view(np.uint32)):raise AssertionError('producer fixture mismatch')
        rows.append(produced)
    return np.array(rawrows),np.array(rows)
def build():
    qraw,q=fixture(32,0);kraw,keys=fixture(64,3)
    weights=np.linspace(-2,2,32,dtype=np.float32)
    weights.view(np.uint32)[::8]=[0x7fc50000,0xffc60000,0x7f800000,0xff800000]
    comparisons=[];counts=Counter();metrics=Counter()
    for n in [5456,5464,10920,10928,16384]:
        with np.errstate(invalid='ignore',over='ignore'):
            got,programs=B.source_sized_scores(q,keys,weights,n)
            # Full ORIGINAL macro shape; 64 distinct source-produced fixture
            # rows repeated explicitly for context, never called checkpoint KV.
            expected=C.reference_scores(q,keys[np.arange(n)%64],weights,np.arange(n))[:64]
        if not np.array_equal(got.astype(np.float64).view(np.uint64),expected.view(np.uint64)):raise AssertionError(f'full batch mismatch {n}')
        comparisons.append({'original_batch_size':n,'compared_keys':64,'actual_output_F32_bits':got.view(np.uint32).tolist(),
            'reference_F64_ABI_sha256':hashlib.sha256(expected.tobytes()).hexdigest(),'bit_exact':True})
        if n==5456:
            for p in programs:
                counts.update(p.counts)
                metrics.update({k:v for k,v in p.metrics.items() if k!='legacy_interpreter_proxy_cycles_NOT_service_budget'})
    # Explicit executed SSA witness for one selected warp from this actual64
    # fixture. Whole64 cost counts above; do not represent as whole64 SSA.
    _,trace=B.block(q[:,:32],keys[0,:32],trace=True)
    sources=['deepseek_hbm_complete_index_blas.py','deepseek_hbm_complete_index_blas_manifest.py',
        'deepseek_hbm_complete_index_exceptional.py','deepseek_hbm_complete_index.py',
        'deepseek_hbm_complete_index_codec.py','deepseek_hbm_complete_index_consumer.py',
        'w19_index32_integer_kernel.py','w19_gpu_compare_lowering.py','hdc_golden_v41.py','hdc_golden.py','w19_hbm_tp96_isa.py']
    return {'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256':{f'tools/{n}':sha(ROOT/'tools'/n) for n in sources},'runtime':B.pinned_runtime(),
        'fixture_kind':'64 distinct synthetic rawF32 keys and32 queries executed through actual source-compatible QDQ; not checkpoint rows',
        'raw_query_bits':qraw.tolist(),'raw_key_bits':kraw.tolist(),'produced_query_bits':q.view(np.uint32).tolist(),
        'produced_key_bits':keys.view(np.uint32).tolist(),'weight_bits':weights.view(np.uint32).tolist(),
        'full_original_batch_comparisons':comparisons,
        'executed_whole64_ordinary_warp_opcode_counts':dict(counts),'executed_whole64_metrics':dict(metrics),
        'selected_first_key_block_executed_virtual_SSA':trace.trace,
        'whole64_SSA_expanded':False,'legacy_proxy_cycles_used':False,
        'NaN_policies':{'DGEMM_FMA231':'current query, current key, accumulator; invalid negative canonical NaN',
            'block_csum':'left priority (source strided right operand)',
            'weight_multiply':'right priority (source contiguous/broadcast)',
            'head_chunk8':'right priority (source transpose-derived view)',
            'head_pairwise_tree':'left priority (source strided slices)'},
        'finite_block':'common-scale E2M1 twice-units IMUL/IADD then single integer RNE; no early FP32 product rounding',
        'RF_ports':'2R1W candidate, allocation and bank admission pending','RF_address_loop_regs':8,
        'RF_allocation':None,'peak_live_allocated_registers':None,'shared_peak_bytes':None,
        'shared_note':'sanitize staging and exception merge add traffic to63488B codec baseline; cannot adopt old lifetime fit',
        'canonical_opcode_cycles':None,'branch_reconvergence_cycles':None,'provider_writecommit_cycles':None,
        'area_mm2':None,'routing_tracks':None,'whole_token_composed_cycles':None,
        'coverage':'directed production-shape candidate; not exhaustive allF32 producer/weight domain or arbitrary original tail sizes',
        'production_dispatcher_bound':False,'FP64_candidate_compute_operations':0,'checkpoint_reads':0,
        'DUT_RTL_executed':False,'hardware_qualified':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    data=(json.dumps(build(),separators=(',',':'))+'\n').encode()
    Path(a.output).write_bytes(gzip.compress(data,mtime=0) if a.output.endswith('.gz') else data)
