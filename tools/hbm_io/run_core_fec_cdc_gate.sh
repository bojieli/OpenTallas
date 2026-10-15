#!/usr/bin/env bash
set -euo pipefail
root=${HCOLL_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
out=$(realpath -m "$1");mkdir -p "$out";cd "$root"
case_run(){
 phase=$1;ppm=$2;mut=$3
 tag=p${phase}_d${ppm}_m${mut}
 iverilog -g2012 -s tb_core_fec_word_window -Ptb_core_fec_word_window.PHASE="$phase" -Ptb_core_fec_word_window.PPM="$ppm" -Ptb_core_fec_word_window.MUT="$mut" -o "$out/$tag.sim" \
 rtl/hbm_accel/io_static_20261015/ot_hbm_static_word_cdc.sv rtl/hbm_accel/io_static_20261015/ot_hbm_core_fec_word_window.sv rtl/hbm_accel/io_static_20261015/tb_core_fec_word_window.sv
 vvp "$out/$tag.sim" > "$out/$tag.log" 2>&1 || return $?
 rm "$out/$tag.sim"
 cat "$out/$tag.log"
}
export -f case_run
export out
{ for phase in -8 0 8;do for ppm in -500 0 500;do echo "$phase $ppm 0";done;done
 echo '0 -10000 0';echo '0 10000 0';echo '0 0 1';echo '0 0 2'; } | xargs -P13 -n3 bash -c 'case_run "$@"' _
