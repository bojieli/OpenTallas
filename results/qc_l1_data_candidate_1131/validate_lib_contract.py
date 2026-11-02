"""Static source-byte guard before any native candidate execution; no STA calls."""
import hashlib,json,fnmatch
from pathlib import Path
m=json.load(open('/work/candidate_manifest.json'));p=Path('/work/lib_master_contract.json')
assert hashlib.sha256(p.read_bytes()).hexdigest()==m['lib_master_contract_sha256']
c=json.loads(p.read_text());libdir=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
for file,rec in c.items():
 assert hashlib.sha256((libdir/file).read_bytes()).hexdigest()==rec['sha256'],file
 for name,cell in rec['masters'].items():
  assert cell['pins']=={'A':{'direction':'input'},'Y':{'direction':'output','function':'A'}},name
  assert not any(fnmatch.fnmatchcase(name,pat)for pat in m['platform_dont_use_patterns']),name
cfg=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/config.mk')
assert hashlib.sha256(cfg.read_bytes()).hexdigest()==m['platform_config_sha256'],'native platform DONT_USE context changed'
