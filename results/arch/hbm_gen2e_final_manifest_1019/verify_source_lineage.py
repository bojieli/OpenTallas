import argparse,pathlib,json,subprocess,hashlib
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);args=p.parse_args()
A=pathlib.Path(__file__).resolve().parent;B=A.parent
assert subprocess.check_output(['git','-C',args.repo,'rev-parse','--show-toplevel'],text=True).strip()==str(pathlib.Path(args.repo).resolve())
d=json.loads((A/'corrected_verified_receipts.json').read_text());paths={}
for rows in d.values():
 for r in rows.values():
  if not isinstance(r,dict):continue
  for path,v in r.get('input_hashes',{}).items():paths.setdefault(path,set()).add(v)
out={}
for path,actual in paths.items():
 if path.startswith('v16w/'):
  q=B/'vplan_a/wrap'/pathlib.Path(path).name;source=str(q);expected=hashlib.sha256(q.read_bytes()).hexdigest() if q.exists() else None
 else:
  cmd=subprocess.run(['git','-C',args.repo,'show','6f783d0a1:'+path],capture_output=True);expected=hashlib.sha256(cmd.stdout).hexdigest() if cmd.returncode==0 else None;source='6f783d0a1:'+path
 out[path]={'expected_source':source,'expected_sha256':expected,'actual_sha256':sorted(actual),'match':expected is not None and actual=={expected}}
(A/'corrected_source_lineage.json').write_text(json.dumps(out,indent=2)+'\n')
bad=[path for path,r in out.items() if not r['match']];print({'count':len(out),'mismatch':bad})
raise SystemExit(bool(bad))
