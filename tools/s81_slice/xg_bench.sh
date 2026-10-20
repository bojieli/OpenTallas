#!/bin/bash
# xg_bench.sh <outdir> [case ...] (cwd = repo root): S81-XG (10-19) lockstep of the hardened gather sub-leaf ot_s81sl_xg
# (ring stop ot_s81sl_rstop + x streamer ot_s81sl_xs) against the unmodified production static PQ slot on the production
# L0 (stage0) / L2 (stage3) phase, stream and calendar images.  Every gather beat enters at the xg RING PINS (W / E line
# beats, own-leaf 4-fragment path, V-partner 4-fragment path; tb_s81sl_xg.cpp).  Positive cases must PASS; the offset-1
# load and the RTL mutants (3 ring stop, 2 x streamer) must FAIL.  Exit 0 = every verdict as expected.
# Verdict lines: XG_CASE <name> <PASS|FAIL> expected=<...> ok=<0|1>; final XG_BENCH PASS|FAIL.  With case names given, only
# those cases run (mutant witness runs).
set -u; O=$(realpath -m $1); shift; mkdir -p $O; ONLY="$*"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > $O/verilator_version.log
VROOT=$($V -V | sed -n 's/^ *VERILATOR_ROOT *= *//p' | head -1)
J=${J:-8}
CAT=results/rtl/dsrom_recovery_20261004/immutable_fullcatalog
MAC="physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
CAL="rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_rom.sv"
REFSRC="$(find physical/s81_pq_hier/pinned -name '*.sv' ! -name ot_sram_1r1w_128x256_m1_r2c2.sv | sort | tr '\n' ' ') $(ls rtl/dsrom_sys/s81_ph/pq/*.sv | tr '\n' ' ') rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv $CAL $MAC rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_xs_ref.sv"
REFDEF="+define+OT_PQ_ROM_PORTS +define+OT_PQ_CTL_STATIC +define+OT_PQ_QB_PIPE +define+OT_PQ_QB_PINREAD +define+OT_PQ_QB_PHYS_SPLIT +define+OT_PQ_AQ_PHYS_SPLIT +define+OT_PQ_IX_PHYS_SPLIT +define+OT_PQ_IX_BANK_SPLIT +define+OT_PQ_BC_SLICED +define+DSFD_PQ_STATIC_X2 +define+OT_PQ_CTL_STATE_PINS +define+OT_PQ_CTL_INCAP +define+OT_PQ_AQ_PIN_LAUNCH +define+OT_PQ_CTL_CALCAP +define+DSFD_PQ_ROM4"
XGSRC="rtl/lib/ot_rst_relay.sv rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv $CAL rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv $MAC rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs_ctl.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rs.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xg.sv"
AQSRC="physical/s81_pq_hier/pinned/rtl/ot_rst_relay.sv physical/s81_pq_hier/pinned/rtl/hdc/ot_hdc_delay.sv $(ls physical/s81_pq_hier/pinned/rtl/hdc/*.sv | grep -v ot_hdc_delay | tr '\n' ' ') physical/s81_pq_hier/pinned/rtl/common/ot_prefix.sv physical/s81_pq_hier/pinned/rtl/hdc/v41x/ot_dsrom_aq12m.sv physical/s81_pq_hier/pinned/rtl/hdc/v41x/ot_dsrom_aq12t.sv physical/s81_pq_hier/pinned/rtl/v41rom/ot_v41_kreg.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
VF="--cc -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0"
build() {  # name top defines srcs
  local n=$1 t=$2 d=$3; shift 3
  [ -f $O/$n/V${n}__ALL.a ] && return 0
  $V $VF --prefix V$n --top-module $t --Mdir $O/$n $d "$@" > $O/$n.verilate.log 2>&1 || { echo "BUILD_FAILED $n"; tail -5 $O/$n.verilate.log; exit 3; }
  make -C $O/$n -f V$n.mk -j$J V${n}__ALL.a OPT_FAST=-O1 OPT_SLOW=-O0 > $O/$n.make.log 2>&1 || { echo "BUILD_FAILED make $n"; tail -5 $O/$n.make.log; exit 3; }
}
want() { [ -z "$ONLY" ] && return 0; for c in $ONLY; do [ "$c" = "$1" ] && return 0; done; return 1; }
build ref tb_s81sl_xs_ref "$REFDEF" $REFSRC
build aq ot_dsrom_aq12t "" $AQSRC
link() {  # variant define
  local v=$1 d=$2 m=$O/xg_$1
  [ -x $O/tb_$v ] && return 0
  if [ ! -f $m/Vxg__ALL.a ]; then
    $V $VF --prefix Vxg --top-module ot_s81sl_xg --Mdir $m +define+DSFD_PQ_STATIC_X2 $d $XGSRC > $m.verilate.log 2>&1 || { echo "BUILD_FAILED xg $v"; tail -5 $m.verilate.log; exit 3; }
    make -C $m -f Vxg.mk -j$J Vxg__ALL.a OPT_FAST=-O1 OPT_SLOW=-O0 > $m.make.log 2>&1 || { echo "BUILD_FAILED make xg $v"; exit 3; }
  fi
  g++ -std=c++20 -O1 -I$VROOT/include -I$VROOT/include/vltstd -I$O/ref -I$O/aq -I$m rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_xg.cpp \
    $O/ref/Vref__ALL.a $O/aq/Vaq__ALL.a $m/Vxg__ALL.a $VROOT/include/verilated.cpp $VROOT/include/verilated_threads.cpp -pthread -o $O/tb_$v > $O/link_$v.log 2>&1 || { echo "BUILD_FAILED link $v"; tail -5 $O/link_$v.log; exit 3; }
}
ALL=1
case_run() {  # name variant expect(PASS|FAIL) program args...
  local n=$1 v=$2 e=$3; shift 3; local w=$O/case_$n
  want $n || return 0
  case $v in base) link base "";; mutfrag) link mutfrag "+define+OT_S81SL_RSTOP_MUT_FRAG";;
    mutvasm) link mutvasm "+define+OT_S81SL_RSTOP_MUT_VASM";; mutgswap) link mutgswap "+define+OT_S81SL_RSTOP_MUT_GSWAP";;
    mutbank) link mutbank "+define+OT_S81SL_XS_MUT_BANK";; mutoff) link mutoff "+define+OT_S81SL_XS_MUT_OFF";; esac
  python3 tools/s81_slice/xs_program.py --out $w --s0-stride 2 --xs-out 2 "$@" > $w.prog.log 2>&1 || { echo "XG_CASE $n SETUP_FAILED"; tail -3 $w.prog.log; ALL=0; return; }
  (cd $w && $O/tb_$v +work=$w +OT_ROM_DIR=$w > $w/run.log 2>&1)
  local got=FAIL; grep -q '^PASS xg_lockstep' $w/run.log && got=PASS
  grep -q '^SETUP_FAIL' $w/run.log && { got=SETUP_FAIL; }
  local ok=0; [ $got = $e ] && ok=1; [ $ok = 1 ] || ALL=0
  echo "XG_CASE $n $got expected=$e ok=$ok :: $(grep -h '^XS_PROGRAM' $w.prog.log | cut -c1-200)"
  grep -h '^XG_RING\|^XS_LOCKSTEP\|^FIRST MISMATCH\|^SETUP_FAIL' $w/run.log
}
L0="--stage-dir $CAT/stage0"; L2="--stage-dir $CAT/stage3"
case_run L0_near_s5   base PASS $L0 --order near --slice 5
case_run L0_far_s0    base PASS $L0 --order far --slice 0 --off 52
case_run L0_rand_s15  base PASS $L0 --order rand --slice 15 --seed 7 --off 29
case_run L2_near_s9   base PASS $L2 --order near --slice 9
case_run L2_rand_s3   base PASS $L2 --order rand --slice 3 --seed 11 --off 44
case_run L2_far_s14   base PASS $L2 --order far --slice 14 --off 61
case_run L0_rand_s8   base PASS $L0 --order rand --slice 8 --seed 3 --off 40
case_run L0_offm1     base FAIL $L0 --order near --slice 5 --off-load 36
case_run L0_mutfrag   mutfrag  FAIL $L0 --order near --slice 5
case_run L0_mutvasm   mutvasm  FAIL $L0 --order near --slice 5
case_run L0_mutgswap  mutgswap FAIL $L0 --order near --slice 5
case_run L0_mutbank   mutbank  FAIL $L0 --order near --slice 5
case_run L0_mutoff    mutoff   FAIL $L0 --order near --slice 5
[ $ALL = 1 ] && { echo "XG_BENCH PASS"; exit 0; }; echo "XG_BENCH FAIL"; exit 1
