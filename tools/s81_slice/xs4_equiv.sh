#!/bin/bash
# xs4_equiv.sh <outdir> [mut] (cwd = repo root): S81-XG4XS (10-20) cycle equivalence of ot_s81sl_xs4 (native-bounded
# x streamer leaf) against CURRENT MAIN ot_s81sl_xs + a one-edge testbench relay on every input
# (rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_xs4_equiv.sv): xw_v / xw_d / fault compared on every edge.
# Stimulus: the production L0 (stage0) / L2 (stage3) x-streamer programs of tools/s81_slice/xs_program.py (issuer
# words + ring all-gather beats in near / far / random ring order, four slice offsets), late-beat offset programs
# (must fault on the same edge), seven fault-injection classes, and an in-flight reset with program restart.
# [mut] = bank | off | qswap | wcopy | tpar | exp builds that negative control (DUT only; the reference is a renamed
# copy whose mutant defines cannot be set) and its listed cases must FAIL.  Final line XS4_EQUIV_BENCH PASS|FAIL.
set -u; O=$(realpath -m $1); MUT=${2:-}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version | tee $O/verilator_version.log
D=""
case "$MUT" in
  "") ;;
  bank) D="+define+OT_S81SL_XS_MUT_BANK";;
  off) D="+define+OT_S81SL_XS_MUT_OFF";;
  qswap) D="+define+OT_S81SL_XS_MUT_QSWAP";;
  wcopy) D="+define+OT_S81SL_XS4_MUT_WCOPY";;
  tpar) D="+define+OT_S81SL_XS4_MUT_TPAR";;
  exp) D="+define+OT_S81SL_XS4_MUT_EXP";;
  *) echo "unknown mutant $MUT"; echo "XS4_EQUIV_BENCH FAIL"; exit 2;;
esac
S=rtl/dsrom_sys/s81_dv/slice
CAT=results/rtl/dsrom_recovery_20261004/immutable_fullcatalog
MAC="physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v"
# the reference: current main ot_s81sl_xs renamed, mutant defines renamed away
mkdir -p $O/ref
sed -e 's/OT_S81SL_XS_MUT_/OT_S81SL_XS_REFNOMUT_/g' -e 's/^module ot_s81sl_xs (/module ot_s81sl_xs_refm (/' $S/ot_s81sl_xs.sv > $O/ref/ot_s81sl_xs_refm.sv
grep -q '^module ot_s81sl_xs_refm' $O/ref/ot_s81sl_xs_refm.sv || { echo "ref rename failed"; echo "XS4_EQUIV_BENCH FAIL"; exit 3; }
SRC="rtl/lib/ot_rst_relay.sv rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv $MAC $S/ot_s81sl_xs_ctl.sv $O/ref/ot_s81sl_xs_refm.sv $S/ot_s81sl_xs4.sv $S/test/tb_s81sl_xs4_equiv.sv"
$V --cc --exe --build -j ${J:-8} -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 \
  +define+DSFD_PQ_STATIC_X2 --prefix Vxs4eq --top-module tb_s81sl_xs4_equiv --Mdir $O/obj $D $SRC \
  $S/test/tb_s81sl_xs4_equiv.cpp -o tb > $O/build.log 2>&1 || { echo BUILD_FAILED; grep -i error $O/build.log | head -20; tail -5 $O/build.log; echo "XS4_EQUIV_BENCH FAIL"; exit 3; }
