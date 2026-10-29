#!/usr/bin/env python3
"""Stage one native-clock prototype without changing RTL, pins, macros or data sites."""
import argparse,sys,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('dest');p.add_argument('slice');p.add_argument('tools');a=p.parse_args()
s,d=Path(a.source),Path(a.dest)
if d.exists():raise SystemExit('fresh output required')
shutil.copytree(s,d,ignore=shutil.ignore_patterns('run','run_route.log','run_finish.log','run_synth.log','signoff.json','views','__pycache__'))
for top in ('results','logs','reports'):
 for f in (s/'run'/top).rglob('*'):
  if not f.is_file() or not f.name.startswith(('1_','2_','3_','1.','2.','3.')):continue
  out=d/'run'/top/f.relative_to(s/'run'/top);out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,out)
sys.path.insert(0,a.tools);import core_infra as CI
sl=json.load(open(a.slice));assert CI.install(d,sl)
(d/'native_pre_cts.tcl').write_text('source /work/max_fanout.tcl\nsource /work/master_core_infra.tcl\n')
cfg=(d/'config.mk').read_text().splitlines();cfg.append('override export PRE_CTS_TCL = /work/native_pre_cts.tcl');assert CI.kit_cts_hook(d,cfg)
(d/'config.mk').write_text('\n'.join(cfg)+'\n');shutil.copy2(a.slice,d/'native_clock_slice.json')
(d/'prototype_scope.json').write_text(json.dumps({'scope':'one native-clock CTS plus GRT prototype, no detailed route','original_kit':str(s),'sinks':5490,'clock_driver_cells':410,'added_command_cycles':0,'rtl_macro_pin_and_data_ff_positions':'unchanged source checkpoint','clock_uncertainty_and_io_frame':'unchanged 833ps 60/25ps TT250/FF202.5ps','review':'q3_native_clock_macro_overlay.png personally viewed; root/clock independent PASS-COND'},indent=1)+'\n')
print('Q3_NATIVE_CLOCK_STAGED',d)
