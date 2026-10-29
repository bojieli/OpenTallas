"""Install reviewed guides for exactly the existing512 calendar data FFs."""
import json,shutil,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];kit=Path(sys.argv[1])
source=Path(sys.argv[2]) if len(sys.argv)>2 else root/'results/hbm_calendar_1029/cfg_w/data_guide.json'
guides=json.loads(source.read_text());guides=guides if isinstance(guides,list)else[guides]
if (kit/'calendar_cfg_w.tcl').exists():raise ValueError('guide already installed')
assert sum(g['expected_cells'] for g in guides)==512
script=['# Exact existing source stage membership guards, before inclusive GPL guides.']
spec=[]
for guide in guides:
 prefixes=' '.join('{'+p+'}'for p in guide['prefixes']);rect=' '.join(str(x)for x in guide['rect_um'])
 script.append('''set cw_n 0
foreach cw_i [[ord::get_db_block] getInsts] {
 set cw_nm [string map {"\\\\" ""} [$cw_i getName]]
 foreach cw_p {%s} {
  if {[string equal -length [string length $cw_p] $cw_nm $cw_p]} {incr cw_n;break}
 }
}
if {$cw_n != %d} {error "CALENDAR_CFG expected%d existing FF cells, got $cw_n"}
'''%(prefixes,guide['expected_cells'],guide['expected_cells']))
 spec.append('%s {%s} %s'%(guide['name'],prefixes,rect))
script.append('set ::ot_mrg_spec {'+' '.join(spec)+'}\nsource /work/macro_reg_guide.tcl\n')
(kit/'calendar_cfg_w.tcl').write_text('\n'.join(script))
assets=root/'physical/die_plan/hbm_arch_cores'
for name in ['macro_reg_guide.tcl','macro_reg_guide_release.tcl']:shutil.copy2(assets/name,kit/name)
with (kit/'face_flops.tcl').open('a') as f:f.write('\nsource /work/calendar_cfg_w.tcl\n')
with (kit/'face_flops_release.tcl').open('a') as f:f.write('\nsource /work/macro_reg_guide_release.tcl\n')
(kit/'calendar_cfg_w.json').write_text(json.dumps(guides,indent=1)+'\n')
