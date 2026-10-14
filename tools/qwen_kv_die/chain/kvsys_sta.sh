#!/bin/bash
# qwen-split/kvsys: (re-)time an existing KV/system die GRT (grt_kv/ckpt_grt.odb + die_grt.spef) with the phi - R
# compensated clocks of its prep (libs/clocks_<c>.tcl) in R/sta_kv_<c>; TT setup + FF hold decide, SS sensitivity only.
# usage: kvsys_sta.sh <run dir R> <chain tools dir H> [corners, default "tt ff ss"]
set -u; R=$(readlink -f $1); H=$(readlink -f $2); CS=${3:-tt ff ss}; G=$R/grt_kv
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
for c in $CS; do D=$R/sta_kv_$c; rm -rf $D; mkdir -p $D/libs
  ln -f $G/ckpt_grt.odb $G/route.guide $G/die_grt.spef $D/
  for f in $R/libs/qfd_elements_$c.lib $R/libs/qfd_etm_*_$c.lib $R/libs/ot_hbm3e_phy_$c.lib $R/libs/views.json; do [ -f "$f" ] && cp "$f" $D/libs/; done
  OT_STA_CLOCKS=$R/libs/clocks_{corner}.tcl python3 $H/sta_tcl.py kv $c $D/grt_$c.tcl
  $H/dietop_run.sh $D grt_$c.tcl 8 60
  say "STA $c (phi-R clocks): $(grep -E '^(wns|tns|worst slack)' $D/grt_$c.log | tr '\n' ' ') $(grep -h -e OT_COMPENSATED_CLOCK -e OT_STEP_FAIL -e '^Error' $D/grt_$c.log | head -3 | tr '\n' ' ')"
done
say "sta done"
