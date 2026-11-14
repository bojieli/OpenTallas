#!/usr/bin/env python3
from pathlib import Path
import shutil,json,os
src=Path(os.environ.get('SOURCE','/srv/opentallas-scratch2/claude/die-s81-85/bksel_vC8e'))
dst=Path(os.environ.get('DEST','/srv/opentallas-scratch2/claude/die-s81-85/bksel_vC9geom'));here=Path(__file__).resolve().parent
if dst.exists():raise SystemExit('refuse overwrite')
def ignore(p,names):return [n for n in names if n in {'lec','physical_completion','__pycache__'} or (n.startswith('lec_async.') and n!='lec_async.sh') or n.startswith('lec_run.log') or n=='placed.csv']
shutil.copytree(src,dst,ignore=ignore)
for directory in ['run/logs','run/reports','run/results']:
 for pattern in ['3_5_place_dp*','3_place.*','4_*','4_cts.*']:
  for p in (dst/directory).rglob(pattern):
   if p.is_file():p.unlink()
shutil.copy(here/'hlat_follow_d_all.tcl',dst/'hlat_follow_d.tcl');shutil.copy(here/'i0_hop_affinity.tcl',dst/'i0_hop_affinity.tcl')
p=dst/'config.mk';p.write_text(p.read_text()+'\n# Full coverage of same-cycle lockup aliases; no RTL or clock policy change.\nexport OT_HLAT_REQUIRE_ALL = 1\n')
p=dst/'bank_regs_release.tcl';p.write_text(p.read_text()+'\nset ::env(OT_I0_HOP_MODE) place\nset ::env(OT_I0_HOP_OUT) /work/results/i0_affinity_place\nsource /work/i0_hop_affinity.tcl\nunset ::env(OT_I0_HOP_MODE)\n')
(dst/'VC9_GEOMETRY_ONLY.json').write_text(json.dumps({'source':str(src),'RTL_change':False,'cycle_delta':0,'changes':['Full aliased HLAT launch-clock binding coverage; fail closed on any omitted negative latch','Geometry-only i0 FF/latch/exact-hop buffers beside launch; preserve every clock pin and P keep-group'],'FIFO_lockup':'NOT SELECTED: separate C9 stopped UNPROVEN at native SRAM data witness, awaiting formal model','resume':'unchanged successful GPL checkpoint; all DPL/CTS outputs removed in this new private form; fresh actual review required'},indent=2)+'\n')
print(dst)