ALL=1
prog() {  # name args...  -> $O/p_<name>/{prog.txt,meta.json,stim.txt,ROM images}
  local n=$1; shift; local w=$O/p_$n
  [ -f $w/stim.txt ] && return 0
  python3 tools/s81_slice/xs_program.py --out $w "$@" > $w.log 2>&1 || { echo "PROGRAM_FAILED $n"; tail -3 $w.log; return 1; }
  python3 - $w <<'PY'
import sys, json
w = sys.argv[1]
out = []
for l in open(w + "/prog.txt"):
    f = l.split()
    if f[1] == "XIS":
        out.append(f"{f[0]} 0 0 0 0 0 {f[2]}")
    elif f[1] == "XG":
        out.append(f"{f[0]} 1 {f[2]} {f[3]} {f[4]} {f[5]} 0")
open(w + "/stim.txt", "w").write("\n".join(out) + "\n")
m = json.load(open(w + "/meta.json"))
open(w + "/end.txt", "w").write(str(m["end_iter"]))
PY
}
run() {  # case program expect(PASS|FAIL) plusargs...
  local n=$1 p=$2 e=$3; shift 3; local w=$O/p_$p
  local end=$(cat $w/end.txt); local cyc=$((end + 40))
  local extra="$*"
  case "$extra" in *rstat=*) local rs=$(echo "$extra" | sed 's/.*rstat=\([0-9]*\).*/\1/'); cyc=$((rs + 24 + end + 40));; esac
  (cd $w && $O/obj/tb +stim=$w/stim.txt +OT_ROM_DIR=$w +cycles=$cyc "$@" > $O/case_$n.log 2>&1)
  local got=FAIL; grep -q '^XS4_EQUIV PASS' $O/case_$n.log && got=PASS
  local ok=0; [ $got = $e ] && ok=1; [ $ok = 1 ] || ALL=0
  echo "XS4_CASE $n $got expected=$e ok=$ok :: $(grep -h '^XS4_EQUIV cycles' $O/case_$n.log)"
  grep -h '^MISMATCH' $O/case_$n.log | head -3
}
L0="--stage-dir $CAT/stage0"; L2="--stage-dir $CAT/stage3"
prog L0n5  $L0 --order near --slice 5 || ALL=0
prog L2n9  $L2 --order near --slice 9 || ALL=0
if [ -z "$MUT" ]; then
  prog L0f0  $L0 --order far --slice 0 --off 52 || ALL=0
  prog L0r15 $L0 --order rand --slice 15 --seed 7 --off 29 || ALL=0
  prog L2r3  $L2 --order rand --slice 3 --seed 11 --off 44 || ALL=0
  prog L2f12 $L2 --order far --slice 12 --off 61 || ALL=0
  prog L0r8  $L0 --order rand --slice 8 --seed 3 --off 40 || ALL=0
  prog L0m1  $L0 --order near --slice 5 --off-load 36 || ALL=0
  prog L2m1  $L2 --order rand --slice 3 --seed 11 --off 44 --off-load 43 || ALL=0
  run L0_near_s5   L0n5  PASS +legal=1
  run L0_far_s0    L0f0  PASS +legal=1
  run L0_rand_s15  L0r15 PASS +legal=1
  run L2_near_s9   L2n9  PASS +legal=1
  run L2_rand_s3   L2r3  PASS +legal=1
  run L2_far_s12   L2f12 PASS +legal=1
  run L0_rand_s8   L0r8  PASS +legal=1 +seed=5
  run L0_offm1     L0m1  PASS +expfault=1
  run L2_offm1     L2m1  PASS +expfault=1
  for k in 1 2 3 4 5 6 7; do run L0_inj$k L0n5 PASS +inj=$k +injt=$((430 + 13 * k)); done
  for k in 1 2 7; do run L2_inj$k L2n9 PASS +inj=$k +injt=$((440 + 17 * k)); done
  run L2_reset     L2n9  PASS +legal=1 +rstat=500
  run L0_reset     L0n5  PASS +legal=1 +rstat=900
else
  run L0_near_s5   L0n5  FAIL +legal=1
  run L2_near_s9   L2n9  FAIL +legal=1
fi
[ $ALL = 1 ] && { echo "XS4_EQUIV_BENCH PASS"; exit 0; }; echo "XS4_EQUIV_BENCH FAIL"; exit 1
