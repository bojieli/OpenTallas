import concurrent.futures,hashlib,importlib.util,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=json.load(open(ROOT/'plan.json')); results=[]
for row in rows:
 d=ROOT/row['job'];d.mkdir(exist_ok=True)
 try:
  vd=Path(row['run'])/'record/views'/row['cell']
  matches={f:sha(vd/f)==h for f,h in row['published_hashes'].items()}
  if not all(matches.values()):raise RuntimeError('published record files mismatch '+str(matches))
  cmd=['docker','run','--rm','-v',row['orfs_dir']+':/work:ro','-v',row['orfs_dir']+':/in:ro','-v',str(d)+':/out',row['image'],'/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/out/raw.tcl']
  for mount in row.get('macro_mounts', []):
   md=ROOT/mount['relative_dir']
   if not all(sha(md/f)==h for f,h in mount['hashes'].items()):raise RuntimeError('immutable macro input hash mismatch')
   cmd[3:3]=['-v',str(md)+':'+mount['target']+':ro']
  a=subprocess.run(cmd,capture_output=True,text=True);(d/'raw_export.log').write_text(a.stdout+a.stderr)
  if a.returncode:raise RuntimeError('raw export returncode '+str(a.returncode))
  raw=d/'raw.lef';rawhash=sha(raw)
  if rawhash!=row['raw_lef_expected']:raise RuntimeError('raw hash mismatch '+rawhash+' != '+row['raw_lef_expected'])
  env=os.environ.copy()
  for k in ['OT_OBS_CLOSE','OT_OBS_CLOSE_UM']:env.pop(k,None)
  a=subprocess.run(['python3',str(d/'helper.py'),str(raw),str(d/'final.lef')],env=env,capture_output=True,text=True);(d/'processor.log').write_text(a.stdout+a.stderr)
  if a.returncode:raise RuntimeError('postprocessor returncode '+str(a.returncode))
  after=sha(d/'final.lef')
  if after!=row['published_hashes'][row['cell']+'.lef']:raise RuntimeError('final output differs from published '+after)
  spec=importlib.util.spec_from_file_location('helper_'+row['job'].replace('-','_'),d/'helper.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
  before=raw.read_text();final=(d/'final.lef').read_text();bh,_=h.split_lef(before);ah,_=h.split_lef(final);bs,bpg=h.pin_rects(bh);asp,apg=h.pin_rects(ah)
  invariant={'macro_name_unchanged':re.search(r'\bMACRO\s+(\S+)',before).group(1)==re.search(r'\bMACRO\s+(\S+)',final).group(1),'outline_unchanged':re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',before).groups()==re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',final).groups(),'signal_pin_names_unchanged':set(bs)==set(asp),'original_signal_pin_rectangles_retained':all(set(rs)<=set(asp[p]) for p,rs in bs.items()),'power_pin_rectangles_unchanged':bpg==apg}
  if not all(invariant.values()):raise RuntimeError('geometry invariant failed '+str(invariant))
  result=dict(row,passed=True,raw_sha256=rawhash,final_sha256=after,helper_sha256=sha(d/'helper.py'),environment={'OT_OBS_CLOSE':None,'OT_OBS_CLOSE_UM':None},environment_basis='Reconstruction replay cleared both options; original process environment was not recorded. Exact published output hash is reproduced.',invariants=invariant,processor_summary=a.stdout.strip(),published_files_verified=matches)
 except Exception as e:
  result=dict(row,passed=False,error=str(e))
 (d/'replay.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result);print(row['job'],'PASS' if result['passed'] else 'FAIL '+result['error'],flush=True)
(ROOT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
sys.exit(0 if all(r['passed'] for r in results) else 1)
