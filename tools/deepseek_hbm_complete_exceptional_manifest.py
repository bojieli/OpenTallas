"""Archive executed virtual-register identities, not a physical RF calendar."""
import contextlib,hashlib,io,json,os,platform,subprocess
from pathlib import Path
import numpy as np
import deepseek_hbm_complete_index_exceptional as E
import deepseek_hbm_complete_index_consumer as C
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    bits=np.resize(np.array([0,0x80000000,1,0x7f7fffff,0x7e800000,0x7f400000],np.uint32),128)
    bits[0]=0x7fff8000;bits[32]=0x7f800000;bits[64:96]=0;bits[96]=0xffc12345
    receipt=E.witness(bits.view(np.float32),'exceptional-mixed-row-r1')
    raw=np.zeros(128,np.uint32);raw[0]=0x7fc10001;raw[17]=0xffc20002
    with np.errstate(invalid='ignore'):
        q=E.C.V.qdq_fp4_e8m0(raw.view(np.float32));queries=np.tile(q,(32,1));keys=np.ones((2,128),np.float32)
        v=C.reference_modules();one=v.dots_q4(queries,keys[:1]);two=v.dots_q4(queries,keys)
    runtime=io.StringIO()
    with contextlib.redirect_stdout(runtime):np.show_runtime()
    libraries=list(Path(np.__file__).resolve().parent.parent.glob('numpy.libs/*openblas*.so'))
    names=['deepseek_hbm_complete_index_exceptional.py','deepseek_hbm_complete_exceptional_manifest.py','deepseek_hbm_complete_index.py','deepseek_hbm_complete_index_codec.py','deepseek_hbm_complete_index_consumer.py','deepseek_hbm_complete_canonical.py','hdc_golden_v41.py','hdc_golden.py','w19_hbm_tp96_isa.py']
    return {'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256':{f'tools/{n}':sha(ROOT/'tools'/n) for n in names},
        'executed_producer':receipt,
        'score_counterexample':{'raw_producer_input_bits':raw.tolist(),'actual_produced_query_bits':q.view(np.uint32).tolist(),
            'query_shape':list(queries.shape),'key_values':'all F32 one','key_shapes':[[1,128],[2,128]],
            'key_strides_bytes':list(keys.strides),'query_strides_bytes':list(queries.strides),
            'one_key_first_output_bits':int(one[0,0].view(np.uint32)),
            'two_key_first_output_bits':int(two[0,0].view(np.uint32)),
            'verdict':'REJECT shape-independent sequential FP64 NaN policy; source BLAS microkernel order still unbound'},
        'runtime':{'numpy':np.__version__,'python':platform.python_version(),'OPENBLAS_NUM_THREADS':os.environ.get('OPENBLAS_NUM_THREADS'),
            'numpy_runtime':runtime.getvalue(),'library_sha256':{str(p):sha(p) for p in libraries}},
        'physical_RF_allocation':None,'physical_provider':None,'whole_phase_cost_admitted':False,
        'checkpoint_reads':0,'hardware_qualified':False,
        'unresolved':['physical register allocation and version lifetime join','all-domain score BLAS operand/order/NaN lowering','integer opcode ports/latencies','whole-phase leases and writecommit/ACK visibility']}
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    Path(args.output).write_text(json.dumps(build(),indent=2)+'\n')
