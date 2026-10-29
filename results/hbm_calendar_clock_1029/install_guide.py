"""Install the accepted existing512FF W guide in a newly generated own kit."""
import json,shutil,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];kit=Path(sys.argv[1])
guide=json.loads((root/'results/hbm_calendar_1029/cfg_w/data_guide.json').read_text())
if (kit/'calendar_cfg_w.tcl').exists():raise ValueError('guide already installed')
assert guide['expected_cells']==512 and guide['rect_um']==[4.32,17.28,17.28,91.8]
prefixes=' '.join('{'+p+'}' for p in guide['prefixes']);rect=' '.join(str(x) for x in guide['rect_um'])
script='''# Exact source stage membership guard, before GPL inclusive guide.
set cw_n 0
foreach cw_i [[ord::get_db_block] getInsts] {
 set cw_nm [string map {"\\\\" ""} [$cw_i getName]]
 foreach cw_p {%s} {
  if {[string equal -length [string length $cw_p] $cw_nm $cw_p]} {incr cw_n;break}
 }
}
if {$cw_n != 512} {error "CALENDAR_CFG_W expected512 existing FF cells, got $cw_n"}
set ::ot_mrg_spec {calendar_cfg_w {%s} %s}
source /work/macro_reg_guide.tcl
'''%(prefixes,prefixes,rect)
(kit/'calendar_cfg_w.tcl').write_text(script)
assets=root/'physical/die_plan/hbm_arch_cores'
for name in ['macro_reg_guide.tcl','macro_reg_guide_release.tcl']:shutil.copy2(assets/name,kit/name)
with (kit/'face_flops.tcl').open('a') as f:f.write('\nsource /work/calendar_cfg_w.tcl\n')
with (kit/'face_flops_release.tcl').open('a') as f:f.write('\nsource /work/macro_reg_guide_release.tcl\n')
(kit/'calendar_cfg_w.json').write_text(json.dumps(guide,indent=1)+'\n')
