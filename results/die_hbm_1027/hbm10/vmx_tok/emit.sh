#!/usr/bin/env bash
# VMX-TOK-1: emit DS L0/L2/L14 for base (no half-local), h0 (--half-local 0), h1 (--half-local 1), LX 15, on the r18h5 land-direct
# SW slice boundary (TOK-HBM vehicle of record: die.v 5b10bf72, TB 38766c45, boundary 93fbc670); same args as tok_func_hbm.sh
# step 3 (CONNECTED_LOWERING=0: no cx / su-lower2), su_SW0 native timing READ_RETURN 22 / WRITE_RETURN 19 / PIN_REG 0.
set -uo pipefail
W=/srv/opentallas-scratch2/claude/wt/vmx-tok-1
R=/srv/opentallas-scratch2/claude/vmx-tok-1
B=$R/vehicle/slice/boundary.json
FIX=$W/results/rtl/hbm_ds_layer_tput_1018/fixtures
cd $W
for v in base h0 h1; do
  case $v in base) HA=();; h0) HA=(--half-local 0 --native-xread-lx 15);; h1) HA=(--half-local 1 --native-xread-lx 15);; esac
  for LL in 00 02 14; do l=$((10#$LL)); O=$R/emit/$v/ds_l$l; mkdir -p $O
    ( python3 tools/hbm_layer_vehicle/layer_images.py --design ds --layer $l --programme "$FIX/L$LL/images/ds_v41_1M_L${LL}_per_die.json" \
        --fixtures "$FIX/L$LL" --boundary "$B" --native-read-return 22 --native-write-return 19 --native-pin-reg 0 "${HA[@]}" --out $O > $O.log 2>&1
      echo "rc=$?" >> $O.log ) &
  done
done
wait
grep -H rc= $R/emit/*/*.log
