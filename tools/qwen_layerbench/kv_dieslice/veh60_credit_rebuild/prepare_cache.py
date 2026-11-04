#!/usr/bin/env python3
"""PREP ONLY: copy 51 immutable child ABI/archive packets; no Verilator/make."""
import hashlib,json,re,shlex,shutil,sys
from pathlib import Path
D=Path(sys.argv[1]).resolve();old=Path('/srv/opentallas-scratch2/claude/codex-kv-veh60-gen1-1131/b');obj=old/'obj';B=D/'b';B.mkdir(exist_ok=True);O=B/'obj';O.mkdir(exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(8<<20),b''):h.update(x)
 return h.hexdigest()
assert sha(old/'tb_kvslice.sv')==json.loads((D/'credit_delta_receipt.json').read_text())['baseline_sha256']
assert sha(obj/'Vtb_kvslice')=='25c672e3f5ac32a06a1e88c8bf0acdbfd7ffc90c657d001a6008759009f5127c'
a=shlex.split((obj/'Vtb_kvslice__hierMkArgs.f').read_text());src=[];args=[];children=[]
for d in sorted(obj.iterdir()):
 if d.is_dir() and list(d.glob('lib*.a')):
  target=O/d.name;target.mkdir(exist_ok=True)
  for f in d.iterdir():
   if f.is_file() and f.suffix in ['.sv','.h','.a']:
    q=target/f.name
    if not q.exists():shutil.copy2(f,q);q.chmod(0o444)
    assert sha(f)==sha(q)
    children.append(dict(source=str(f),snapshot=str(q),size=f.stat().st_size,sha256=sha(q)))
assert len({Path(x['source']).parent for x in children})==51
precision=[]
for child in sorted({Path(x['source']).parent for x in children}):
 for cpp in child.glob('*Syms*.cpp'):
  vals=re.findall(r'timeprecision\(([^)]*)\)',cpp.read_text())
  if vals:
   assert vals==['-15'],(cpp,vals)
   precision.append(dict(path=str(cpp),sha256=sha(cpp),timeprecision=vals))
assert len(precision)==51

for tok in a:
 if tok=='--binary':args+=['--main','--exe'];continue
 if tok=='--build':continue
 if tok==str(old/'tb_kvslice.sv'):tok=str(B/'tb_kvslice.sv')
 elif not tok.startswith('-') and tok.endswith('.sv') and not Path(tok).is_absolute():
  p=obj/tok;assert p.is_file(),p;tok=str(O/tok)
 if not tok.startswith(('-','+')) and tok.endswith(('.sv','.v','.vlt')):
  p=Path(tok);assert p.is_file(),p
  if p!=B/'tb_kvslice.sv':src.append(dict(path=str(p),size=p.stat().st_size,sha256=sha(p)))
 args.append(tok)
assert args[args.index('--threads')+1]=='1'
assert args[args.index('-CFLAGS')+1]=='-O1'
assert args[args.index('--timescale')+1]=='1ns/1ps'
assert '--build' not in args and '--binary' not in args
# No top files are copied: every new top C++/object will be compiled freshly.
# Child source/headers/archives are byte-copied private files, never symlinks/hardlinks.
vl=(old/'vl.f').read_text().replace(str(old/'tb_kvslice.sv'),str(B/'tb_kvslice.sv'))
(B/'vl.f').write_text(vl)
(B/'top_args.f').write_text('\n'.join(shlex.quote(x) for x in args)+'\n')
libs=[str(Path(x['snapshot']).relative_to(O)) for x in children if x['snapshot'].endswith('.a')]
assert len(libs)==51
(D/'child_libs.json').write_text(json.dumps(libs,indent=2)+'\n')
for name in ['phy_slice_map.json','native_boot.profile','native_boot_abi.json','vehicle_closure.json','tb_kvslice.clocks.json']:
 shutil.copy2(old/name,B/name)
inputs=Path('/srv/opentallas-scratch2/claude/kv-fn-7/veh60/runs/tok_gen1_nwB/nwB/inputs.sha256')
shutil.copy2(inputs,D/'baseline_run_inputs.sha256')
meta={'status':'PREP_ONLY_NOT_RUN','baseline_binary_sha256':sha(obj/'Vtb_kvslice'),'baseline_root':str(old),'child_count':51,'total_precision_constructors_expected':52,'private_child_files':children,'private_child_bytes':sum(x['size'] for x in children),'unchanged_hdl_inputs':src,'child_precision':precision,'candidate_tb_sha256':sha(B/'tb_kvslice.sv'),'top_rebuild':'all new top C++/objects; unchanged private child archives only','context':{'threads':1,'cflags':'-O1','clock_period_ps':833,'precision_fs':1},'production_rtl_changes':0,'added_arithmetic_cycles':0}
(D/'cache_receipt.json').write_text(json.dumps(meta,indent=2)+'\n');(D/'.keep').touch();print(json.dumps({k:v for k,v in meta.items() if k not in ['private_child_files','unchanged_hdl_inputs']}))
