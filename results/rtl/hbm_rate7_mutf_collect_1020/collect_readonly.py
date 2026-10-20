import hashlib,json,os,re
from pathlib import Path
B=Path('/srv/opentallas-scratch/claude/hbm-rate7-1020/suvop')
records=['qw8_softmax_max','qw8_bf16_p','qw8_pv_normalize','qw8_round_q','qw8_row_scale_qkv']
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
files=[]
for x in re.findall(r'(?:\$S/[^\s\\]+\.sv|(?:rtl|physical)/[^\s\\]+\.(?:sv|v)|tb_toksim_su_top\.sv)',(B/'run_toksim_su.sh').read_text()):
 x=x.replace('$S','rtl/hbm_accel/generic/adapters/static_su')
 if x not in files:files.append(x)
files+=['run_toksim_su.sh','run_mutf.sh','build.summary','obj_mr10/Vtb_toksim_su_top__verFiles.dat','obj_mr10/Vtb_toksim_su_top']
source={x:dict(sha256=digest(B/x),bytes=(B/x).stat().st_size,mtime_ns=(B/x).stat().st_mtime_ns) for x in files}
inputs={};witness={}
for rec in records:
 root=B/'vec_tp8'/rec
 inputs[rec]={str(p.relative_to(root)):dict(sha256=digest(p),bytes=p.stat().st_size)
   for p in sorted(root.rglob('*')) if p.is_file() and p.suffix not in ('.log',) and p.name!='compile.txt'}
 witness[rec]={x:dict(sha256=digest(root/x),tail=(root/x).read_text().splitlines()[-24:]) for x in ['sim_mr10_POS.log','sim_mr10_MUT_FORCE.log']}
print(json.dumps(dict(root=str(B),source_observed_now=source,record_inputs=inputs,witnesses=witness,
  qualification=False,scope='Terminal component PRETREE0/MULTIRATE0/COLLPORT0 profile mr10 RR12 WR10; NOT current PRETREE1 or release-token qualification'),indent=2))
