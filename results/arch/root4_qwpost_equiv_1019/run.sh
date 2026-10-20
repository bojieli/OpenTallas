#!/bin/bash
# The blackbox config ROM (ot_rom_4096x72_m8) is cut: its read data rom_q becomes a free input on both sides and its ce/addr are compared as outputs.
# ROOT4-QWPOST (10-19): yosys sequential equivalence of closed-view RTL (gold) vs main 0408184bd RTL (gate) at the
# closed kit's parameters. usage: run.sh  (in this dir). Writes logs/*.log and verdict lines to results.txt
set -u; cd "$(dirname "$0")"; mkdir -p logs; [ -n "${ONLY_ISO:-}" ] || : > results.txt
YS=${YOSYS:-yosys}; $YS -V > logs/yosys.version
side() { # name dir top files incdir chparams defines
  local n=$1 d=$2 top=$3 files=$4 inc=$5 chp=$6 defs=$7 rd=""
  for f in $files; do rd="$rd $d/$f"; done
  echo "read_verilog -sv -DSYNTHESIS $defs ${inc:+-I$d/$inc} $rd"
  [ -n "$chp" ] && echo "chparam ${chp//-chparam/-set} $top"   # (hierarchy -chparam on a top with paramod children asserts in yosys 0.68)
  echo "hierarchy -check -top $top"
  echo "proc; flatten; opt_clean; memory; opt_clean"
  [ "$top" = qfd_sys_face ] && echo "delete c:u_rom; expose -input w:rom_q; expose w:rom_ce w:rom_a"   # ROM macro = free read data, its ce/addr compared
  echo "rename -top $n"
  echo "hierarchy -top $n"
  echo "design -stash $n"
}
eq() { # tag top files inc gold_chp gate_chp gate_defs expect(pass|fail) golddir gatedir
  local tag=$1 top=$2 files=$3 inc=$4 gchp=$5 tchp=$6 tdefs=$7 exp=$8 gd=$9 td=${10}
  { side gold $gd $top "$files" "$inc" "$gchp" ""
    side gate $td $top "$files" "$inc" "$tchp" "$tdefs"
    echo "design -copy-from gold -as gold gold"
    echo "design -copy-from gate -as gate gate"
    echo "equiv_make gold gate equiv"
    echo "hierarchy -top equiv"
    echo "async2sync"
    echo "equiv_simple -seq 5"
    echo "equiv_induct -seq 5"
    echo "equiv_status -assert"; } > logs/$tag.ys
  $YS -q -l logs/$tag.log -s logs/$tag.ys > /dev/null 2>&1; rc=$?
  st=$(grep -E 'Found [0-9]+ \$equiv cells|Of those cells [0-9]+ are proven|unproven' logs/$tag.log | tr '\n' ' ')
  if [ $rc -eq 0 ]; then got=pass; else got=fail; fi
  [ "$got" = "$exp" ] && ok=OK || ok=UNEXPECTED
  echo "EQUIV $tag expect=$exp got=$got rc=$rc $ok :: $st" | tee -a results.txt
}
[ -n "${ONLY_ISO:-}" ] || : > results.txt; SF=$(cat sf_files.txt); XL=$(cat xl_files.txt)
[ -n "${ONLY_ISO:-}" ] || eq sys_face_default qfd_sys_face "$SF" rtl/qwen_sys/d2d_static_20261015 "" "" "" pass sf_gold sf_gate
[ -n "${ONLY_ISO:-}" ] || eq sys_face_mu1_neg qfd_sys_face "$SF" rtl/qwen_sys/d2d_static_20261015 "" "-chparam MU 1 -chparam MU_HEAD 1" "" fail sf_gold sf_gate
XP="-chparam NCH 4 -chparam READ_PIN_PIPE 1 -chparam FILL_PIPE 1"
[ -n "${ONLY_ISO:-}" ] || eq xs_leaf_default ot_qfd_xs_leaf "$XL" "" "$XP" "$XP" "" pass xl_gold xl_gate
# isolation: main's .sv with the CLOSED view's d2d_cal_image.svh (separates the RTL/param edits from the compiled image)
eq sys_face_main_sv_closed_img qfd_sys_face "$SF" rtl/qwen_sys/d2d_static_20261015 "" "" "" pass sf_gold sf_gatesvh
