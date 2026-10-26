#!/bin/bash
# QXPQ-CGR bench runner (S81-CORE-LAT/QX 2026-10-26): tb_qxpq_cgr = q element CGR = 8 (region clock-gate copies) vs the
# same element before the change (OLD_ROOT's RTL, every module renamed old_*), die parameters, lock-step every cycle.
#   qxpq_cgr_bench.sh SRC_ROOT OLD_ROOT WORK [MODE]   MODE all (default): pass x3 seeds + mutant; pass; mut
# OLD_ROOT = a tree with the reference rtl/ (e.g. a worktree of origin/claude/s81-core-lat-qb-1026).
set -u
S=$(cd "$1" && pwd); O=$(cd "$2" && pwd); W=$3; mkdir -p "$W"; W=$(cd "$W" && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
TB=$S/tools/dsrom_qelem_cl/tb_qxpq_cgr.sv
RTL="rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv rtl/v41rom/ot_v41_elem_pq_tags.sv rtl/v41rom/ot_v41_kreg.sv
 rtl/v41rom/ot_v41_chain3.sv rtl/v41rom/ot_v41_chain4.sv rtl/v41rom/ot_v41_fadd2.sv rtl/v41rom/ot_v41_rom_elem_w10.sv
 rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv
 rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bterm2_w10.sv rtl/v41rom/ot_v41_chain2.sv
 rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv rtl/v41rom/ot_v41_bterm3_w10.sv rtl/v41rom/ot_v41_bterm4_w10.sv
 rtl/v41rom/ot_v41_bterm5_w10.sv rtl/v41rom/ot_v41_segtree3.sv rtl/v41rom/ot_v41_segtree4.sv rtl/v41rom/ot_v41_segtree5.sv
 rtl/v41rom/ot_v41_segtree6.sv "
F=""; for f in $RTL; do F="$F $S/$f"; done
# the reference: OLD_ROOT's files with every module they define renamed old_<name> (the ROM fixture stays shared)
mkdir -p "$W/old"; FO=""
MODS=$(for f in $RTL; do grep -ohE '^\s*module\s+[A-Za-z_][A-Za-z0-9_]*' "$O/$f"; done | awk '{print $2}' | grep -v '^ot_rom_' | sort -u)
SED=""; for m in $MODS; do SED="$SED -e s/\\b$m\\b/old_$m/g"; done
for f in $RTL; do b=$(basename $f); sed $SED "$O/$f" > "$W/old/$b"; FO="$FO $W/old/$b"; done
echo "reference modules renamed: $(echo $MODS | wc -w)"
build() { # name defines...
  local n=$1; shift
  "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_qxpq_cgr --Mdir "$W/$n" -j 16 -CFLAGS -O1 \
    "$@" $F $FO "$TB" > "$W/$n.build.log" 2>&1 || { echo "BUILD_FAIL $n"; tail -20 "$W/$n.build.log"; return 1; }
}
run() { # name expect seed
  "$W/$1/Vtb_qxpq_cgr" +seed=$3 > "$W/$1_s$3.log" 2>&1
  local v=$(grep -o "QXPQ_CGR \(PASS\|FAIL\)" "$W/$1_s$3.log" | tail -1)
  local ok=0; [ "$v" = "QXPQ_CGR PASS" ] && [ "$2" = pass ] && ok=1; [ "$v" = "QXPQ_CGR FAIL" ] && [ "$2" = fail ] && ok=1
  echo "$1 seed $3 expect $2 -> ${v:-NO_VERDICT} $([ $ok = 1 ] && echo OK || echo BAD)"
  grep '^QXPQ_CGR cycles' "$W/$1_s$3.log"; grep -m2 '^MISMATCH\|FAIL:' "$W/$1_s$3.log"
  [ $ok = 1 ]
}
MODE=${4:-all}
rc=0
case "$MODE" in
  pass) build pass +define+QP_CHECK || exit 2; for s in 1 2 3; do run pass pass $s || rc=1; done ;;
  mut) build mut +define+OT_CGR_MUTANT_R3 || exit 2; run mut fail 1 || rc=1 ;;
  all) build pass +define+QP_CHECK && build mut +define+OT_CGR_MUTANT_R3 || exit 2
       for s in 1 2 3; do run pass pass $s || rc=1; done; run mut fail 1 || rc=1 ;;
  *) echo "unknown MODE $MODE"; exit 2 ;;
esac
echo "BENCH_RC $rc"; exit $rc
