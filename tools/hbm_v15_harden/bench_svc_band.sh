#!/usr/bin/env bash
# v15.1 service band master (wires-only hfd_svc_v15_<q>_s<k>: N physical PCs) vs N stand-alone ot_hbm_svc_static_pc,
# lockstep, per-lane directed-random protocol drivers, every output bit every cycle, every lane non-vacuous.
#  MUT=0 exact; MUT=1 lane-0 fill slot wired off by one (fill_slot ^ 1); MUT=2 lanes 0/1 read slot swapped
#  (N=1: lane-0 read epoch bit 0 inverted); MUT=3 per-PC clock entries collapsed onto clk_pc[0] (N>=2).
#  Before the lockstep run: per-PC clock ownership (a pulse on clk_pc[k] alone opens a bank in PC k only).  HBM-V15-HARDEN 10-15
set -euo pipefail
out=${1:?out}; mut=${2:-0}; band=${3:?band module}; cyc=${CYCLES:-20000}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
src=physical/hbm_accel_die_views/svc/v15/rtl/$band.sv
cp $src "$out/band.sv"
n=$(grep -c 'ot_hbm_svc_static_pc u_' $src)
case "$mut" in
 1) python3 - "$out/band.sv" <<'PY'
import re,sys;p=sys.argv[1];t=open(p).read()
t2=re.sub(r"\.fill_slot\(fill_slot(\[0 \+: 6\])?\)",lambda m:".fill_slot(fill_slot"+(m.group(1) or "")+" ^ 6'd1)",t,count=1);open(p,'w').write(t2)
PY
 ;;
 2) python3 - "$out/band.sv" "$n" <<'PY'
import sys;p=sys.argv[1];n=int(sys.argv[2]);t=open(p).read()
if n>=2:
  a,b=".read_slot(read_slot[0 +: 6])",".read_slot(read_slot[6 +: 6])"
  assert a in t and b in t
  t=t.replace(a,"@@A@@",1).replace(b,a,1).replace("@@A@@",b,1)
else:
  t=t.replace(".read_epoch(read_epoch)",".read_epoch(read_epoch ^ 16'd1)",1)
open(p,'w').write(t)
PY
 ;;
 3) python3 - "$out/band.sv" <<'PY'
import re,sys;p=sys.argv[1];t=open(p).read()
t2=re.sub(r"\.clk\(clk_pc\[\d+\]\)",".clk(clk_pc[0])",t);open(p,'w').write(t2)
PY
 ;;
esac
if [ "$mut" != 0 ]; then cmp -s "$out/band.sv" $src && { echo 'mutant not applied'; exit 3; }; fi
python3 tools/hbm_v15_harden/gen_band_tb.py "$out/band.sv" "$out/tb.sv"
iverilog -g2012 -s tb_hv15_band_clk -o "$out/clk.vvp" "$mem" $d/ot_hbm_svc_static_pc.sv "$out/band.sv" "$out/tb.sv"
vvp "$out/clk.vvp" > "$out/clk.log" 2>&1 || { cat "$out/clk.log"; exit 1; }
cat "$out/clk.log"; grep -q 'BAND_CLOCK_OWNERSHIP PASS' "$out/clk.log"
iverilog -g2012 -s tb_hv15_band -Ptb_hv15_band.CYCLES=$cyc -o "$out/sim.vvp" "$mem" $d/ot_hbm_svc_static_pc.sv "$out/band.sv" "$out/tb.sv"
vvp "$out/sim.vvp" > "$out/sim.log" 2>&1 || { cat "$out/sim.log"; exit 1; }
cat "$out/sim.log"; grep -q 'BAND_EQUIV PASS' "$out/sim.log"
