#!/usr/bin/env python3
"""Fresh exact NP4 producer with qualified CUDA, dynamic-KV layout and chunk-8 leaves.

All substitutions are process-local to this explicit successor. Original
producer/golden/SU/causal bounds/rank folds remain byte-identical. No retry,
resume, concurrent producer or unvalidated feature substitution is provided.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
FEATURE_LAYERS=(1,9,17,25,33)

def sha(path):
    with Path(path).open('rb') as stream:
        digest=hashlib.sha256()
        for data in iter(lambda:stream.read(1048576),b''):digest.update(data)
    return digest.hexdigest()

def require(value,message):
    if not value:raise ValueError(message)

def plan(args):
    require(args.position>0 and args.position+4<=8192,'NP4 needs a position at or before 8188')
    require(args.host_threads>0,'positive controlled host thread count required')
    require(sha(args.tokens)==args.tokens_sha256,'actual prompt changed')
    tokens=[int(t) for t in args.tokens.read_text().split()]
    require(len(tokens)>args.position and all(0<=t<(1<<18) for t in tokens), 'actual prompt/pending token required')
    require(tokens[args.position]==args.anchor,'actual pending token differs')
    require(not args.out.exists(),'fresh producer output required')
    for layer in range(34):
        for rank in range(4):
            require((Path(args.layer_dirs.format(layer=layer,die=rank))/f'layer{layer}_rom.json').is_file(),
                    f'actual retained TP4 layer {layer} rank {rank} missing')
    for path in (args.embedding_npz,args.snapshot/'config.json',args.draft_dir/'config.json',args.draft_dir/'model.safetensors'):
        require(path.is_file(),'actual released input missing: '+str(path))
    config=json.loads((args.draft_dir/'config.json').read_text())
    require(tuple(config['target_layer_ids'])==FEATURE_LAYERS,'released target-feature layer order differs')
    require(args.ptx.resolve()==(ROOT/'results/host/qwen_exact_cuda_matvec_20261004/qwen_exact_matvec.ptx').resolve(),
            'use the enrolled qualified PTX from this pinned source tree')
    check_engines(vectorized_chunk8=args.vectorized_chunk8,kv_layout=args.kv_layout)
    return dict(engine_selection='exact_cuda_matvec+vectorized_dynamic_kv'+('+vectorized_chunk8' if args.vectorized_chunk8 else '')+('+kv_layout' if args.kv_layout else ''),kv_layout=args.kv_layout,vectorized_chunk8=args.vectorized_chunk8,position=args.position,anchor=args.anchor,context_positions=args.position,
                target_layers=34,feature_layers=list(FEATURE_LAYERS),
                feature_shape=[args.position,20480],feature_payload_bytes=args.position*20480*4,
                tp=4,groups=6144,su_width=1024,kv_format='fp8',host_threads=args.host_threads,
                waiting_for_existing_gpu_pid=args.wait_for_pid,run_requested=args.run,
                scope='One actual feature/draft input producer; no numerical target outputs, DUT, acceptance or rate proof')


def check_engines(*,vectorized_chunk8=False,kv_layout=False):
    cuda=json.loads((ROOT/'results/host/qwen_exact_cuda_matvec_20261004/tiny_fixture.json').read_text())
    kv=json.loads((ROOT/'results/host/qwen_dynamic_kv_vectorized_20261004/r2/result.json').read_text())
    require(cuda['status']=='PASS' and len(cuda['cases'])==6 and all(c['bit_exact'] for c in cuda['cases']),
            'qualified CUDA exactness receipt required')
    require(kv['verdict']=='PASS_COMPONENT_EXACT_DYNAMIC_KV' and all(
        c['exact_uint32'] and c['same_read_addresses'] and c['same_scalar_operation_counts'] for c in kv['checks']),
        'qualified dynamic-KV exactness/readset receipt required')
    for name,digest in kv['source_sha256'].items():
        require(sha(ROOT/'tools'/name)==digest,'dynamic-KV qualified source differs: '+name)
    for name,key in (('tools/cuda/qwen_exact_matvec.cu','source_sha256'),
                     ('tools/qwen_rom_exact_cuda_matvec.py','wrapper_sha256'),
                     ('tools/qwen_rom_dspark_oracle_gpu_w12.py','oracle_sha256'),
                     ('tools/hdc_golden.py','golden_sha256'),
                     ('results/host/qwen_exact_cuda_matvec_20261004/qwen_exact_matvec.ptx','ptx_sha256')):
        require(sha(ROOT/name)==cuda[key],'CUDA qualified source/PTX differs: '+name)
    if vectorized_chunk8:
        reducer=json.loads((ROOT/'results/host/qwen_chunk8_reducer_vectorized_20261004/result.json').read_text())
        require(reducer['verdict']=='PASS_EXACT_HOST_CHUNK8_COMPONENT' and
                len(reducer['checks'])==18 and all(c['exact_uint32'] for c in reducer['checks']) and
                reducer['default_off_hook_pass'] and reducer['timing']['exact_uint32'],
                'qualified exact chunk-8 reducer required')
        for name,digest in reducer['source_sha256'].items():
            require(sha(ROOT/'tools'/name)==digest,'chunk-8 qualified source differs: '+name)

    if kv_layout:
        layout=json.loads((ROOT/'results/host/qwen_dynamic_kv_layout_20261004/r2/result.json').read_text())
        require(layout['verdict']=='PASS_EXACT_MATERIAL_HOST_COMPONENT_GAIN' and
                len(layout['checks'])==20 and all(t['exact_uint32'] for t in layout['timings']) and
                all(m['verdict']=='REJECTED' for m in layout['mutants']),
                'qualified exact dynamic-KV layout required')
        for name,digest in layout['source_sha256'].items():
            require(sha(ROOT/'tools'/name)==digest,'KV layout qualified source differs: '+name)


def require_gpu_idle(wait_for_pid):
    require(not (Path('/proc')/str(wait_for_pid)).exists(),'existing GPU owner PID still live; no concurrent producer')
    result=subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],
                          text=True,capture_output=True,check=True)
    require(not result.stdout.strip(),'GPU has a live compute owner; request its next slot')

def run(args,book):
    require_gpu_idle(args.wait_for_pid)
    # Set host-library worker counts before importing numerical code. This
    # controls local responsiveness, not job duration, output or RAM capacity.
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[name]=str(args.host_threads)
    for k,v in dict(QWEN_O4_GROUPS='6144',QWEN_O4_TP='4',HDC_SU_WIDTH='1024',HDC_KV_FMT='fp8').items():os.environ[k]=v
    sys.path.insert(0,str(ROOT/'tools'))
    import numpy as np
    import qwen_rom_dspark_oracle_gpu_w12 as gpu
    gpu.torch.set_num_threads(args.host_threads)
    gpu.torch.set_num_interop_threads(args.host_threads)
    gpu.torch.backends.cuda.matmul.allow_tf32=False
    require(gpu.TP==4 and gpu.PO.GROUPS==6144 and gpu.G.KV_FMT=='fp8' and gpu.I.SU_WIDTH==1024,
            'actual TP4/W8/FP8 GPU arithmetic contract required')
    from qwen_rom_exact_cuda_matvec import ExactMatvec
    from hdc_dynamic_kv_vectorized import me_dynamic_kv
    engine=ExactMatvec(args.ptx)
    engine.install(gpu)
    from hdc_reduce_chunked_vectorized_hook import install
    install(gpu.G,enabled=args.vectorized_chunk8)
    dynamic_me=me_dynamic_kv
    if args.kv_layout:
        from hdc_dynamic_kv_layout import me_dynamic_kv_layout
        dynamic_me=me_dynamic_kv_layout
    original_machine=gpu.GpuDieMachine
    class CombinedExactDieMachine(original_machine):
        def me(self,f,dyn):
            if f['me_wsrc']:
                return dynamic_me(self,f,dyn)
            return super().me(f,dyn)
    gpu.GpuDieMachine=CombinedExactDieMachine
    args.out.mkdir(parents=True)
    record=dict(schema='opentallas.qwen-dspark-oracle-gpu.v1',mode='first_block_inputs',**book)
    record.update(prompt_tokens_sha256=args.tokens_sha256,embedding_npz_sha256=sha(args.embedding_npz),
                  checkpoint_sha256={name:sha(args.draft_dir/name) for name in ('config.json','model.safetensors')},
                  source_sha256={name:sha(ROOT/name) for name in (
                      'tools/qwen_rom_dspark_np4_producer.py','tools/qwen_rom_dspark_oracle_gpu_w12.py',
                      'tools/qwen_rom_position_oracle_w12.py','tools/qwen_rom_dspark_drafter_golden.py',
                      'tools/hdc_golden.py','tools/hdc_program.py','tools/hdc_isa.py',
                      'tools/qwen_o4_layer0_oracle_w12.py','tools/qwen_o4_token_oracle_w12.py',
                      'tools/hdc_qwen_fullshape_program_w12.py','tools/hdc_qwen_fullshape_isa_w12.py',
                      'tools/qwen_rom_dspark_np4_optimized_producer.py',
                      'tools/qwen_rom_dspark_np4_optimized_chunk8_producer.py',
                      'tools/qwen_rom_dspark_np4_optimized_layout_producer.py',
                      'tools/hdc_dynamic_kv_layout.py','tools/test_hdc_dynamic_kv_layout.py',
                      'results/host/qwen_dynamic_kv_layout_20261004/r2/result.json',
                      'tools/hdc_reduce_chunked_vectorized.py','tools/hdc_reduce_chunked_vectorized_hook.py',
                      'tools/test_hdc_reduce_chunked_vectorized.py',
                      'results/host/qwen_chunk8_reducer_vectorized_20261004/result.json',
                      'tools/qwen_rom_exact_cuda_matvec.py','tools/cuda/qwen_exact_matvec.cu',
                      'tools/hdc_dynamic_kv_vectorized.py','tools/test_hdc_dynamic_kv_vectorized.py',
                      'results/host/qwen_exact_cuda_matvec_20261004/qwen_exact_matvec.ptx',
                      'results/host/qwen_exact_cuda_matvec_20261004/qwen_exact_matvec.json',
                      'results/host/qwen_exact_cuda_matvec_20261004/tiny_fixture.json',
                      'results/host/qwen_dynamic_kv_vectorized_20261004/r2/result.json')})
    output=args.out/'oracle.json'
    def save():output.write_text(json.dumps(record,indent=2)+'\n')
    record['status']='producing_features';save()
    features_path=args.out/'target_features.npy'
    features=np.lib.format.open_memmap(features_path,mode='w+',dtype='<f4',shape=(args.position,20480))
    tokens=[int(t) for t in args.tokens.read_text().split()][:args.position]
    emb=gpu.Emb(args.embedding_npz,args.snapshot)
    golden=gpu.Golden(args.layer_dirs,'',None,34,args.out)
    vms=[[gpu.fresh_vm(emb(t)) for _ in range(4)] for t in tokens]
    record['retained_vm_bytes']=sum(v.nbytes for ranks in vms for v in ranks)
    captured=[0]*5
    t0=time.time()
    def capture(layer,index,before,after,machines):
        # Literal source output X, all ranks checked; no expected features.
        if layer not in FEATURE_LAYERS:return
        x=[v[gpu.X_BASE:gpu.X_BASE+4096] for v in after]
        require(all(np.array_equal(gpu.G.bits(x[0]),gpu.G.bits(v)) for v in x[1:]),
                f'actual feature ranks disagree at layer {layer} position {index}')
        slot=FEATURE_LAYERS.index(layer)
        features[index,slot*4096:(slot+1)*4096]=x[0];captured[slot]+=1
        if index==args.position-1:
            features.flush();record['captured_positions_per_layer']=captured[:]
            record['layer_image_sha256']=golden.image_sha;save()
    golden.run_positions(tokens,list(range(args.position)),vms,capture)
    require(captured==[args.position]*5,'incomplete actual feature export')
    features.flush();record.update(target_feature_sha256=sha(features_path),target_feature_file=str(features_path.resolve()),
                                  target_feature_seconds=round(time.time()-t0,3),status='features_ready')
    save()
    # Release target working state before loading the trained draft weights.
    del vms,golden,emb
    gpu.GpuDieMachine.drop()
    drafter=gpu.Drafter(args.draft_dir)
    draft=drafter.draft(features,args.anchor,args.position,3)
    record.update(step1_draft=draft,
                  step1=dict(P=args.position,positions=list(range(args.position,args.position+4)),
                             block_tokens=[args.anchor]+draft['draft_tokens']),status='actual_draft_inputs_ready')
    save();print(json.dumps(record['step1']),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true')
    p.add_argument('--kv-layout',action='store_true',help='explicitly select qualified exact host KV affine views')
    p.add_argument('--vectorized-chunk8',action='store_true',help='explicitly select the qualified exact host reducer')
    p.add_argument('--ptx',type=Path,default=ROOT/'results/host/qwen_exact_cuda_matvec_20261004/qwen_exact_matvec.ptx')
    p.add_argument('--tokens',type=Path,required=True);p.add_argument('--tokens-sha256',required=True)
    p.add_argument('--position',type=int,default=8187);p.add_argument('--anchor',type=int,default=15)
    p.add_argument('--host-threads',type=int,default=1);p.add_argument('--wait-for-pid',type=int,default=2920874)
    p.add_argument('--layer-dirs',default='/home/ubuntu/qwen-dspark-oracle-run/img_tp4/L{layer}-d{die}')
    p.add_argument('--embedding-npz',type=Path,default=Path('/home/ubuntu/qwen-dspark-oracle-run/ref/realmem_gold/prompt_embedding.npz'))
    p.add_argument('--snapshot',type=Path,default=Path.home()/'.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218')
    p.add_argument('--draft-dir',type=Path,default=Path.home()/'.cache/huggingface/hub/models--deepseek-ai--dspark_qwen3_8b_block7/snapshots/03326e5043815da1f81b109078b2889737c26017')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();book=plan(a);print(json.dumps(book,indent=2),flush=True)
    if a.run:run(a,book)

if __name__=='__main__':main()
