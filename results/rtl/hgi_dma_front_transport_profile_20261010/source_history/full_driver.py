import concurrent.futures,hashlib,json,subprocess
from pathlib import Path
R=Path('/srv/opentallas-scratch/codex/dma-front-final-20261010')
base=R/'src';raw=(base/'ot_hgi_dma_front.sv').read_text()
assert raw.count('tg_dsec[tag_slot(i/NL,in[267:264])]')==1
mut=base/'tag_alias.sv';mut.write_text(raw.replace('tg_dsec[tag_slot(i/NL,in[267:264])]','tg_dsec[tag_slot(0,in[267:264])]'))
prod=dict(LDEPTH=256,DATA_HOPS=80,CREDIT_HOPS=80,RESPONSE_LATENCY=104,SERVICE_SLOTS=8,BW_SCOPE=1)
cases=[('default',{},False,False),('legacy_production',dict(prod,STACK_LOCAL_TAGS=0),True,False),('local_production',dict(prod,STACK_LOCAL_TAGS=1),False,False),('mut_bf16',dict(prod,STACK_LOCAL_TAGS=1,MUT=1),True,False),('mut_earlytag',dict(prod,STACK_LOCAL_TAGS=1,MUT=2),True,False),('mut_stackalias',dict(prod,STACK_LOCAL_TAGS=1),True,True)]
def run(c):
 name,params,negative,alias=c;d=R/name;d.mkdir(exist_ok=False)
 src=mut if alias else base/'ot_hgi_dma_front.sv';bench=base/'tb_hgi_dma_front.sv'
 cmd=['/srv/opentallas-scratch/admit.sh','8','--','verilator','--binary','--timing','-Wno-fatal','--top-module','tb_hgi_dma_front','--Mdir',str(d/'vlt'),'-j','8',*[f'-G{k}={v}' for k,v in params.items()],str(src),str(bench)]
 with (d/'build.log').open('w')as f:cp=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 r=dict(name=name,parameters=params,expected_negative=negative,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in(src,bench)},compile_exit=cp.returncode)
 if cp.returncode==0:
  with (d/'run.log').open('w')as f:sim=subprocess.run([str(d/'vlt/Vtb_hgi_dma_front'),'+FULL','+DMA_PROFILE'],stdout=f,stderr=subprocess.STDOUT)
  text=(d/'run.log').read_text();r.update(sim_exit=sim.returncode,exact_pass='PASS HGI_DMA_FRONT' in text and 'FAIL' not in text,negative_detected=('FAIL' in text or sim.returncode!=0))
  r['passed']=r['negative_detected']if negative else r['exact_pass']
 else:r['passed']=False
 (d/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as ex:
 for r in ex.map(run,cases):print(json.dumps(r),flush=True)
