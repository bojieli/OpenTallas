#!/usr/bin/env python3
"""Source-bound pre-layout mapped synthesis and mandatory native census only."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path.cwd();out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
libs=sorted((Path.home()/'.local/opentallas-pdk-asap7/lib/NLDM').glob('*RVT_TT*.lib'))
assert len(libs)==5,libs
dff=next(p for p in libs if '_SEQ_' in p.name)
srcs=[Path(p) for p in (root/'results/rtl/s81_lepab_regional_1021/sources.txt').read_text().splitlines()]
macros=[Path('physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1'),Path('physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2')]
srcs += [p/(p.name+'_bb.v') for p in macros]
keep=['ot_sram_showahead_hit5','ot_s81sl_lep_rx_control','ot_s81sl_lep_host_event','ot_s81sl_lep_tx_push','ot_s81sl_lep_stamp','ot_s81sl_lep_vcopy','ot_s81sl_lep_pair_ready','ot_s81sl_lep_return8','ot_sram_showahead_readptr','ot_s81sl_lepab_select']
top='ot_s81sl_lep_mu_ab_regional'
script=['read_verilog -sv '+str(root/p) for p in srcs]
script += ['hierarchy -check -top '+top]+['setattr -mod -set keep_hierarchy 1 '+m for m in keep]
script += ['synth -top '+top+' -flatten','dfflibmap -liberty '+str(dff),'abc '+ ' '.join('-liberty '+str(p) for p in libs)+' -D 833.333','splitnets -ports','opt_clean -purge','write_verilog -noattr '+str(out/'mapped.v'),'tee -o '+str(out/'stat.txt')+' stat '+ ' '.join('-liberty '+str(p) for p in libs)]
(out/'synth.ys').write_text('\n'.join(script)+'\n')
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'inputs.json').write_text(json.dumps({'top':top,'sources':{str(p):h(root/p) for p in srcs},'libs':{str(p):h(p) for p in libs},'keep_modules':keep},indent=2)+'\n')
with (out/'synth.log').open('w') as f:
 subprocess.run([str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-s',str(out/'synth.ys')],stdout=f,stderr=subprocess.STDOUT,check=True)
cmd=[sys.executable,'tools/ref_tile/native_census.py','--netlist',str(out/'mapped.v'),'--top',top,'--out',str(out/'native_census.json')]
for p in libs+[p/(p.name+'_tt.lib') for p in macros]:cmd+=['--liberty',str(p)]
subprocess.run(cmd,check=True)
print('NATIVE_SYNTH_CENSUS_PASS',flush=True)
