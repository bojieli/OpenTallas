import importlib.util,json
from pathlib import Path
spec=importlib.util.spec_from_file_location('nc','/src/results/rtl/qw_head_safe32_1020/native_synth/runtime/ref_tile/native_census.py');nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
r=json.loads(Path('/out/native_census_current.json').read_text());roles,receipts=nc.liberty_roles([x['path']for x in r['liberty']]);Path('/out/liberty_roles.json').write_text(json.dumps(dict(roles=roles,receipts=receipts))+'\n')
