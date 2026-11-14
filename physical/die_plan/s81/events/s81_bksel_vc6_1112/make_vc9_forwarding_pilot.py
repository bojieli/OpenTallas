#!/usr/bin/env python3
from pathlib import Path
import shutil,subprocess,json,os
src=Path(os.environ.get('SOURCE','/srv/opentallas-scratch2/claude/die-s81-85/bksel_vC8e'))
dst=Path(os.environ.get('DEST','/srv/opentallas-scratch2/claude/die-s81-85/bksel_vC9'))
here=Path(__file__).resolve().parent
if dst.exists():raise SystemExit('refuse overwrite')
skip={'run','results','lec','signoff','views','pa_hold','physical_completion','__pycache__'}
def ignore(p,names):return [n for n in names if n in skip or (n.startswith('lec_async.') and n!='lec_async.sh') or n.startswith('lec_run.log') or n=='placed.csv']
shutil.copytree(src,dst,ignore=ignore)
subprocess.run(['python3',str(here/'apply_fifo_hlat.py'),'--source',str(src/'rtl'),'--out',str(dst/'fifo_hlat_sources')],check=True)
for n in ['ot_s81ph_hq_parts.sv','ot_s81ph_hq_slice.sv']:shutil.copy(dst/'fifo_hlat_sources'/n,dst/'rtl'/n)
shutil.copy(dst/'fifo_hlat_sources/FIFO_HLAT_CHANGE.json',dst/'FIFO_HLAT_CHANGE.json')
shutil.copy(here/'hlat_follow_d_all.tcl',dst/'hlat_follow_d.tcl')
shutil.copy(here/'i0_hop_affinity.tcl',dst/'i0_hop_affinity.tcl')
p=dst/'bank_regs_release.tcl'
p.write_text(p.read_text()+'\nset ::env(OT_I0_HOP_MODE) place\nset ::env(OT_I0_HOP_OUT) /work/results/i0_affinity_place\nsource /work/i0_hop_affinity.tcl\nunset ::env(OT_I0_HOP_MODE)\n')
c=dst/'config.mk';c.write_text(c.read_text()+'\n# Private zero-cycle forwarding and complete hop-clock contract.\nexport VERILOG_DEFINES += -DOT_BKQ_FQ_HLAT\nexport OT_HLAT_REQUIRE_ALL = 1\n')
if not (dst/'lec_async.sh').is_file():raise SystemExit('missing required actual async proof helper')
(dst/'VC9_PREPARATION.json').write_text(json.dumps({'source':str(src),'cycle_delta':0,'changes':['Base FIFO wdata lockup to previous register, current-hit forwarding, and SRAM write pins; separate previous-hit option remains off','Complete follow-D aliases plus fail-closed all-negative-latch coverage assertion','Geometry-only input hop localization with all clock pins and P keep-group unchanged'],'proof':'FIFO receiving-edge+SRAM-state exact and stale-cycle mutant passed; fresh native proof still required','status':'PREPARED; input hop is geometry-only, clock mode unselected; render and review before any physical launch'},indent=2)+'\n')
print(dst)
