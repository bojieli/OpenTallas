import hashlib,json,re
from pathlib import Path
out=Path('/out');records={}
for corner in ('SS','TT','FF'):
 p=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')/f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib';s=p.read_text();name='DFFHQNx1_ASAP7_75t_R';m=re.search(r'cell\s*\('+name+r'\)',s);start=s.index('{',m.start());i=start+1;depth=1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 raw=s[m.start():i]+'\n';dest=out/f'HQN_{corner}.cells.lib';dest.write_text(raw)
 records[dest.name]={'source_path':str(p),'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'selected_sha256':hashlib.sha256(raw.encode()).hexdigest()}
(out/'HQN_sources.json').write_text(json.dumps(records,indent=2)+'\n')
