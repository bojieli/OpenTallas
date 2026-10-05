# Reuse the retained P8191 full-token comparison on the released P4095 reference.
# Invoke only after the existing runtime terminal; never launches a DUT/oracle.
from pathlib import Path
import hashlib,json,re,sys
R=Path('/srv/opentallas-scratch/jobs/laplace-qwen-plainar-stream4-P4095-r1')
S=Path('/srv/opentallas-scratch/claude/qwen-hbmacc-8k/src')
assert (R/'runtime.exit').read_text().strip()=='0', 'actual process exit0 required'
reference=json.loads((R/'full_reference.json').read_text())
o=Path(reference['oracle'])/'oracle.json'
assert hashlib.sha256(o.read_bytes()).hexdigest()==reference['oracle_sha256']
j=json.loads(o.read_text());assert j['status']=='ISA_golden_only'
assert j['input_book_sha256']==hashlib.sha256((R/'inputs/inputs.json').read_bytes()).hexdigest()
assert 'WRITEBACK drained=1' in (R/'runtime.log').read_text(), 'actual ACK drain required'
G=Path(reference['oracle'])/'P4095'
sys.path.insert(0,str(S/'tools'))
from qwen_rom_rt_token_w12_rm import e4m3
checks={};kv={};heads={};norms={}
for l in range(36):
 for d in range(4):
  n=f'L{l}_die{d}';p=R/'run'/(n+'_x.hex');w=G/f'L{l:02d}_die{d}_x.hex'
  got=[int(x,16) for x in p.read_text().split()] if p.exists() else []
  want=[int(x,16) for x in w.read_text().split()];assert len(want)==4096
  checks[n]=dict(words=len(got),mismatches=sum(a!=b for a,b in zip(got,want))+abs(len(got)-len(want)))
  j=json.loads((G/'kv_at_P'/f'L{l}_die{d}.json').read_text())
  p=R/'run'/(n+'_kvP.hex');rows=[x.split() for x in p.read_text().splitlines()] if p.exists() else []
  kv[n]={}
  for kind,key in [('K','k_bits'),('V','v_bits')]:
   got=[int(x[3],16) for x in rows if x[0]==kind];want=[e4m3(int(x,16)) for x in j[key]]
   assert len(want)==256
   kv[n][kind]=dict(codes=len(got),mismatches=sum(a!=b for a,b in zip(got,want))+abs(len(got)-len(want)))
h=json.loads((G/'head.json').read_text());expected=[h['next_token'],int(h['next_logit_bits'],16)]
for d in range(4):
 p=R/'run'/f'head_die{d}_result.hex';got=[int(x,16) for x in p.read_text().split()] if p.exists() else []
 heads[f'die{d}']=dict(actual=got,expected=expected,exact=got==expected)
 p=R/'run'/f'head_die{d}_xnorm.hex';w=G/f'head_die{d}_xnorm.hex'
 got=[int(x,16) for x in p.read_text().split()] if p.exists() else []
 want=[int(x,16) for x in w.read_text().split()];assert len(want)==4096
 norms[f'die{d}']=dict(words=len(got),mismatches=sum(a!=b for a,b in zip(got,want))+abs(len(got)-len(want)))
log=(R/'runtime.log').read_text();m=re.search(r'QWEN_ROM_STREAM4_PLAIN_AR_FULLTOKEN DONE stages=37 cycles=(\d+)',log)
stages=re.findall(r'^STAGE (\S+) done .*',log,re.M)
good=bool(m) and stages==[f'L{l}' for l in range(36)]+['head'] and all(x['mismatches']==0 for x in checks.values()) and all(x['mismatches']==0 for v in kv.values() for x in v.values()) and all(x['exact'] for x in heads.values()) and all(x['mismatches']==0 for x in norms.values())
result=dict(status='PASS' if good else 'FAIL',process_exit=0,position=4095,token=1165,stages=stages,cycles=int(m[1]) if m else None,layer_x=checks,kv=kv,head=heads,head_xnorm=norms,mode='plainAR nativeSTREAM4 tagged; near/DSpark/accept absent',physical_qualification=False)
(R/'full_numerical_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print('FINAL',result['status'],'cycles',result['cycles'],flush=True)
if not good:raise SystemExit(1)
