#!/usr/bin/env python3
"""One source-identical GEN8 diagnostic continuation; never edits the failed run."""
import hashlib,json,os,subprocess,sys,shutil
from pathlib import Path
BASE='5f2ce19bc57cc98c941aad2362d4c7a855498171'
B=Path('/srv/opentallas-scratch/claude/qwen-kvsys')
old=B/'kvs14r-5f2ce19bc-gen8v3mub'
w=Path.cwd(); commit=subprocess.check_output(['git','rev-parse','--short=9','HEAD'],text=True).strip()
r=B/f'kvs14r-{commit}-gen8v4mub'
def git(*a): return subprocess.check_output(['git',*a],text=True)
changed=git('diff','--name-only',BASE,'HEAD').splitlines()
assert all(p=='tools/qwen_kv_die/chain/kvsys_prep.sh' or p.startswith('results/arch/kv_gen8_v4_1019/') for p in changed),changed
assert 'PREP FAIL' in (old/'STATUS.log').read_text() and '$2: unbound variable' in (old/'prep.log').read_text()
for pid in (758542,1455125,1493373): assert not Path(f'/proc/{pid}').exists(),f'old PID {pid} live'
assert not r.exists(),f'refuse reuse {r}'
# Compare every actual tracked tool/RTL/view dependency in the old and new
# worktrees. Never use git in the old worktree, and never trust a source label alone.
oldw=B/'wt-kvs14r-5f2ce19bc-gen8v3mub'
dep_rows=[]
for rel in git('ls-tree','-r','--name-only',BASE,'--','tools','rtl','physical').splitlines():
 if rel=='tools/qwen_kv_die/chain/kvsys_prep.sh': continue
 a=oldw/rel; b=w/rel
 if a.is_symlink() or b.is_symlink():
  assert a.is_symlink() and b.is_symlink() and os.readlink(a)==os.readlink(b),rel
  dep_rows.append([rel,'link',os.readlink(a)])
 else:
  ah=hashlib.file_digest(a.open('rb'),'sha256').hexdigest()
  bh=hashlib.file_digest(b.open('rb'),'sha256').hexdigest()
  assert ah==bh and (a.stat().st_mode&0o777)==(b.stat().st_mode&0o777),rel
  dep_rows.append([rel,ah])
print('ACTUAL_DEPENDENCY_HASH_GUARD PASS',len(dep_rows),flush=True)
subprocess.run(['cp','-a','--reflink=auto',str(old),str(r)],check=True)
def manifest(root):
 out={}
 for p in sorted(root.rglob('*')):
  if p.is_symlink(): out[str(p.relative_to(root))]={'link':os.readlink(p)}
  elif p.is_file(): out[str(p.relative_to(root))]={'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),'size':p.stat().st_size}
 return out
original=manifest(old); copied=manifest(r); assert original==copied
(r/'dependency_manifest.json').write_text(json.dumps(dep_rows)+'\n')
assert (r/'case_kv/SOURCE_COMMIT').read_text().strip()=='5f2ce19bc'
(r/'STATUS.log').rename(r/'v3_STATUS.log')
(r/'v3_manifest.json').write_text(json.dumps(original,indent=1)+'\n')
(r/'continuation.json').write_text(json.dumps(dict(original_source=BASE,driver_source=git('rev-parse','HEAD').strip(),unchanged_dependencies=['tools except chain/kvsys_prep.sh','rtl','physical'],changed_paths=changed,old_run=str(old),run=str(r),reuse='full byte-identical snapshot before first orientation; no hardlinks',qualification='PARAM_DIAG NOT_A_DIE_RESULT; OT_PIN_ALIGN FAIL1001 WARN20340 preserved'),indent=1)+'\n')
prep=(w/'tools/qwen_kv_die/chain/kvsys_prep.sh').read_text(); tail=prep[prep.index('kv_orient() {'):]
header='#!/bin/bash\nset -eu\nO='+str(r)+'\nS='+str(w)+'\ncd "$S"\nsource "$O/kv_flags.env"\nH14="--host-v14 --host-north --host-trees --v143 --reserve-native-astk"\nEXP="--expanded $O/expand.json"\n'
resume=r/'resume_prep.sh'; resume.write_text(header+tail)
(r/'prep_tail_sha256.txt').write_text(hashlib.sha256(tail.encode()).hexdigest()+'\n')
subprocess.run(['python3','tools/qwen_kv_die/kv_place_orient.py','--case',str(r/'case_kv'),'--report',str(r/'orientation_preflight.json'),'--check-only'],check=True)
# The original chain exports exactly its original flags, then resumes at first orientation.
chain=(w/'tools/qwen_kv_die/chain/kvs14r.sh').read_text()
needle='bash tools/qwen_kv_die/chain/kvsys_prep.sh $R > $R/prep.log 2>&1'
assert chain.count(needle)==1
chain=chain.replace(needle,'bash '+str(resume)+' > $R/prep_v4_resume.log 2>&1').replace('$R/prep.log','$R/prep_v4_resume.log')
launch=r/'continue_chain.sh'; launch.write_text(chain)
os.environ.update(KVS14R_TAG='gen8v4mub',KVS14R_REF='codex/kv-gen8-v4-1019',OT_KV_MU='1',OT_KV_BOOT_AGES='1',OT_KV_SCHED_STRICT='1',OT_KV_DCAL_BC='1',OT_KV_PARAM_DIAG='1')
# Output originals stay immutable; SOURCE_COMMIT intentionally remains the generated source.
print('V4_REUSE_HASH_GUARD PASS',len(original),'files',str(r),flush=True)
os.execv('/bin/bash',['bash',str(launch),commit])
