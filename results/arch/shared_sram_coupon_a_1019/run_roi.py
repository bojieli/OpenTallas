import json,os,hashlib
from pathlib import Path
import openroad
P=Path('/work');os.chdir(P)
assert hashlib.sha256(Path('/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad').read_bytes()).hexdigest()=='21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846'
tech=openroad.Tech();design=openroad.Design(tech);design.readDb('/work/native/original.odb')
print('ORIGINAL_ODB_SHA256',hashlib.sha256((P/'native/original.odb').read_bytes()).hexdigest(),flush=True)
coupon=json.loads((P/'coupon.json').read_text())
for i,c in enumerate(coupon['cases']):
 # Hidden Tcl command passes integers straight into native DBU interface.
 box=' '.join(str(z) for z in c['score_roi_nm'])
 cmd=f'drt::check_drc -box {{{box}}} -output_file /work/roi_{i:02d}.rpt -marker_name CASE_{i}'
 result=design.evalTclString('if {[catch {'+cmd+'} why]} {puts stderr "CHECKER_ERROR $why"; exit 1} else {puts "CHECKER_OK '+str(i)+' $why"}')
 print('CASE_RESULT',i,c['name'],repr(result),flush=True)
 assert (P/f'roi_{i:02d}.rpt').is_file(),(i,result)
print('ROI_COMPLETE',len(coupon['cases']),flush=True)
