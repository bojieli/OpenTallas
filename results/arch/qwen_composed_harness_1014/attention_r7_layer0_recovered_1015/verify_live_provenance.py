import pathlib,hashlib,json
base=pathlib.Path('/srv/opentallas-scratch/claude/qwen-wholetoken-1014');a=base/'lv6_hier/attn_rtlfp_r7_shim';checks={}
for name in ['attn_r7_positive','attn_r7_mutant_l0r3']:
 d=base/'qfunc_rtlfp_2328'/name;cm=json.loads((d/'core_arithmetic.json').read_text())
 for group in ['source_sha256','archives_sha256']:
  for p,w in cm[group].items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==w,p
 count=0
 for line in(d/'inputs.sha256').read_text().splitlines():
  h,p=line.split(None,1);assert hashlib.sha256(pathlib.Path(p.strip()).read_bytes()).hexdigest()==h,p;count+=1
 h,p=(d/'binary.sha256').read_text().strip().split(None,1);assert hashlib.sha256(pathlib.Path(p.strip()).read_bytes()).hexdigest()==h
 checks[name]=dict(input_files=count,binary_sha256=h,core_sources=len(cm['source_sha256']),core_archives=len(cm['archives_sha256']))
for f in ['source.sha256','archives.sha256','binary.sha256','reused_r6.sha256','build_inputs.sha256']:
 count=0;drift=[];root=pathlib.Path('/srv/opentallas-scratch/codex/native-service-f46073090') if f=='source.sha256' else a/'obj'
 for line in(a/f).read_text().splitlines():
  if not line.strip():continue
  h,p=line.split(None,1);p=pathlib.Path(p.strip());p=p if p.is_absolute()else root/p
  actual=hashlib.sha256(p.read_bytes()).hexdigest()
  if actual!=h:
   assert str(p)==str(base/'build_attn_hier_shim.sh') and h=='7489da2e70a6c65d4b1437012f8564a747675ca993e540010076b61d31708e71'
   drift.append(dict(path=str(p),expected=h,current=actual,note='Original recipe recovered exactly from836c057712; later2322b7be63 script is not the historical build recipe.'))
  else:count+=1
 checks[f]=dict(verified=count,drift=drift)
print(json.dumps(checks))
