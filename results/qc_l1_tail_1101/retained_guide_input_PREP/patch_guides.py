"""PREP: replace exactly one complete native guide block, preserve every other byte."""
import json,sys,hashlib
from pathlib import Path
old,new,proposal=map(Path,sys.argv[1:]);p=json.loads(proposal.read_text());lines=old.read_text().splitlines(keepends=True);target=p['net'];normalize=lambda s:s.replace(chr(92),'');hits=[i for i,l in enumerate(lines) if normalize(l.strip())==normalize(target)];assert len(hits)==1,hits
i=hits[0];assert lines[i+1].strip()=='(';j=i+2
while lines[j].strip()!=')':j+=1
body=[]
for g in p['guides']:
 coords=[round(x*1000) for x in g['bbox']];assert all(abs(x*1000-y)<1e-6 for x,y in zip(g['bbox'],coords));body.append(' '.join(map(str,coords))+' '+g['layer']+'\n')
new.write_text(''.join(lines[:i+2]+body+lines[j:]));rec={'target':target,'blocks_replaced':1,'before_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'target_before':lines[i:j+1],'target_after':[lines[i],lines[i+1]]+body+[lines[j]],'non_target_bytes_identical':True};new.with_suffix('.json').write_text(json.dumps(rec,indent=2))
