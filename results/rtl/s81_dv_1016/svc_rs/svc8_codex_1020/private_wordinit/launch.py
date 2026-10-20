import concurrent.futures,hashlib,json,re,shutil,subprocess
from pathlib import Path
R=Path('/srv/opentallas-scratch/claude/s81-svc8-1020')
A=R/'out_codex_mapped_probe_randommem';O=R/'out_codex_private_wordinit';B=O/'obj'
assert not O.exists(), 'Preserve prior private coupon'
O.mkdir();subprocess.run(['cp','-a','--reflink=auto',str(A/'obj'),str(B)],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
identity={'status':'PREPARED_PRIVATE_COUPON','source_manifest':(A/'source_identity.sha256').read_text(),'runtime_source':'/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include/verilated.cpp','patched_files':[],'constructors':[],'unchanged_archive_members':{},'TB_scope':'ov every sampled edge from1 including reset; payload/fault iff either ov; no reset/warmup comparison exclusion','reset_stimulus':'unchanged reset4/warm8/preload20/inflight reset180..184/inputresume192'}
for line in identity['source_manifest'].splitlines():
 h,p=line.split('  ',1);assert sha(Path(p))==h,(p,'source drift')
identity['runtime_sha256']=sha(Path(identity['runtime_source']))
# Per-address salt is private initialization instrumentation, never a shared memory or DUT edit.
pattern=re.compile(r'(?P<lhs>vlSelf->(?P<field>tb_svc8_mapped__DOT__(?P<kind>gold|cand)__DOT__[^;]+?__DOT__arr)\[__Vi0\]) = VL_SCOPED_RAND_RESET_Q\(64, __VscopeHash, (?P<salt>\d+)ull\);')
K=0x9e3779b97f4a7c15;MASK=(1<<64)-1;salts=[]
for name in ['Vtb_svc8_mapped___024root__332__Slow.cpp','Vtb_svc8_mapped___024root__383__Slow.cpp']:
 p=B/name;old=p.read_text();matches=list(pattern.finditer(old));assert len(matches)==17,(name,len(matches))
 def replacement(m):
  base=int(m['salt']);row={'file':name,'kind':m['kind'],'field':m['field'],'base_salt':base};identity['constructors'].append(row)
  for address in range(32):salts.append((base^(((address+1)*K)&MASK)))
  salt=f'({base}ull ^ (static_cast<uint64_t>(__Vi0 + 1) * 0x9e3779b97f4a7c15ULL))'
  assign=f'{m["lhs"]} = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, {salt});'
  audit=f'\n        VL_PRINTF("SVC8_WORD_INIT kind={m["kind"]} instance={base} address=%d value=%016llx seed=%u salt=%016llx\\n", __Vi0, static_cast<unsigned long long>({m["lhs"]}), Verilated::threadContextp()->randSeed(), static_cast<unsigned long long>({salt}));'
  return assign+audit
 new=pattern.sub(replacement,old);p.write_text(new);identity['patched_files'].append({'file':name,'old_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_sha256':sha(p),'scope':'17 SRAM constructor assignments and read-only init audit only; all other bytes unchanged'})
assert len(salts)==len(set(salts))==1088
seedkeys=[x^seed for seed in [1,2,3]for x in salts];assert len(seedkeys)==len(set(seedkeys))==3264
identity['distinct_instance_address_seed_keys']=len(seedkeys);identity['distinct_bit_identities']=len(seedkeys)*64
# Exact generated monitor guard change, independent of all DUT/eval/data-path code.
p=B/'Vtb_svc8_mapped___024root__0.cpp';old=p.read_text();guard='if (VL_LTES_III(32, 0x0000000cU, vlSelfRef.tb_svc8_mapped__DOT__cycle)) {';assert old.count(guard)==1
newguard='if (VL_LTES_III(32, 0x00000001U, vlSelfRef.tb_svc8_mapped__DOT__cycle)) {'
causal='\n            if (vlSelfRef.tb_svc8_mapped__DOT__cycle == 2 && VL_TESTPLUSARGS_I("coupon_early_observer")) { VL_PRINTF("SVC8_EARLY_OBSERVER_CAUSAL cycle=2\\n"); VL_FATAL_MT("private_coupon_tb.v", 1, "", "SVC8_EARLY_OBSERVER_CAUSAL"); }'
new=old.replace(guard,newguard+causal);p.write_text(new);identity['patched_files'].append({'file':p.name,'old_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_sha256':sha(p),'scope':'TB comparison threshold12->1 and optional early observer causal control; no DUT state/eval changes'})
p=B/'Vtb_svc8_mapped___024root__0__Slow.cpp';old=p.read_text();assert old.count('initial_compare_from=12')==1;new=old.replace('initial_compare_from=12','initial_compare_from=1');p.write_text(new);identity['patched_files'].append({'file':p.name,'old_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_sha256':sha(p),'scope':'TB banner only'})
tb=(A/'tb.v').read_text();assert tb.count('if(cycle>=12)begin')==1
(O/'private_coupon_tb.v').write_text(tb.replace('initial_compare_from=12','initial_compare_from=1').replace('if(cycle>=12)begin','if(cycle>=1)begin\n   if(cycle==2 && $test$plusargs("coupon_early_observer"))$fatal(1,"SVC8_EARLY_OBSERVER_CAUSAL");'))
# Verify every unmodified generated source/header and all cached runtime objects match the original.
changed={x['file']for x in identity['patched_files']}
for p in sorted((A/'obj').iterdir()):
 if p.is_file()and p.name not in changed and p.suffix in ['.cpp','.h','.o','.a','.gch']:
  assert sha(p)==sha(B/p.name),p.name
# Capture actual archive member identities; only four generated compile groups may change.
def archive_members(path):
 names=subprocess.check_output(['ar','t',str(path)],text=True).splitlines()
 return {n:hashlib.sha256(subprocess.check_output(['ar','p',str(path),n])).hexdigest()for n in names}
before=archive_members(A/'obj/Vtb_svc8_mapped__ALL.a');identity['archive_original_sha256']=sha(A/'obj/Vtb_svc8_mapped__ALL.a')
allowed={'Vtb_svc8_mapped_vm_classes_0.o','Vtb_svc8_mapped_vm_classes_Slow_0.o','Vtb_svc8_mapped_vm_classes_Slow_13.o','Vtb_svc8_mapped_vm_classes_Slow_15.o'}
# Recompile only the four touched groups; use the original actual compiler commands byte-for-byte.
lines=(A/'build.log').read_text().splitlines();targets=[]
for name in sorted(allowed):
 cpp=name[:-2]+'.cpp';commands=[x for x in lines if x.startswith('g++ ')and x.endswith(' -c '+cpp)];assert len(commands)==1,(cpp,len(commands));targets.append((name,commands[0]))
(O/'compile_commands.json').write_text(json.dumps(targets,indent=2)+'\n')
def compile_one(row):
 name,command=row
 with (O/(name+'.build.log')).open('w')as f:r=subprocess.run(command,cwd=B,shell=True,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(name,r.returncode)
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:list(pool.map(compile_one,targets))
subprocess.run(['ar','r',str(B/'Vtb_svc8_mapped__ALL.a'),*sorted(allowed)],cwd=B,check=True)
after=archive_members(B/'Vtb_svc8_mapped__ALL.a');assert set(before)==set(after)
for n,h in before.items():
 if n not in allowed:assert h==after[n],n
identity['archive_member_changes']={n:{'before':before[n],'after':after[n]}for n in before if before[n]!=after[n]};assert set(identity['archive_member_changes'])<=allowed
link=next(x for x in lines if x.startswith('g++ ')and x.endswith(' -o sim'))
subprocess.run(link,cwd=B,shell=True,check=True);identity['binary_sha256']=sha(B/'sim');identity['archive_new_sha256']=sha(B/'Vtb_svc8_mapped__ALL.a');identity['status']='BUILT_PRIVATE_INITIALIZATION_AND_OBSERVER_ONLY'
(O/'identity.json').write_text(json.dumps(identity,indent=2)+'\n');print('SVC8_PRIVATE_WORDINIT_BUILT',identity['binary_sha256'],'independent_seed_keys',len(seedkeys),'bit_identities',len(seedkeys)*64,flush=True)
results=[]
for seed in [1,2,3]:
 log=O/f'run_s{seed}.log'
 with log.open('w')as f:r=subprocess.run([str(B/'sim'),f'+seed={seed}','+verilator+rand+reset+2',f'+verilator+seed+{seed}'],stdout=f,stderr=subprocess.STDOUT,cwd=B)
 text=log.read_text();audit=[x for x in text.splitlines()if x.startswith('SVC8_WORD_INIT ')];assert len(audit)==1088,(seed,len(audit))
 values=[re.search(r'value=([0-9a-f]+)',x).group(1)for x in audit];assert len(values)==len(set(values))==1088
 verdict=[x for x in text.splitlines()if x.startswith(('SVC8_MAPPED_PASS','SVC8_MAPPED_MISMATCH'))];row={'seed':seed,'rc':r.returncode,'distinct_initial_memory_words':len(set(values)),'verdicts':verdict};results.append(row);print(json.dumps(row),flush=True)
 if r.returncode!=0:break
(O/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
# The early observer causal control proves an event at edge2 reaches the unmasked monitor.
if len(results)==3 and all(x['rc']==0 for x in results):
 with (O/'early_observer_mutant.log').open('w')as f:r=subprocess.run([str(B/'sim'),'+seed=1','+verilator+rand+reset+2','+verilator+seed+1','+coupon_early_observer'],stdout=f,stderr=subprocess.STDOUT,cwd=B)
 text=(O/'early_observer_mutant.log').read_text();assert r.returncode!=0 and 'SVC8_EARLY_OBSERVER_CAUSAL cycle=2' in text
 print('SVC8_EARLY_OBSERVER_CAUSAL_REJECTED',r.returncode,flush=True)
print('SVC8_PRIVATE_WORDINIT_COMPLETE',flush=True)
