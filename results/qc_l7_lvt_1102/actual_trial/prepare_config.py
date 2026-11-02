from pathlib import Path
import json,hashlib
p=Path('/work');s=(p/'config.mk').read_bytes();sha=hashlib.sha256(s).hexdigest();extra=[]
for co,var in [('tt','TC_LIB_FILES'),('ff','BC_LIB_FILES')]:
 d=json.load(open(p/f'baseline_{co}_libraries.json'));assert d['status']=='LOADED' and d['corner']==co.upper() and d['config_sha256']==sha
 files=[]
 for row in d['libraries']:
  f=Path(row['path']);assert hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256'];files.append(str(f))
 n=f'asap7sc7p5t_SIMPLE_LVT_{co.upper()}_nldm_211120.lib.gz';model=json.load(open(p/'MODEL_PREP.json'));assert hashlib.sha256((p/n).read_bytes()).hexdigest()==model['files'][n];files.append('/work/'+n)
 extra.append('override export '+var+' = '+' '.join(files))
(p/'config.baseline.mk').write_bytes(s);(p/'config.mk').write_bytes(s+b'\n# PRIVATE four-DATA-LVT timing diagnostic; exact native baseline libraries plus selected SIMPLE LVT only.\n'+('\n'.join(extra)+'\n').encode());json.dump({'baseline_sha256':sha,'after_sha256':hashlib.sha256((p/'config.mk').read_bytes()).hexdigest(),'changes':extra,'no_SDC_RC_gate_or_clock_changes':True},open(p/'LVT_LIBRARY_CONFIG.json','w'),indent=2)
