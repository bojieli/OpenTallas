#!/usr/bin/env bash
# Same-edge VP4 command-control replication: actual SRAM-backed bank bench.
set -euo pipefail
out=${1:?output directory}; mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
python3 - "$d" "$out" <<'PY'
import pathlib,sys
src,out=map(pathlib.Path,sys.argv[1:]);s=(src/'ot_hgi_dma_back_static_vp4_banks.sv').read_text()
t=(src/'tb_dma_back_vp4_banks_equiv.sv').read_text();a='ot_hgi_dma_back_static_vp4_banks dut('
assert t.count(a)==1
(out/'tb_local.sv').write_text(t.replace(a,'ot_hgi_dma_back_static_vp4_banks #(.LOCAL_CTRL(1)) dut('))
(out/'tb_default.sv').write_text(t)
(out/'local.sv').write_text(s)
a='flags[4]<=$signed(b_ci_m2-cycle_q)>=1;';assert s.count(a)==1
(out/'mut_flag.sv').write_text(s.replace(a,"flags[4]<=(g==11)?1'b0:($signed(b_ci_m2-cycle_q)>=1);"))
a='if(!local_rst_n)valid_q<=0;else valid_q<=b_v;';assert s.count(a)==1
(out/'mut_cv.sv').write_text(s.replace(a,"if(!local_rst_n)valid_q<=0;else valid_q<=(g==6)?1'b0:b_v;"))
PY
for variant in default local mut_flag mut_cv; do
  rtl="$out/local.sv";tb="$out/tb_local.sv"
  [ "$variant" != default ] || tb="$out/tb_default.sv"
  case "$variant" in mut_*)rtl="$out/$variant.sv";;esac
  iverilog -g2012 -s tb_dma_back_vp4_banks_equiv -o "$out/$variant.vvp" "$m" "$d/ot_hgi_dma_back_static_cursor.sv" "$d/ot_hgi_dma_back_static_vp_banks.sv" "$rtl" "$tb" > "$out/$variant.compile.log" 2>&1
  rc=0;vvp "$out/$variant.vvp" > "$out/$variant.log" 2>&1 || rc=$?
  case "$variant" in
    mut_*)[ "$rc" != 0 ] || { echo "SURVIVING_MUTANT $variant";exit 1; };echo "CAUGHT $variant";;
    *)[ "$rc" = 0 ];grep 'DMA_VP_EQUIV PASS' "$out/$variant.log";;
  esac
done
