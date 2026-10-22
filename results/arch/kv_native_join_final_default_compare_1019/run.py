import pathlib, subprocess, json, hashlib, re, os, time
r=pathlib.Path(__file__).resolve().parent; os.chdir(r)
assert not (r/'receipt.json').exists()
m=json.loads((r/'manifest.json').read_text())
for f in m['sources']: assert hashlib.sha256((r/f['path']).read_bytes()).hexdigest()==f['sha256'],f['path']
v=str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
version=subprocess.check_output([v,'--version'],text=True); (r/'version.log').write_text(version); assert '5.050' in version
receipt={'candidate_revision':m['candidate_revision'],'hostname':os.uname().nodename,'version':version,'started':time.time(),'builds':[],'cases':[]}
def save(): (r/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
for family,top,srcs in [('scheduler','scheduler_descriptor_baseline',['scheduler_compare.sv','scheduler_candidate.sv','scheduler_baseline.sv']),('core','disabled_core_compare',['disabled_core_compare.sv','core_candidate.sv'])]:
 cmd=['/usr/bin/time','-v',v,'--binary','--timing','-Wno-fatal','--top-module',top,'--Mdir','obj_'+family,'-j','2']+srcs
 with (r/(family+'_build.log')).open('x') as log: rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
 receipt['builds'].append({'family':family,'command':cmd,'exit':rc}); save()
 if rc: raise SystemExit(rc)
 binary=r/('obj_'+family)/('V'+top); sha=hashlib.sha256(binary.read_bytes()).hexdigest()
 for case in range(26) if family=='scheduler' else [0]:
  cmd=[str(binary)]+(['+CASE='+str(case)] if family=='scheduler' else [])
  name=f'{family}_case{case}.log'
  with (r/name).open('x') as log: rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
  output=(r/name).read_text(); expected=f'FINAL_DEFAULT_SCHED_PASS outputs=70 case={case} ' if family=='scheduler' else 'DISABLED_CORE_PASS edges=257'
  receipt['cases'].append({'family':family,'case':case,'exit':rc,'binary_sha256':sha,'expected_found':expected in output}); save()
  if rc or expected not in output: raise SystemExit(rc or 1)
low=high=edges=0
for case in range(26):
 s=(r/f'scheduler_case{case}.log').read_text(); match=re.search(r'DEFAULT_ELIGIBILITY_COVER edges=(\d+) low=(\d+) high=(\d+)',s); assert match,s
 e,l,h=map(int,match.groups()); edges+=e; low+=l; high+=h
assert low>0 and high>0, (low,high)
receipt.update(verdict='BOUNDED_PASS',scheduler_compared_edges=edges,certificate_attempt_eligibility_low=low,certificate_attempt_eligibility_high=high,finished=time.time()); save(); print('FINAL_DEFAULT_COMPARE_BOUNDED_PASS',edges,low,high)
