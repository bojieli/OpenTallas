import os, sys, json, hashlib, time
from pathlib import Path
for k,v in {'QWEN_O4_GROUPS':'6144','QWEN_O4_TP':'4','HDC_SU_WIDTH':'1024','HDC_KV_FMT':'fp8','QWEN_O4_AR_WORDS':'256','OMP_NUM_THREADS':'1'}.items(): os.environ[k]=v
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools'))
import numpy as np
import torch
import qwen_rom_position_oracle_gpu as g
root=Path(sys.argv[1]).resolve()
def words(p): return np.array([int(x,16) for x in p.read_text().split()],dtype=np.uint32)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
g.need_env()
assert torch.cuda.is_available()
t=time.time()
T=g.torch_golden(torch.device('cuda'))
m=g.GpuTP(T,Path(sys.argv[2]).resolve(),[],head=True)
progs, program_shas=g.head_programs(m.prep)
vm=torch.zeros((4,m.VM_ELEMS),dtype=torch.float32,device=T.dev)
inputs=[]
for rank in range(4):
    p=root/f'L0_die{rank}_x.hex'; w=words(p); assert len(w)==4096
    vm[rank,m.VM['X']:m.VM['X']+4096]=torch.from_numpy(w.view(np.float32)).to(T.dev)
    inputs.append({'rank':rank,'sha256':sha(p),'words':len(w)})
print('HEAD_ONLY_GPU_START actual_produced_L0_X layers=[]',flush=True)
expected, logits=m.run_head(vm,24,8191,progs)
norm=vm[:,8192:12288].cpu().numpy().view(np.uint32)
ranks=[]
for rank in range(4):
    actual=words(root/f'head_die{rank}_result.hex')
    nactual=words(root/f'head_die{rank}_xnorm.hex')
    ranks.append({'rank':rank,'actual_token':int(actual[0]),'actual_logit_bits':f'{int(actual[1]):08x}',
                  'winner_exact':int(actual[0])==expected['next_token'] and f'{int(actual[1]):08x}'==expected['next_logit_bits'],
                  'xnorm_words':len(nactual),'xnorm_mismatches':int(np.count_nonzero(nactual!=norm[rank]))})
result={'scope':'P8191 token24 actual E -> L0 -> head component chain; not full36 token',
        'runtime_exit':int((root/'runtime.exit').read_text()),'runtime_pid':2344404,
        'runtime_root':'/srv/opentallas-scratch/jobs/laplace-qwen-P8191-E-L0-head-r1',
        'actual_source':'db289ef05','cycles':20503,'edges':20511,
        'timing':'SIM_ONLY shared-row service excluded from performance claims',
        'comparison':'Existing GPU head oracle only, initialized from newly produced L0 X; no decoder replay or expected intermediate injection',
        'inputs':inputs,'head_program_sha256':program_shas,'expected':expected,'ranks':ranks,
        'elapsed_s':time.time()-t,'exact':all(r['winner_exact'] and r['xnorm_mismatches']==0 for r in ranks)}
(root/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
raise SystemExit(0 if result['exact'] else 1)
