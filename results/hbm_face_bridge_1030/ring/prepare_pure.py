from pathlib import Path
import re
from pure_flit import fix
P=Path(__file__).resolve().parent
for label in ('native','physical'):
 p=P/'prepared'/f'{label}.sv';(p.parent/f'{label}_pure.sv').write_text(fix(p.read_text()))
old=(P/'native_ring_api.sv').read_text();old=re.search(r'\bmodule\s+ot_hgi_coll_ring_ag_ctl\b.*?\bendmodule\b',old,re.S)[0]
formal=P/'boolean';formal.mkdir(exist_ok=True)
(formal/'old.sv').write_text(old.replace('module ot_hgi_coll_ring_ag_ctl','module ctl_old',1)+'\n')
(formal/'new.sv').write_text(fix(old).replace('module ot_hgi_coll_ring_ag_ctl','module ctl_new',1)+'\n')
ys=[]
for label in ('old','new'):
 ys += [f'read_verilog -sv /work/boolean/{label}.sv',f'chparam -set AG 1 -set NT 8 -set LAT 8 ctl_{label}',f'hierarchy -top ctl_{label}','proc','opt','memory_map','opt','techmap','opt','abc -g simple','opt_clean',f'write_json /work/boolean/{label}_mapped.json',f'design -stash {label}']
ys += ['design -reset','design -copy-from old -as gold ctl_old','design -copy-from new -as gate ctl_new','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple -undef','equiv_induct -undef -seq 2','equiv_status -assert']
(formal/'equiv.ys').write_text('\n'.join(ys)+'\n')
