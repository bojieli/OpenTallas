"""Rebuild the N59 kept-source, reach405 place prototype from repo inputs.
Does not launch P&R; review.txt conditions gate CTS/route/adoption.
"""
import argparse,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent
out=Path(a.out).resolve()
subprocess.run([sys.executable,str(root/'tools/die_plan/gen.py'),'phys',str(root/'physical/die_plan/qwen_compute/die_plan.json'),'--out',str(out),'--types','native59','--rtl-root',str(root),'--kit-rtl','native59='+str(packet/'inputs/files.f'),'--hold-ff-margin','5'],cwd=root,check=True)
k=out/'native59'
for h in (packet/'inputs/hooks').glob('*.tcl'):shutil.copyfile(h,k/h.name)
shutil.copytree(root/'physical/common_flow',k/'cf',dirs_exist_ok=True)
(k/'pre_gpl.tcl').write_text('source /work/face_flops.tcl\nsource /work/n59_stations.tcl\nsource /work/cf/macro_pin_flops.tcl\nsource /work/n59_reach405.tcl\n')
(k/'pre_dpl.tcl').write_text('source /work/face_flops_release.tcl\nsource /work/n59_stations_release.tcl\nsource /work/cf/macro_pin_flops_release.tcl\nsource /work/n59_reach405.tcl\n')
c=(k/'config.mk').read_text().replace('export VERILOG_DEFINES = -DSYNTHESIS','export VERILOG_DEFINES = -DSYNTHESIS -DOT_N59_WIF -DOT_N59_STN')
c=c.replace('export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl','export PRE_GLOBAL_PLACE_TCL = /work/pre_gpl.tcl').replace('export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl','export PRE_DETAIL_PLACE_TCL = /work/pre_dpl.tcl')
c+='\nexport MIN_CLK_ROUTING_LAYER = M6\nexport MAX_CLK_ROUTING_LAYER = M7\n'
(k/'config.mk').write_text(c)
print(k)
