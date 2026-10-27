from pathlib import Path
import json
from infra_connectivity import check_basic_clearance
r=check_basic_clearance('/old_input.odb',['ck_mesh','VDD','VSS'],['ck_mesh'])
Path('/work/old_68via_clearance.json').write_text(json.dumps(r,indent=2)+'\n')
assert r['verdict']=='FAIL',r
print('OLD_68VIA_BAD_PINLANDINGS_REJECTED',len(r['violations']),r['violations'][:2])
