import glob,subprocess,gzip,hashlib,json
from pathlib import Path
base=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM');out=Path('/work');libs=[];hashes={}
for name in ['AO','INVBUF','OA','SEQ','SIMPLE']:
 files=list(base.glob('asap7sc7p5t_'+name+'_RVT_TT_nldm_*lib*'))
 if len(files)!=1:raise ValueError(files)
 src=files[0];dst=out/(name+'.lib');raw=gzip.decompress(src.read_bytes()) if src.suffix=='.gz' else src.read_bytes();dst.write_bytes(raw);libs.append(dst);hashes[src.name]=hashlib.sha256(src.read_bytes()).hexdigest()
(out/'library_hashes.json').write_text(json.dumps(hashes,indent=1)+'\n')
for top in ['qkd_kvs_grp_s5','qkd_kvs_grp_h_s5']:
 cmd='; '.join(['read_liberty -lib '+str(p) for p in libs]+['read_verilog -lib /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir_bb.v','read_verilog /work/'+top+'.sv','hierarchy -check -top '+top,'synth -top '+top,'check','write_verilog -noattr /work/'+top+'.mapped.v'])
 with (out/(top+'.resynth.log')).open('w') as h:rc=subprocess.run(['yosys','-p',cmd],stdout=h,stderr=subprocess.STDOUT).returncode
 print(top,'RESYNTH',rc,flush=True)
 if rc:raise SystemExit(rc)
