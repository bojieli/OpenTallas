import concurrent.futures,hashlib,json,subprocess
from pathlib import Path
R=Path('/srv/opentallas-scratch/codex/dma-front-random-20261010');base=R/'src'
prod=dict(LDEPTH=256,DATA_HOPS=80,CREDIT_HOPS=80,RESPONSE_LATENCY=104,SERVICE_SLOTS=8,BW_SCOPE=2,STACK_LOCAL_TAGS=1)
cases=[('local_random',prod,False),('mut_earlytag_random',dict(prod,MUT=2),True)]
def run(c):
 name,params,negative=c;d=R/name;d.mkdir(exist_ok=False)
 src=base/'ot_hgi_dma_front.sv';bench=base/'tb_hgi_dma_front.sv'
 cmd=['/srv/opentallas-scratch/admit.sh','8','--','verilator','--binary','--timing','-Wno-fatal','--top-module','tb_hgi_dma_front','--Mdir',str(d/'vlt'),'-j','8',*[f'-G{k}={v}'for k,v in params.items()],str(src),str(bench)]
 with (d/'build.log').open('w')as f:cp=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 r=dict(name=name,parameters=params,expected_negative=negative,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in(src,bench)},compile_exit=cp.returncode,source_mode='random gaps, no bandwidth assertion')
 if cp.returncode==0:
  with (d/'run.log').open('w')as f:sim=subprocess.run([str(d/'vlt/Vtb_hgi_dma_front'),'+DMA_PROFILE'],stdout=f,stderr=subprocess.STDOUT)
  text=(d/'run.log').read_text();r.update(sim_exit=sim.returncode,exact_pass='PASS HGI_DMA_FRONT'in text and'FAIL'not in text,negative_detected=('FAIL'in text or sim.returncode!=0))
  r['passed']=r['negative_detected']if negative else r['exact_pass']
 else:r['passed']=False
 (d/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as ex:
 for r in ex.map(run,cases):print(json.dumps(r),flush=True)
