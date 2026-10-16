#!/usr/bin/env bash
# hgi-unitrate: PIPE = 0 regression of the edited endpoint / block (must be unchanged): the bypass bench (endpoint and
# record forms, GN 8 / 96, ARGMAX_MERGE, duplicate-flit negative) and the mode guard (positive + mutant).
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd); O=$(realpath -m "$1"); mkdir -p "$O"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
CORE="rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $M rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv"
BLK="rtl/hbm_accel/generic/collective/ot_hgi_coll_ep.sv rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv rtl/hbm_accel/generic/collective/ot_hgi_coll_record.sv rtl/hbm_accel/generic/collective/ot_hgi_coll_decode.sv rtl/hbm_accel/generic/ot_hgi_cfg.sv"
F="-Wno-fatal -Wno-lint -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Irtl/hbm_accel/generic"
$V --binary --timing -j 8 $F --top-module tb_hgi_coll_bypass --Mdir "$O/ep" $CORE rtl/hbm_accel/tu/tb_hgi_coll_bypass.sv > "$O/build_ep.log" 2>&1
$V --binary --timing -j 8 $F --top-module tb_hgi_coll_bypass --Mdir "$O/rec" +define+BYP_REC $CORE $BLK rtl/hbm_accel/tu/tb_hgi_coll_bypass.sv > "$O/build_rec.log" 2>&1
$V --binary --timing -j 8 $F --top-module tb_hgi_coll_mode_guard --Mdir "$O/mg" $CORE rtl/hbm_accel/tu/tb_hgi_coll_mode_guard.sv > "$O/build_mg.log" 2>&1
$V --binary --timing -j 8 $F --top-module tb_hgi_coll_mode_guard --Mdir "$O/mgm" +define+OT_COLL_MUT_MODE_GUARD $CORE rtl/hbm_accel/tu/tb_hgi_coll_mode_guard.sv > "$O/build_mgm.log" 2>&1
r() { n=$1; shift; "$@" > "$O/$n.log" 2>&1; echo "$n rc=$? $(grep -h 'PASS\|BYP_\|FATAL\|fatal\|MODE\|BAD' "$O/$n.log" | head -2 | tr '\n' ' ')" >> "$O/verdict.txt"; }
: > "$O/verdict.txt"
r ep_g8  "$O/ep/Vtb_hgi_coll_bypass" +GN=8 +RANK=3 +PF=16
r ep_g96 "$O/ep/Vtb_hgi_coll_bypass" +GN=96 +RANK=37 +PF=4 +LAT=453
r ep_dupe "$O/ep/Vtb_hgi_coll_bypass" +GN=8 +RANK=3 +PF=16 +DUPE=1
r rec_g8 "$O/rec/Vtb_hgi_coll_bypass" +GN=8 +DIE=11 +PF=16
r rec_g96 "$O/rec/Vtb_hgi_coll_bypass" +GN=96 +DIE=133 +PF=4 +LAT=453
r rec_amx "$O/rec/Vtb_hgi_coll_bypass" +GN=8 +DIE=11 +AMX=1
r rec_multi "$O/rec/Vtb_hgi_coll_bypass" +GN=8 +DIE=11 +PF=16 +MULTI=1
r mg "$O/mg/Vtb_hgi_coll_mode_guard"
r mgm "$O/mgm/Vtb_hgi_coll_mode_guard"
cat "$O/verdict.txt"
