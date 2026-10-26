#!/usr/bin/env python3
"""Map one actual SU master independently; this is no CTS/closure claim."""
import json,re,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];kind=sys.argv[1];variant=(kind=='0_lat4_leaf1');out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
args=[sys.executable,'tools/run_abi3_physical.py','--view','asap7','--clock-period-ns','1.111111111','--clock-uncertainty-ns','0.060','--clock-uncertainty-hold-ns','0.025','--stages','synth','--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited','--keep-workdir',str(out/'work'),'--output',str(out/'result.json')]
if kind=='bank':
 args[args.index('synth')]='pnr'
 args+=['--pnr-stop-after','floorplan','--die-area','0','0','364.472','142.08','--core-area','2','2','362.472','140.08','--macro-place-halo','10','10']
 files=['rtl/hbm_accel/generic/adapters/static_su/data_store/ot_hbm_su_static_pinned_bank.sv','rtl/hbm_accel/generic/adapters/static_su/data_store/ot_hbm_su_static_data_store.sv','rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v']
 args+=['--top','ot_hbm_su_static_pinned_bank','--clock-port','clk','--param','READERS=6','--param','RB=9','--macro-view','ot_sram_1r1w_128x256_m1_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2']
else:
 files=re.findall(r'(?:rtl|physical)/[^\s\\]+\.(?:sv|v)',(R/'tools/hbm_static/su_arith_run.sh').read_text());files=[f for f in files if '/data_store/'not in f and '/peers/'not in f and not f.startswith('physical/') and '/tb_'not in f]
 args+=['--top','ot_hbm_su_static_lane','--clock-port','clk_stage[0]']
 for p in ['KIND='+('0' if variant else kind),'LN=7','MLAT='+('4' if variant else '3'),'ALAT=3','LEAF='+('1' if variant else '0'),'FETCH_EXTRA_EDGES=2']:args+=['--param',p]
for f in files:args+=['--source',f]
(out/'command.json').write_text(json.dumps(args,indent=2)+'\n')
with (out/'map.log').open('w')as log:r=subprocess.run(args,cwd=R,stdout=log,stderr=subprocess.STDOUT)
print('SU_PHYSICAL_MAP',kind,'exit',r.returncode,flush=True);sys.exit(r.returncode)
