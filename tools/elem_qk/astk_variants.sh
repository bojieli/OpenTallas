#!/bin/bash
# ELEM-QK 10-24: ASTK core closure variants from the KVG3-CORES kits (Codex TT/FF recovery copies: corners.tcl LIB_FILES
# parser fix, all_inputs -no_clocks SDC).  SDC / clocks / pins / geometry unchanged in every variant.
#   hm55   canonical RTL; implementation hold margin 55 ps at TC (FF hold is ~35 ps faster than TT: recovery FF -36..-38)
#   r4h    Codex same-cycle read-control replicas (d3c7327ff3: 4x5 b per Z, 0 added data cycles; FP miter 9992 checks +
#          mutant caught) + hold margin 55  (TT failures are the zq read-mux fanout: zq[2] -> oa[108] -80.6 ps on WN)
#   r4hs   r4h + setup margin 20, place density 0.72, timing-driven GPL
#   astk_variants.sh BASE(dir with <core>/ kits) R4(dir with r4 rtl) OUT CORE VARIANT
set -euo pipefail
BASE=$1; R4=$2; OUT=$3; C=$4; V=$5
D=$OUT/$C/$V; mkdir -p $D
rsync -a --delete --exclude run --exclude views $BASE/$C/ $D/
cp $R4/run_kit_kv.sh $R4/corners.tcl $D/
case $V in r4h|r4hs)
  cp $R4/rtl/qkd_astk_zn_r4.sv $R4/rtl/qkd_astk_zn_head_p_r4.sv $D/rtl/
  sed -i -E 's/^(    )qkd_astk_zn_head_p( u_u_strip)/\1qkd_astk_zn_head_p_r4\2/; s/^(    )qkd_astk_zn( u_u_strip)/\1qkd_astk_zn_r4\2/' $D/rtl/kv3_astk_$C.sv
  test $(grep -c "^    qkd_astk_zn\(_head_p\)\?_r4 u_u_strip" $D/rtl/kv3_astk_$C.sv) = 4
  sed -i 's#^\(export VERILOG_FILES = .*\)$#\1 /work/rtl/qkd_astk_zn_r4.sv /work/rtl/qkd_astk_zn_head_p_r4.sv#' $D/config.mk;;
esac
{ echo "# ELEM-QK variant $V (implementation margins only; SDC unchanged)"
  echo "export HOLD_SLACK_MARGIN = 55"
  case $V in r4hs) echo "export SETUP_SLACK_MARGIN = 20"; echo "export PLACE_DENSITY = 0.72"; echo "export GPL_TIMING_DRIVEN = 1";; esac
} >> $D/config.mk
echo "$D"
