#!/usr/bin/env python3
from pathlib import Path
import subprocess,os,json
r=Path.cwd();img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
subprocess.run(['tar','xzf','source.tgz'],check=True)
cmd=r"""set -eu
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
mkdir -p libs
for f in "$L"/*.lib*; do b=$(basename "$f" .gz); case "$f" in *.gz) gzip -dc "$f" > "libs/$b";; *) cp "$f" "libs/$b";; esac; done
L=/w/libs
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
cat > synth.ys <<YS
read_verilog -sv -DSYNTHESIS rtl/lib/ot_reset_sync.sv rtl/link/ot_link_afifo.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_kq2.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_kport_q.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v
chparam -set WOPEN 0 -set MUT 0 -set FAW 3 ot_hbm_svc_wb_kport_q
hierarchy -check -top ot_hbm_svc_wb_kport_q
tcl physical/common_flow/ot_keep_regs.tcl
synth -top ot_hbm_svc_wb_kport_q -flatten
dfflibmap -liberty $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
abc -liberty $L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty $L/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty $L/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib
opt_clean -purge
write_verilog -noattr mapped.v
tee -o stat.txt stat
YS
$Y -l synth.log synth.ys
LIBS=''
for f in $L/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_TT_nldm_*.lib*; do LIBS="$LIBS --liberty $f"; done
python3 tools/ref_tile/native_census.py --netlist mapped.v --top ot_hbm_svc_wb_kport_q --out native.json $LIBS --liberty physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
"""
with (r/'run.log').open('w') as f:rc=subprocess.run(['docker','run','--rm','-u',f'{os.getuid()}:{os.getgid()}','-v',str(r)+':/w','-w','/w','--entrypoint','bash',img,'-c',cmd],stdout=f,stderr=subprocess.STDOUT).returncode
print('STANDALONE_NATIVE_RC',rc,flush=True)
raise SystemExit(rc)
