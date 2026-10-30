import json,subprocess,hashlib,shutil
from pathlib import Path
R=Path('/srv/opentallas-scratch/claude/wt/codex-hbm-1030');S=Path(__file__).resolve().parent;O=R/'results/hbm_die_codex_1030/su_structural_bridges';O.mkdir(exist_ok=True)
get=lambda p:subprocess.check_output(['git','-C',str(R),'show','1f9fe3c3a:'+p],text=True)
hashf=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
allrows=json.load(open(S/'postcompose_descriptors_PREP.json'))['descriptors'];descriptors=[]
for physical in sorted({r['physical']['module']for r in allrows}):
 master=physical.removesuffix('__nocoll');bridge=physical+'__native_bridge';p=O/physical;p.mkdir(exist_ok=True)
 bf=p/(bridge+'.sv');bf.write_text(get('physical/die_plan/hbm_arch_cores/wrappers/'+bridge+'.sv'))
 full=p/(physical+'.sv');full.write_text(get('physical/die_plan/hbm_arch_cores/wrappers/'+physical+'.sv'))
 stub=p/'physical_bb.sv';shutil.copy(S/master/'physical_stub.sv',stub)
 ys=p/'fragment.ys';ys.write_text(f'read_verilog -lib -sv {stub}\nread_verilog -sv {bf}\nhierarchy -check -top {bridge}\nwrite_json {p}/fragment.json\n')
 proc=subprocess.run(['yosys','-Q','-T','-s',str(ys)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(p/'fragment.log').write_text(proc.stdout);assert proc.returncode==0
 rel=lambda x:str(x.relative_to(R))
 instances=[]
 for r in allrows:
  if r['physical']['module']!=physical:continue
  rr={k:r[k]for k in ['expected_module','expected_abi','physical']};rr['path']=r['inst'];rr['physical']['rtl_file']=rel(full);instances.append(rr)
 descriptors.append(dict(json=rel(p/'fragment.json'),json_sha256=hashf(p/'fragment.json'),top=bridge,source_files_sha256={rel(x):hashf(x)for x in [bf,full,stub]},instances=instances))
(O/'manifest_PREP.json').write_text(json.dumps(dict(structural_bridges=descriptors),indent=2)+'\n')
updates={r['physical_mapping']['path']:[r['physical_mapping']['part'],r['physical_mapping']['local']]for r in allrows}
(O/'map_parts_PREP.json').write_text(json.dumps(updates,indent=2)+'\n')
for n in ['check_expansion.py','expansion_receipt.json','all48_context_receipt.json','postcompose_descriptors_PREP.json']:shutil.copy(S/n,O/n)
shutil.copy(Path(__file__),O/'package_expansion.py')
print('PACKAGED',len(descriptors),'fragments',sum(len(d['instances'])for d in descriptors),'paths')
