import sys,json,hashlib
from pathlib import Path
w=Path('/srv/opentallas-scratch3/claude/wt/codex-lec-transfer-1106');sys.path.insert(0,str(w/'tools/die_plan'))
import bound_reset_contract as B
p=Path(__file__).parent
try:B.source(p/'t30_bound.sv','ot_s81sl_leaf__t30',p,w)
except ValueError as e:
 assert 'no serialized reset tree' in str(e)
 result=dict(type='ot_s81sl_leaf__t30',new_export='REFUSED_missing_captured_tree',reason=str(e),baseline='preserved; owner actual source212/physical212 matches',rtl_sha256=hashlib.sha256((p/'t30_bound.sv').read_bytes()).hexdigest(),placement_tcl_sha256=hashlib.sha256((p/'t30_placement.tcl').read_bytes()).hexdigest())
 (p/'t30_result.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result))
else:raise AssertionError('new tree was guessed for t30')
