import concurrent.futures,hashlib,json,pathlib,re,subprocess
root=pathlib.Path('/srv/opentallas-scratch/claude/q-vmwb/run2')
cases=json.loads(pathlib.Path('cases.json').read_text())
variants=['pos','imut1']
binaries={v:hashlib.sha256((root/('b_'+v)/'obj/Vtb_vmwb').read_bytes()).hexdigest() for v in variants}
assert binaries['pos']=='9061cc828e66d7599b123dfc8cd8e37c9ba71743eb693ba9932877ef0a314a52'
def run(pair):
 v,c=pair
 r=subprocess.run([str(root/('b_'+v)/'obj/Vtb_vmwb'),*c['args']],capture_output=True,text=True)
 pathlib.Path(v+'_PC'+str(c['pc'])+'.log').write_text(r.stdout+r.stderr)
 data=json.loads(next(l for l in r.stdout.splitlines() if l.startswith('{')))
 passed='PASS vmwb' in r.stdout
 assert passed==(v=='pos'),(v,c['pc'],data)
 assert data['bursts']==c['markers'],data
 if passed:assert data['rows']==0 and data['vm_rows_checked']==0 and data['errors']==0,data
 return dict(variant=v,pc=c['pc'],observed=data,passed=passed)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:runs=list(pool.map(run,[(v,c) for v in variants for c in cases]))
out=dict(scope='Head NULL-marker projection only: cached bench forces amax=0; programmed amax/row0/amc and head arithmetic not served. Actual ctl/24 ports/issuer/serializers/real mapped VM, head timing fields unchanged.',binaries=binaries,cases=cases,runs=runs,ok=True)
pathlib.Path('receipt.json').write_text(json.dumps(out,indent=2)+'\n')
print('HEAD NULL MARKERS PASS cases',len(runs),'positive markers',sum(c['markers'] for c in cases))
