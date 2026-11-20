#!/bin/bash
# FABLE-FIX-S81-SERDES-0000: OT_S81_SERDES_RM_WPL8 bench (iverilog).  usage: run_rm_wpl_bench.sh [OUTDIR]; exit 0 = base PASS x2 and mutant FAIL
set -u
cd "$(dirname "$0")/../../rtl/dsrom_sys/s81_link"
O=${1:-$(mktemp -d)}; mkdir -p "$O"; rc=0
for v in "" "-DWPL_FAST_W" "-DRMWPL_RT_MUT_EARLY"; do
  iverilog -g2012 -DOT_S81_SERDES_RST_TREE $v -s tb_s81_rate_match_rt_wpl -o "$O/wpl.vvp" tb_s81_rate_match_rt_wpl.sv col/ot_pdie_serdes_col.sv ot_pdie_serdes.sv ot_pdie_serdes_locksafe.sv || { echo "COMPILE FAIL [$v]"; rc=1; continue; }
  r=$(vvp -n "$O/wpl.vvp" 2>&1 | grep -E "RM_RT_WPL" | tail -1)
  echo "[$v] $r"
  case "$v" in
    *MUT*) echo "$r" | grep -q "FAIL exact" || { echo "MUTANT NOT CAUGHT"; rc=1; } ;;
    *) echo "$r" | grep -q "RM_RT_WPL PASS" || rc=1 ;;
  esac
done
echo "RM_WPL_BENCH rc $rc"; exit $rc
