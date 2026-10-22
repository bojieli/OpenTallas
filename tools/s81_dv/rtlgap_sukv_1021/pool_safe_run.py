#!/usr/bin/env python3
"""Minimum full 512-feature pool numerical witness, then ordinary native census."""
import sys,subprocess,json,hashlib,shutil
from pathlib import Path
variant=sys.argv[1];assert variant in ('main','alternate')
root=Path.cwd();base=root.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rtl=root/(sys.argv[2] if len(sys.argv)>2 else f'pool_safe_{variant}.sv');tb=root/(sys.argv[3] if len(sys.argv)>3 else 'tb_pool_native.sv')
record={'variant':variant,'source_sha256':{str(p.relative_to(root)):sha(p) for p in (rtl,tb,Path(__file__))},'numerical':{},'native':None}
def save(): (root/'result.json').write_text(json.dumps(record,indent=2)+'\n')
vl=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
cmd=[str(vl),'--binary','--timing','-O1','-fno-dfg','--unroll-count','4','-Wno-fatal','-Wno-MULTIDRIVEN','--top-module','tb_pool_native','-Mdir',str(root/'obj'),'-j','8',str(rtl),str(tb),'-CFLAGS','-O1']
with open('build.log','w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
record['build_returncode']=r.returncode;save();assert r.returncode==0
exe=root/'obj/Vtb_pool_native';record['binary_sha256']=sha(exe)
for tag,args in [('positive',[]),('swap_kv',['+SWAP_KV'])]:
 d=root/tag;d.mkdir(exist_ok=True)
 for n in ('img_main.mem','exp_cp.mem','exp_cp32.mem'):shutil.copyfile(base/'hard_rq/L2'/n,d/n)
 record.setdefault('runtime_images_sha256',{})[tag]={p.name:sha(p) for p in d.glob('*.mem')}
 r=subprocess.run([str(exe)]+args,cwd=d,capture_output=True,text=True)
 (d/'run.log').write_text(r.stdout+r.stderr)
 ok=(r.returncode==0 and 'POOL_NATIVE_PASS' in r.stdout) if tag=='positive' else (r.returncode!=0 and 'POOL_MISMATCH' in r.stdout and 'POOL_NATIVE_FAIL' in r.stdout)
 record['numerical'][tag]={'returncode':r.returncode,'ok':ok,'lines':[x for x in r.stdout.splitlines() if x.startswith('POOL_')]};save();assert ok,tag
# Normal source synthesis and mapped-native census. Neither source waivers nor a mapped override.
cmd=['docker','run','--rm','-v',f'{root}:/work','-w','/OpenROAD-flow-scripts/flow','openroad/orfs:asap7lock','make','-B','DESIGN_CONFIG=/work/native.mk','WORK_HOME=/work/native','synth']
with open('synth.log','w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
record['synth_returncode']=r.returncode;save();assert r.returncode==0
L='/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM'
cmd=['docker','run','--rm','-v',f'{root}:/work','-w','/work','openroad/orfs:asap7lock','python3','tools/ref_tile/native_census.py','--netlist','/work/native/results/asap7/ot_s81sl_cmp_pool/base/1_2_yosys.v','--top','ot_s81sl_cmp_pool']
for n in ('asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz','asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz','asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz','asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz','asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib'):cmd+=['--liberty',f'{L}/{n}']
cmd+=['--out','/work/native_census.json']
with open('native.log','w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
p=root/'native_census.json';j=json.loads(p.read_text());record['native']={k:j[k] for k in ('status','limit','max_dynamic_loads','roots_examined')};record['native']['report_sha256']=sha(p)
record['native']['worst']=sorted(j['driver_counts'],key=lambda x:x['loads'],reverse=True)[:30];save()
print(json.dumps(record,indent=2));sys.exit(0 if j['status']=='PASS' else 1)
