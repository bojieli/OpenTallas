import json,hashlib,gzip,sys,re,collections
from pathlib import Path
B=Path('/stage');sys.path.insert(0,str(B/'source658/tools/ref_tile'));import native_census as NC
P=Path('/OpenROAD-flow-scripts/flow/platforms/asap7');rows=json.loads((B/'cases.json').read_text());flavours={'R'}
for r in rows:
 for f in r['files']:
  if f['path'].endswith('6_final.v'):
   flavours.update(re.findall(r'ASAP7_75t_(SL|L|R)\b',Path(f['path']).read_text()))
paths=[]
for c in ['SS','FF','TT']:
 for f in sorted(flavours):
  tag={'R':'RVT','L':'LVT','SL':'SLVT'}[f]
  for group,tail in [('AO','211120.lib.gz'),('INVBUF','220122.lib.gz'),('OA','211120.lib.gz'),('SEQ','220123.lib'),('SIMPLE','211120.lib.gz')]:paths.append(str(P/'lib/NLDM'/f'asap7sc7p5t_{group}_{tag}_{c}_nldm_{tail}'))
roles,receipts=NC.liberty_roles(paths)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
exe='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad';lefs=[P/'lef/asap7_tech_1x_201209.lef']+[P/'lef'/f'asap7sc7p5t_28_{f}_1x_220121a.lef' for f in sorted(flavours)]
out=dict(scope='CURRENT_FROZEN_IMAGE_PROSPECTIVE_NOT_HISTORICAL_IMAGE_PROOF',image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29',exe=dict(path=exe,sha256=sha(exe)),Liberty=receipts,LEF=[dict(path=str(p),sha256=sha(p)) for p in lefs],flavours=sorted(flavours),cell_roles=roles)
(B/'current_image_native_sources.json').write_text(json.dumps(out,indent=2));print('IMAGE_SOURCES',len(paths),'Libs',len(roles),'cells')
