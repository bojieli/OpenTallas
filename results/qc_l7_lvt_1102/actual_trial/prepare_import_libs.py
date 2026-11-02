from pathlib import Path
import json,hashlib
p=Path('/work');d=json.loads((p/'postcts_gate_tt.libraries.json').read_text());assert d['status']=='LOADED' and d['corner']=='TT';paths=[]
for row in d['libraries']:
 f=Path(row['path']);assert hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256'];paths.append(str(f))
m=json.loads((p/'MODEL_PREP.json').read_text())
for n in ['asap7sc7p5t_SIMPLE_LVT_TT_nldm_211120.lib.gz','asap7sc7p5t_28_L_1x_220121a.lef']:
 assert hashlib.sha256((p/n).read_bytes()).hexdigest()==m['files'][n]
paths.append('/work/asap7sc7p5t_SIMPLE_LVT_TT_nldm_211120.lib.gz');print(' '.join('{'+x+'}' for x in paths))
