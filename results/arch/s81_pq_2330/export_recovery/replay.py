"""Replay only abstract generation from a CLOSED immutable final ODB, never route."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads((D/'plan.json').read_text())
result={'passed':False,'input':r}
try:
 v=Path(r['run'])/'record/views'/r['cell']
 matches={f:sha(v/f)==h for f,h in r['published_hashes'].items()}
 if not all(matches.values()):raise ValueError('canonical record bytes differ: '+str(matches))
 odb=Path(r['immutable_final_odb']);odb_hash=sha(odb)
 command=['docker','run','--rm','-v',r['orfs_dir']+':/work:ro','-v',str(D)+':/out',r['image'],'/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/out/raw.tcl']
 run=subprocess.run(command,capture_output=True,text=True)
 (D/'raw_export.log').write_text(run.stdout+run.stderr)
 result.update(command=command,raw_export_returncode=run.returncode,odb_sha256=odb_hash)
 if run.returncode:raise ValueError('raw exporter failure')
 if sha(odb)!=odb_hash:raise ValueError('immutable final ODB changed')
 if sha(D/'raw.lef')!=r['raw_lef_expected']:raise ValueError('raw LEF not original exporter manifest hash')
 if sha(D/'helper.py')!=r['helper_sha256']:raise ValueError('helper hash mismatch')
 env=os.environ.copy()
 for key in ('OT_OBS_CLOSE','OT_OBS_CLOSE_UM'):env.pop(key,None)
 command=[sys.executable,str(D/'helper.py'),str(D/'raw.lef'),str(D/'final.lef')]
 run=subprocess.run(command,env=env,capture_output=True,text=True)
 (D/'processor.log').write_text(run.stdout+run.stderr)
 result.update(helper_command=command,helper_returncode=run.returncode,helper_stdout=run.stdout,helper_stderr=run.stderr)
 if run.returncode:raise ValueError('historical helper failure')
 if sha(D/'final.lef')!=r['published_hashes'][r['cell']+'.lef']:raise ValueError('final LEF differs from immutable published record')
 result.update(passed=True,raw_sha256=sha(D/'raw.lef'),final_sha256=sha(D/'final.lef'),published_files_verified=matches,
   environment={'OT_OBS_CLOSE':None,'OT_OBS_CLOSE_UM':None},environment_basis='Original process environment was not recorded. Replay explicitly cleared both options and reproduced the exact published output hash.')
except Exception as exc:
 result['error']=str(exc)
(D/'replay.json').write_text(json.dumps(result,indent=2)+'\n')
print(r['job'], 'PASS' if result['passed'] else 'FAIL '+result['error'],flush=True)
sys.exit(0 if result['passed'] else 1)
