from pathlib import Path
import shutil,json,subprocess
src=Path('/srv/opentallas-scratch2/claude/die-s81-85/bksel_vC7b'); dst=src.parent/'bksel_vC8r1c8'
if dst.exists():raise SystemExit('refuse overwrite')
skip={'run','results','lec','pa_hold','physical_completion','__pycache__'}
def ignore(p,names):return [n for n in names if n in skip or (n.startswith('lec_async.') and n!='lec_async.sh') or n.startswith('lec_run.log') or n.startswith('run_') and n.endswith('.log') or n=='placed.csv']
shutil.copytree(src,dst,ignore=ignore)
subprocess.run(['python3',str(src.parent/'patch_r1c8.py'),str(dst/'rtl/ot_s81ph_hq_slice.sv')],check=True)
shutil.copy(src.parent/'r1c8_affinity.tcl',dst/'r1c8_affinity.tcl')
c=dst/'config.mk';c.write_text(c.read_text()+'\n# Private same-cycle local replay-select copies; no cycle or IO change.\nexport VERILOG_DEFINES += -DOT_BKQ_R1C8\n')
p=dst/'bank_regs_release.tcl';p.write_text(p.read_text()+'\nsource /work/r1c8_affinity.tcl\n')
(dst/'R1C8_CHANGE.json').write_text(json.dumps({'source':str(src),'change':'per-8-bit H2 replay/memory control copies plus local source/capture affinity','cycle_delta':0,'alignment':'All copies sample identical rpd/mbd at identical edge, original rpb_v/memb_v sign copies unchanged, HLAT retained for each copy; q/r1_v/r1_fl latency unchanged','proof':'smallest actual extracted block exact 2048 cycles, mutant killed 1899 mismatches; full fresh RTL/netlist proof required before GRT'},indent=2)+'\n')
print(dst)
