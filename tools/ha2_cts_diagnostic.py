#!/usr/bin/env python3
"""Replay one unchanged CTS attempt in a private copy, dumping its failure state."""
import argparse, hashlib, json, pathlib, shlex, shutil, subprocess
p=argparse.ArgumentParser();p.add_argument('--recovery',required=True);p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args()
old=pathlib.Path(a.recovery).resolve();out=pathlib.Path(a.out).resolve();out.mkdir(exist_ok=False)
r=json.loads((old/'recovery.json').read_text());image=r['image_id']
assert r['status']=='FAILED_CTS'
work=out/'orfs';shutil.copytree(old/'orfs',work)
script=pathlib.Path(__file__).with_name('ha2_cts_diagnostic.tcl');shutil.copy2(script,out/'cts_diagnostic.tcl')
original='/OpenROAD-flow-scripts/flow/scripts/cts.tcl'
s=subprocess.run(['docker','run','--rm','--entrypoint','cat',image,original],check=True,capture_output=True)
(out/'original_cts.tcl').write_bytes(s.stdout)
command=r['commands']['cts'][:-1]
for f in sorted((work/'results').rglob('*')):
 if f.is_file():command+=['-o','/work/'+str(f.relative_to(work))]
command+=['do-4_1_cts']
shell='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '+shlex.join(command)
cmd=['docker','run','--rm','-v',a.source+':/src:ro','-v',str(work)+':/work','-v',str(out)+':/diagnostic','-v',str(out/'cts_diagnostic.tcl')+':'+original+':ro','-w','/OpenROAD-flow-scripts/flow',image,'bash','-lc',shell]
def hashes(root):return {str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (root/'results').rglob('*') if f.is_file()}
before=hashes(old/'orfs');rec={'scope':'One unchanged CTS diagnostic replay; failure preserved; not closure','command':cmd,'image_id':image,'input_hashes':before,'source_recovery':str(old),'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'original_cts_sha256':hashlib.sha256(s.stdout).hexdigest()}
(out/'diagnostic.json').write_text(json.dumps(rec,indent=2)+'\n')
with (out/'replay.log').open('wb') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
rec.update(returncode=rc,original_inputs_unchanged=before==hashes(old/'orfs'))
(out/'diagnostic.json').write_text(json.dumps(rec,indent=2)+'\n')
