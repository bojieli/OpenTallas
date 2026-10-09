#!/bin/bash
set -eu
out=$(readlink -m "$1");mkdir -p "$out"
python3 - "$out" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,'tools'); import ha2_ar_fixture as HF
HF.SHAPES['ar96']=dict(GS=8,NG=12,NC=8,NOG=12,E=1024,LANES=16,ONESHOT=0,BF16=1)
HF.write(Path(sys.argv[1])/'fx','ar96',20261009)
PY
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
SRC="rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $M rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_ps.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv rtl/hbm_accel/generic_sram_ecc_20261009/tb_endpoint.sv"
/usr/bin/time -v "$V" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_accel_tu_endpoint --Mdir "$out/obj" +define+TU_DUT=ot_hbm_accel_tu_endpoint_psg +define+TU_LOCKSTEP +define+TU_NC=8 +define+TU_NOG=12 +define+TU_BF16=1 +define+TU_GSZPORT=15 +define+TU_PFMAX=64 +define+TU_PCLK_IS_CLK -GT_PHY=0.833333 $SRC > "$out/build.log" 2> "$out/build.time.txt"
for r in $(seq 0 95);do
 "$out/obj/Vtb_hbm_accel_tu_endpoint" +VEC="$out/fx" +PF=64 +RANK="$r" +SEED=1 > "$out/rank$r.log" 2>&1
 grep -q 'TUDONE .* mismatches=0 faults=0 ' "$out/rank$r.log"
done
echo 'PAYLOAD_ENDPOINT PASS ranks=96 NC8 NOG12 DS cycle lockstep' > "$out/verdict.txt"
