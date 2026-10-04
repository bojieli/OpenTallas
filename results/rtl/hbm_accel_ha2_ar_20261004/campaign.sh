#!/bin/bash
# HA2 all-reduce campaign (Claude). Builds 4 configs with the pinned sources in src/, runs seed sweeps.
set -u
E=$HOME/claude-ha2ar
cd $E
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
SRC="src/rtl/link/ot_link_afifo.sv src/rtl/hdc/ot_hdc_fastfp.sv src/rtl/hdc/ot_hdc_prefix.sv src/rtl/hdc/ot_hdc_fp32_add_lat.sv src/rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv src/rtl/hbm_accel/ha2_ar/ot_ha2_link.sv src/rtl/hbm_accel/ha2_ar/ot_ha2_ar_endpoint.sv src/rtl/hbm_accel/ha2_ar/tb_ha2_ar.sv"
sha256sum $SRC fx/*/*.hex > runs/input_sha256.txt
D() { for kv in "$@"; do printf -- "+define+HA2_%s " "$kv"; done; }
LINK="$(D HUBW=35 WSTG=14 BITS_X100=21165 PWB=551 PHY_L=130 PHY_G=138 JS=3 DMAX=192 LANES=16 ONESHOT=0 BF16=1 INJ=2 DEL=4 GS=16 NG=6)"
declare -A P
P[ds]="$LINK $(D NC=8 NOG=8 E=1024)"
P[dsgather]="$LINK $(D NC=1 NOG=96 E=64)"
P[dsgather512]="$LINK $(D NC=1 NOG=96 E=256)"
P[qwen]="$(D GS=2 NG=1 NC=2 NOG=1 E=4096 LANES=256 ONESHOT=1 BF16=0 INJ=1 DEL=1 HUBW=37 WSTG=14 BITS_X100=1308000 PWB=8217 PHY_L=5 PHY_G=5 JS=1 DMAX=16 T_PHY=0.4)"
build() {
  c=$1
  ( /usr/bin/time -v $V --binary --timing --hierarchical -j 16 -Wno-fatal -Wno-lint -Wno-style --x-assign fast --x-initial fast \
      --top-module tb_ha2_ar --Mdir b/$c ${P[$c]} $SRC ) > runs/build_$c.log 2>&1
  echo $? > runs/build_$c.exit
}
for c in ds dsgather dsgather512 qwen; do build $c & done
wait
# every simulation is single-threaded: run them concurrently
{
for c in ds dsgather dsgather512 qwen; do
  [ "$(cat runs/build_$c.exit)" = 0 ] || continue
  for s in $(seq 1 10); do echo "b/$c/Vtb_ha2_ar +VEC=fx/$c +SEED=$s > runs/${c}_central_s$s.log 2>&1"; done
done
if [ "$(cat runs/build_ds.exit)" = 0 ]; then
  for s in 1 2 3; do
    echo "b/ds/Vtb_ha2_ar +VEC=fx/ds +SEED=$s +PHY_L=114 +PHY_G=122 > runs/ds_phy114_s$s.log 2>&1"
    echo "b/ds/Vtb_ha2_ar +VEC=fx/ds +SEED=$s +PHY_L=170 +PHY_G=178 > runs/ds_phy170_s$s.log 2>&1"
  done
fi
} > runs/jobs.txt
xargs -P 24 -I{} bash -c "{}" < runs/jobs.txt
sha256sum -c runs/input_sha256.txt > runs/pins_after.log 2>&1; echo $? > runs/pins_after.exit
echo done > runs/campaign.exit
