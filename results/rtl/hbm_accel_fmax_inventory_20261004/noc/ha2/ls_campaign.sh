#!/bin/bash
# HA2 owner-reducer lockstep campaign (noc fmax closure): the unmodified HA2 DS bench with tb_ha2_ep_ls, which runs
# ot_ha2_owner_reduce beside every die's ot_ha2_ar_endpoint and compares {r_v, r_m, r_d, dupe} every cycle.
# Usage (from a source root holding rtl/ tools/ and this directory): ls_campaign.sh <workdir> <SLOTREG> <seeds...>
set -u
W=$1; SR=$2; shift 2
S=$(pwd); N=$S/results/rtl/hbm_accel_fmax_inventory_20261004/noc/ha2
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p $W && cd $W
[ -d fx/ds ] || python3 $S/tools/ha2_ar_fixture.py fx/ds --shape ds > fx_ds.json
$N/mk_ls_tb.sh $S tb_ls.sv
D() { for kv in "$@"; do printf -- "+define+HA2_%s " "$kv"; done; }
SRC="$S/rtl/link/ot_link_afifo.sv $S/rtl/hdc/ot_hdc_fastfp.sv $S/rtl/hdc/ot_hdc_prefix.sv $S/rtl/hdc/ot_hdc_fp32_add_lat.sv $S/rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $S/rtl/hbm_accel/ha2_ar/ot_ha2_link.sv $S/rtl/hbm_accel/ha2_ar/ot_ha2_ar_endpoint.sv $S/rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce.sv tb_ls.sv $N/tb_ha2_ep_ls.sv"
sha256sum $SRC fx/ds/*.hex > input_sha256_sr$SR.txt
$V --binary --timing --hierarchical -j 16 -Wno-fatal -Wno-lint -Wno-style --x-assign fast --x-initial fast \
   --top-module tb_ha2_ar --Mdir b_sr$SR \
   $(D HUBW=35 WSTG=14 BITS_X100=21165 PWB=551 PHY_L=130 PHY_G=138 JS=3 DMAX=192 LANES=16 ONESHOT=0 BF16=1 INJ=2 DEL=4 GS=16 NG=6 NC=8 NOG=8 E=1024 SLOTREG=$SR) \
   $SRC > build_sr$SR.log 2>&1
echo $? > build_sr$SR.exit
for s in "$@"; do b_sr$SR/Vtb_ha2_ar +VEC=fx/ds +SEED=$s > ds_sr${SR}_s$s.log 2>&1 & done
wait
echo done > campaign_sr$SR.exit
