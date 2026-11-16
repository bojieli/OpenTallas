from pathlib import Path
import argparse,sys,json,shutil,hashlib
p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('image',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
r=a.root;o=a.out;d=r/'rtl/qwen_sys/d2d_static_20261015';old=d/'d2d_cal_image_qc_pair.svh'
sys.path.insert(0,str(r/'tools/mem_compiler'));import kv_dcal_profile as P
sys.path.insert(0,str(r/'tools/qwen_kv_die/bc4_epoch_1113'));from epoch_calendar import epoch_calendar,bind_image_profile
pr=P.extract_sv(a.image.read_text());st=P.extract_sv(old.read_text());early=pr['FIRST_OFS']-st['FIRST_OFS'];assert early>0
try:bind_image_profile(pr,st)
except ValueError as e:control=str(e)
else:raise AssertionError('old profile mismatch was not detected')
o.mkdir(parents=True,exist_ok=False)
for n,x in [('profile',pr),('stale',st)]:
 rec=P.personalise(x,o/n,instance=n);shutil.copy2(o/n/rec['viamap'],o/(n+'.viamap.hex'))
g=(d/'qkd_d2d_cal_seq_bc4.sv').read_text().replace('module qkd_d2d_cal_seq_pin_bc4 #(','module bc4_literal_qc_pair #(',1).replace('`include "d2d_cal_image_mu.svh"','`include "qc_pair.svh"')
assert '`include "qc_pair.svh"' in g
(o/'gold.sv').write_text(g);shutil.copy2(a.image,o/'qc_pair.svh')
alias=r/'physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/qkd_d2d_cal_seq_bc4_rom64.sv'
shutil.copy2(alias,o/'selected_bc4_rom64.sv')
for f in [d/'ot_qwen_d2d_cal_seq_bc4.sv',d/'ot_qwen_d2d_cal_seq_rom64_core.sv',r/'physical/asap7_memory_macros_v2/ot_rom_64x32_m2/ot_rom_64x32_m2.v']:shutil.copy2(f,o/f.name)
t=(r/'tools/qwen_kv_die/bc4_epoch_1113/tb.sv').read_text().replace('first_token-stale_first!=170',f'first_token-stale_first!={early}')
(o/'tb.sv').write_text(t)
tx=int(a.image.read_text().split("D2D_CAL_K_TX_IMG = 1024'h")[1].split(';')[0],16);rx=int(a.image.read_text().split("D2D_CAL_K_RX_IMG = 1024'h")[1].split(';')[0],16)
boot=[n for i in range(32) for n in [(tx>>(32*i))&0xffffffff,(rx>>(32*i))&0xffffffff]]+[pr['TX_SEG2'],pr['RX_SEG2']]
(o/'boot.hex').write_text(''.join(f'{v:08x}\n' for v in boot));(o/'defs.svh').write_text(''.join(f'`define {k} {pr[k]}\n' for k in ['TX_SEG1','RX_SEG1','TX_SEG2','RX_SEG2']))
(o/'run.sh').write_text('''#!/bin/bash
set -euo pipefail
ulimit -c 0
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd "$(dirname "$0")"
/usr/bin/time -f 'elapsed %e maxrss_kb %M' -o build.time verilator --binary --timing -Wno-fatal -j 4 --top-module tb --Mdir obj tb.sv gold.sv selected_bc4_rom64.sv ot_qwen_d2d_cal_seq_bc4.sv ot_qwen_d2d_cal_seq_rom64_core.sv ot_rom_64x32_m2.v > build.log 2>&1
/usr/bin/time -f 'elapsed %e maxrss_kb %M' -o run.time ./obj/Vtb > run.log 2>&1
grep -q BC4_EPOCH_PASS run.log
tail -9 run.log
''')
inputs=dict(image=str(a.image),image_sha256=hashlib.sha256(a.image.read_bytes()).hexdigest(),selected_alias=str(alias),alias_sha256=hashlib.sha256(alias.read_bytes()).hexdigest(),profile=pr,old_profile=st,old_profile_mismatch=control,old_programme_early_edges=early,clock_ps=833,epochs=3,native_epoch=epoch_calendar(222,pr),rf_epoch=epoch_calendar(222,pr,rf=True),scope='Current proposed +3 QC seam pair-image data on native selected BC4 ROM64; exact literal image lockstep, stale actual old profile and lost-base controls; no final bind, full D2D or G5 claim.')
(o/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n');print(json.dumps(inputs))
