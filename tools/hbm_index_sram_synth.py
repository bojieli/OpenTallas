#!/usr/bin/env python3
"""Native IKS SRAM logic inventory using pinned host ASAP7 TT cells; no P&R."""
import hashlib,json,os,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
work=Path(os.environ['OUT']);work.mkdir(parents=True,exist_ok=False)
pdk=Path.home()/'.local/opentallas-pdk-asap7/lib/NLDM'
libs=sorted(pdk.glob('*_RVT_TT_*.lib'))
if len(libs)!=5:raise RuntimeError('expected five actual ASAP7 RVT TT library groups')
body=[]
for p in libs:
 s=p.read_text();body.append(s[s.index('{')+1:s.rindex('}')])
combined=work/'combined.lib';combined.write_text('library (native_iks_asap7_tt) {\n'+ '\n'.join(body)+'\n}\n')
src=['rtl/common/ot_secded.sv','rtl/common/ot_secded_cols.svh','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v','physical/hbm_accel_die_views/svc/rtl/ot_hbm_index_lines_sram.sv']
rec={'source_commit':os.environ['PINNED_SOURCE_COMMIT'],'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in src},'library_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in libs},'area_scope':'TT mapped standardcells only; add64 native macros; no clock tree, placement, wires or signoff'}
(work/'source.json').write_text(json.dumps(rec,indent=2)+'\n')
script=work/'synth.ys'
script.write_text('\n'.join([
 'read_verilog -sv -I'+str(ROOT/'rtl/common')+' '+str(ROOT/src[0])+' '+str(ROOT/src[2])+' '+str(ROOT/src[3]),
 'hierarchy -check -top ot_hbm_index_lines_sram -chparam ENABLE 1 -chparam ROTATE_REMAP '+os.environ.get('ROTATE_REMAP','0'),
 'synth -top ot_hbm_index_lines_sram -flatten -run coarse',
 'tee -o '+str(work/'coarse_stat.json')+' stat -json',
 'write_rtlil '+str(work/'coarse.rtlil'),
 'synth -top ot_hbm_index_lines_sram -flatten -run fine:check',
 'dfflibmap -liberty '+str(combined),
 'abc -liberty '+str(combined),
 'clean', 'stat -liberty '+str(combined),
 'write_json '+str(work/'mapped.json'),
 'write_verilog -noattr '+str(work/'mapped.v')])+'\n')
yosys=Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'
with(work/'synth.log').open('w')as log:cp=subprocess.run([str(yosys),'-s',str(script)],stdout=log,stderr=subprocess.STDOUT)
rec['returncode']=cp.returncode;rec['verdict']='MAPPED'if cp.returncode==0 else'FAIL'
(work/'record.json').write_text(json.dumps(rec,indent=2)+'\n');raise SystemExit(cp.returncode)
