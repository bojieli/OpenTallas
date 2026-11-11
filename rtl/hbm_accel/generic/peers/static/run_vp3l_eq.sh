#!/usr/bin/env bash
# vPose3L EQ_CYCLE_SHIFTED bench (HBM-HUB-RTL-1 11-11, tag dma-vpose3l). Run from the repo root.
#  pos   : VP3L=1 vs VP3L=0, wd declared +1 edge, all else same edge            -> must PASS
#  shift0: same, wd compared unshifted (the declared pin cycle is real)          -> must FAIL
#  neg1  : VP3L=1 with the early lead term offset one short (OT_DMA_VP3L_NEG1)    -> must FAIL
#  neg2  : VP3L=1 with the W-field hi+1 stage off by one (OT_DMA_VP3L_NEG2)      -> must FAIL
set -uo pipefail
out=${1:?output};mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
cp "$d/ot_hgi_dma_back_static_vp4_banks.sv" "$out/vp.sv"
# same Icarus 11 workaround as bench_dma_vp4_banks.sh (net from unpacked-array word); identical combinational read
python3 -I - "$out/vp.sv" <<'PYFIX'
import pathlib,sys
p=pathlib.Path(sys.argv[1]);s=p.read_text()
a='    assign bank_write_slot=(RR_RT==7)?expect_tag[7]:land_tag_rt;'
assert s.count(a)==1
p.write_text(s.replace(a,'    reg [6:0] bank_write_slot_sim; always @* bank_write_slot_sim=(RR_RT==7)?expect_tag[7]:land_tag_rt; assign bank_write_slot=bank_write_slot_sim;'))
PYFIX
rc=0
run(){ # name expect(PASS|FAIL) defines...
  local n=$1 e=$2; shift 2
  iverilog -g2012 -DOT_DMA_ACCEPT_EARLY "$@" -s tb_dma_vp4_vp3l_equiv -o "$out/$n.vvp" "$m" "$d/ot_hgi_dma_back_static_vp_banks.sv" "$out/vp.sv" "$d/tb_dma_vp4_vp3l_equiv.sv" > "$out/$n.compile.log" 2>&1 || { echo "VP3L_EQ $n COMPILE_FAIL"; cat "$out/$n.compile.log"; rc=1; return; }
  vvp "$out/$n.vvp" > "$out/$n.log" 2>&1
  if grep -q 'DMA_VP3L_EQ_CYCLE_SHIFTED PASS' "$out/$n.log"; then got=PASS; else got=FAIL; fi
  echo "VP3L_EQ $n expect=$e got=$got :: $(grep -m1 -E 'PASS|FATAL|mismatch|fatal' "$out/$n.log" | cut -c1-160)"
  [ "$got" = "$e" ] || rc=1
}
for rt in 7 80; do  # 7 = unit control; 80 = the bound die (t11_top hb_dbk_* #(.RR_RT(80)))
run pos_rt$rt PASS -DRT=$rt
run shift0_rt$rt FAIL -DRT=$rt -DVP3L_SHIFT0
run neg1_rt$rt FAIL -DRT=$rt -DOT_DMA_VP3L_NEG1
run neg2_rt$rt FAIL -DRT=$rt -DOT_DMA_VP3L_NEG2
done
[ $rc = 0 ] && echo "VP3L_EQ ALL PASS" || echo "VP3L_EQ FAILED"
exit $rc
