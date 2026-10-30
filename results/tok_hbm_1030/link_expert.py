"""Build and test native expert input loads from the qualified chain's outputs."""
import argparse,copy,json,runpy,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];p=Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools');sys.path[:0]=[str(root/'tools/hbm_next'),str(p/'hbm_next'),str(p),'/home/ubuntu/OpenTallas/tools']
import isa_rows as IR,vm_expert_entry as E,vm_phase_shadow as S
from hgi_sim import machine as M,records as R
base=Path(__file__).parent
ap=argparse.ArgumentParser();ap.add_argument('--chain',type=Path,default=base/'capacity_mtp_tail/link6');ap.add_argument('--out-dir',type=Path,default=base/'expert_tail');args=ap.parse_args();chain=args.chain;packet=json.loads((chain/'chain.json').read_text());expert=json.loads((base/'expert/expert.json').read_text());required=json.loads((base/'expert/required_source_inputs.json').read_text());ALL=(1<<len(R.UNITS))-1
# Run the actual whole native chain and its mutant controls, obtaining the
# independent canonical output values for the verified sector selector ABI.
sys.argv=[str(root/'results/tok_hbm_2249/check_chain.py'),'--shadow',str(chain),'--values',str(base/'pipeline_expert/values0')]
ns=runpy.run_path(sys.argv[0]);final=ns['FINAL'];hbm=M.Hbm()
for s in packet['final_output_sectors']:
    a,b=s['source_words'];addr,end=s['hbm_range'];hbm.add(addr,final[a:b].copy(),f'source_{a}')
loads=[];manifest=[];blob=bytearray()
for lo,hi in required:
    for selector in packet['final_output_sectors']:
        a,b=selector['source_words'];begin=max(lo,a);end=min(hi,b)
        if begin>=end:continue
        target=E.translate(begin,expert['segments']);hb=selector['hbm_range'][0]+4*(begin-a)
        if begin%8 or end%8 or target%8:raise ValueError('native expert load lacks whole sector')
        S.native_capacity(hb,4*(end-begin))
        rec=R.Rec('DMA','LOAD',wait=ALL,desc=dict(A=R.MDesc(space='HBM',fmt='U32',base=hb,n=end-begin,m=1),O=R.MDesc(space='VM',fmt='U32',base=target,n=end-begin,m=1)))
        data=IR.encode(rec,None);manifest.append(dict(source_words=[begin,end],hbm_range=[hb,hb+4*(end-begin)],vm_words=[target,target+end-begin],offset=len(blob),bytes=len(data)));blob.extend(data);loads.append(rec)
die=M.Die(0,hbm);machine=M.Machine([die]);count=0
for rec in loads:machine.cur=rec;M.u_dma_load(machine,rec,0)
for lo,hi in required:
    dest=E.translate(lo,expert['segments']);assert np.array_equal(final[lo:hi],die.vm[dest:dest+hi-lo]),'canonical source expert input differs';count+=hi-lo
bad=copy.deepcopy(loads[0]);bad.desc['A'].base+=32;machine.cur=bad
try:
    M.u_dma_load(machine,bad,0)
    for lo,hi in required:
        dest=E.translate(lo,expert['segments']);assert np.array_equal(final[lo:hi],die.vm[dest:dest+hi-lo])
except(AssertionError,M.Fault):control='wrong_native_epoch_caught'
else:raise AssertionError('wrong native epoch escaped')
out=args.out_dir;out.mkdir(parents=True,exist_ok=True);(out/'loads.hgi1r').write_bytes(blob);(out/'loads.json').write_text(json.dumps(dict(records=manifest,required_source_words=required,words=count,bytes=count*4,native_loads=len(loads),control=control,whole_programme_executable=False,scratch_reserved=False,numeric_expert_execution=False),indent=1)+'\n')
print(json.dumps(dict(canonical_expert_input_words=count,native_loads=len(loads),control=control)))
