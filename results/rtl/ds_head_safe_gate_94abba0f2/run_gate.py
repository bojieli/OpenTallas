import pathlib,sys,importlib.util,json,hashlib,subprocess,datetime,time,resource
root=pathlib.Path(__file__).resolve().parent;src=root/'src';out=root/'out';out.mkdir(exist_ok=True)
manifest=json.loads((root/'source_manifest.json').read_text())
def verify():
 assert all(hashlib.sha256((src/p).read_bytes()).hexdigest()==h for p,h in manifest['files'].items())
verify()
spec=importlib.util.spec_from_file_location('gate',src/'tools/test_fh_margin.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=src
record={'source_commit':manifest['commit'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verilator':subprocess.check_output(['verilator','--version'],text=True).strip(),'cases':{},'all_pass':True}
for name in manifest['selected_cases']:
 bench=m.BENCH[name]
 for variant,mut in [('baseline',None),*bench['mut'].items()]:
  d=out/(name+'__'+variant);d.mkdir(exist_ok=False);t=time.monotonic()
  r=m.run(name,bench,mut,str(d));binary=d/'obj'/('V'+bench['top'])
  built=binary.is_file()
  # Require an executed simulation assertion for negatives, never a compiler failure.
  ok=built and ((r['returncode']==0 and 'PASS' in r['output']) if mut is None else (r['returncode']!=0 and ('Fatal' in r['output'] or 'FATAL' in r['output'] or 'Assertion failed' in r['output'])))
  record['cases'][name+'/'+variant]={**r,'binary_built':built,'expected':'FAIL' if mut else 'PASS','ok':ok,'elapsed_s':time.monotonic()-t,'mutation':mut}
  record['all_pass'] &= ok
  (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
  print(name,variant,'PASS_GATE' if ok else 'FAIL_GATE',r['output'],flush=True)
verify();record['sources_unchanged_after']=True;record['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();record['max_child_rss_kib']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
(out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
sys.exit(0 if record['all_pass'] else 1)
