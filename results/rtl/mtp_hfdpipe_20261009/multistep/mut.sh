#!/bin/bash
# mutant: S_STEP consumes the registered n-derived values without the nd_ok wait (stale n after a commit)
D=/tmp/claude-1000/hfdpipe/ms; WT=$(cd "$(dirname "$0")/../../../.." && pwd)
sed 's/S_STEP: if (NREG == 0 || nd_ok) begin/S_STEP: if (1) begin/' "$D/ctl_new.sv" > "$D/ctl_mut.sv"
grep -c "S_STEP: if (1)" "$D/ctl_mut.sv"
for c in "60 17 1" "40 1048576 1" "40 1048576 0" "60 19 0"; do
  set -- $c
  iverilog -g2012 -s tb_ctl_stop_multistep -Ptb_ctl_stop_multistep.NGEN=$1 -Ptb_ctl_stop_multistep.MAXPOS_CFG=$2 -Ptb_ctl_stop_multistep.FORCE=$3 -Ptb_ctl_stop_multistep.PRL=$( [ $3 = 0 ] && [ $2 = 19 ] && echo 2 || echo 0) -o "$D/mut.vvp" \
    "$D/ctl_mut.sv" $WT/rtl/hdc/ot_hdc_prefix.sv $WT/rtl/hdc/ot_hdc_accept.sv $WT/rtl/gpu/dshbm/ot_dshbm_accept_port.sv \
    $WT/rtl/test/hbm_accel/tb_ctl_stop_multistep.sv 2>/dev/null
  vvp -n "$D/mut.vvp" > "$D/mut_$1_$2_$3.log" 2>&1; grep '^TX' "$D/mut_$1_$2_$3.log" > "$D/mut_$1_$2_$3.tx"
  ref=$(ls $D/ngen$1_eos0-103_mp$2_prl*_f$3.old.tx | head -1)
  if cmp -s "$D/mut_$1_$2_$3.tx" "$ref"; then echo "ngen$1 mp$2 f$3 MUTANT UNDETECTED"; else echo "ngen$1 mp$2 f$3 MUTANT DETECTED: $(diff "$D/mut_$1_$2_$3.tx" "$ref" | head -4 | tr '\n' ' ')"; fi
done
