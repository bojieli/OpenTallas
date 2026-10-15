#!/usr/bin/env bash
# S-NET: exact bench of ot_s81_retn_static vs the compiler model (tools/s81/static_return_calendar.py).
#   run_retn_static_gate.sh pass|mut_window|mut_fwd|mut_fault OUT [WIN]
# pass: 6 legal seeds (exact every edge, fault 0) + 1 deliberate collision (fault 1) at WIN and WIN=1,3.
# mut_*: the RTL mutant must FAIL the same vectors.
set -eu
cd "$(dirname "$0")/../.."
mode=${1:?mode}; out=${2:?out}; win=${3:-2}; mkdir -p "$out"
src=(rtl/v41rom/ot_v41_ret.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_delay.sv
     rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv rtl/dsrom_sys/s81_static_net/test/tb_s81_retn_static.sv)
mut=0; case $mode in pass) mut=0;; mut_window) mut=1;; mut_fwd) mut=2;; mut_fault) mut=3;; *) echo bad mode; exit 2;; esac
fails=0; runs=0
run_one() { # win seed collide
  local w=$1 s=$2 c=$3 d="$out/v_w$1_s$2_c$3"
  python3 tools/s81/static_return_calendar.py vectors --win "$w" --rst 1 --seed "$s" --words 500 $( [ "$c" = 1 ] && echo --collide ) --out "$d" > "$d.gen.log"
  iverilog -g2012 -s tb_s81_retn_static -Ptb_s81_retn_static.WIN="$w" -Ptb_s81_retn_static.MUT=$mut -o "$d.sim" "${src[@]}"
  runs=$((runs+1))
  if vvp -n "$d.sim" +DIR="$d" +T="$(cat $d/T)" +FAULT="$(cat $d/FAULT)" > "$d.log" 2>&1 && grep -q "RETN_STATIC PASS" "$d.log"; then
    grep "RETN_STATIC PASS" "$d.log"
  else fails=$((fails+1)); grep -m3 "RETN_STATIC" "$d.log" || tail -3 "$d.log"; fi
}
for s in 1 2 3 4 5 6; do run_one "$win" "$s" 0; done
run_one "$win" 7 1
if [ "$mode" = pass ]; then run_one 1 8 0; run_one 3 9 0; run_one 1 10 1; fi
if [ "$mode" = pass ]; then
  [ $fails = 0 ] && echo "RETN_STATIC_GATE PASS $runs runs exact vs compiler model" || { echo "RETN_STATIC_GATE FAIL $fails/$runs"; exit 1; }
else
  [ $fails -gt 0 ] && echo "RETN_STATIC_GATE MUTANT $mode REJECTED $fails/$runs" || { echo "RETN_STATIC_GATE MUTANT $mode ESCAPED"; exit 1; }
fi
