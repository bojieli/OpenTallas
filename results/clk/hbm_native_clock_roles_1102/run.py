from pathlib import Path
import json,subprocess,hashlib,os
root=Path.cwd();profiles=json.load(open('profiles.json'))['profiles'];out=[]
for i,p in enumerate(profiles):
 kit=Path(p['kit']);matches=list(kit.glob('run/results/**/1_synth.odb'))
 if len(matches)!=1:
  out.append(dict(view=p['view'],kit=str(kit),status='NO_ACTUAL_SYNTH_ODB' if not matches else 'AMBIGUOUS_SYNTH_ODB',matches=list(map(str,matches))));(root/'progress.json').write_text(json.dumps(out,indent=2)+'\n');continue
 odb=matches[0];folder=root/str(i);folder.mkdir(exist_ok=True)
 cmd=['docker','run','--rm','--memory=4g','--memory-swap=4g','--cpus=1','-v','/srv/opentallas-scratch2:/srv/opentallas-scratch2:ro','-v',str(root)+':/out','-e','INPUT_ODB='+str(odb),'-e',f'OUTPUT_TSV=/out/{i}/roots.tsv','openroad/orfs:asap7lock','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 1 -exit /out/census.tcl']
 with open(folder/'read.log','w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 out.append(dict(view=p['view'],kit=str(kit),source_odb=str(odb),source_odb_sha256=hashlib.sha256(odb.read_bytes()).hexdigest(),returncode=r.returncode,tsv=f'{i}/roots.tsv'))
 (root/'progress.json').write_text(json.dumps(out,indent=2)+'\n')
 assert r.returncode==0,(i,r.returncode)
(root/'COMPLETE').write_text('actual saved native synth ODB direct net roles; no routing or timing qualification\n')
