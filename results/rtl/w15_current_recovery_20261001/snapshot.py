import pathlib,json,hashlib,shutil,subprocess,datetime
root=pathlib.Path(__file__).resolve().parents[3];out=root/'results/rtl/w15_current_recovery_20261001';rows=[]
for case in ['port_board','port_qwen','tm89_500']:
 p=pathlib.Path('/tmp/claude-1000/w15p/out')/case;dest=out/'physical'/case;dest.mkdir(parents=True,exist_ok=True)
 for name in ['physical.json','signoff_ssff.json']:
  f=p/name
  if not f.exists():continue
  shutil.copy2(f,dest/name);d=json.loads(f.read_text());rows.append({'case':case,'file':str((dest/name).relative_to(root)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'status':d.get('status'),'source_commit':d.get('git',{}).get('commit'),'corner':d.get('corner'),'flow_completed':d.get('flow_completed'),'timing':{k:v.get('timing') for k,v in d.get('corners',{}).items()}})
for f in pathlib.Path('/tmp/claude-1000/w15b/out2').glob('*hbm96*.json'):
 dest=out/'hbm96';dest.mkdir(exist_ok=True);shutil.copy2(f,dest/f.name);d=json.loads(f.read_text());pins={p:hashlib.sha256(subprocess.check_output(['git','show',d['git']+':'+p],cwd=root)).hexdigest()==h for p,h in d['source_sha256'].items()};assert all(pins.values());rows.append({'case':f.stem,'source_commit':d['git'],'all_exact':d['all_exact'],'pins_verified':True,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
queues={}
for name in ['lane_pve2a','lane_pve2b','lane_pve2d','lane5_133h','lane6_133']:
 p=pathlib.Path('/tmp/claude-1000/w15b/jobs')/name;queues[name]=p.read_text()
(out/'snapshot.json').write_text(json.dumps({'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'claim_boundary':'Immutable terminal snapshots and simulation intake. Local port_qwen is an older terminal record while another port_qwen route remains live; never use it as the live result. No physical closure adoption.','artifacts':rows,'existing_queues':queues,'remaining_policy':'Reuse five live W15 jobs. Do not duplicate HBM96 exact simulations or SRAM campaign. Board route exit247 requires resource review; no identical rerun on 13-18GiB available VM. Outstanding fullshape topk physical route remains prerequisite. tm89_500 SS/FF timing is positive but physical status not_met, not signoff PASS.'},indent=2)+'\n')
print('SNAPSHOT_PASS',len(rows))
