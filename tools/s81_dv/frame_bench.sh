#!/bin/bash
# frame_bench.sh <outdir> [MASTER=col_h9] [MUT=0|xlane|marker|tree|cfgbank|noskew] (cwd = repo root): the exact S81-DV frame bench
# (tools/s81_dv/frame_bench.py; tb rtl/dsrom_sys/s81_dv/frame/test/tb_s81dv_frame.sv).  MUT 0 = the emitted wrapper
# (rtl/dsrom_sys/s81_dv/frame/<MASTER>.sv) must PASS; a mutant re-emits the wrapper with one wiring fault into <outdir>
# (tools/s81_dv/frame_wrap.py emit --mutant) and must FAIL.  Exit 0 = the expected verdict.
# One build; vector sets (SET):
#   each (default)  one run per q element k of the frame (gen --only k): that element alone holds MATS (4) one-row
#                   K-1024 matrices (4 super rows, macro b idle: no same-edge r0 / r1 leaf pair), so
#                   every q element's x / cfg / ROM / leaf path and its return path to the root is exercised exactly
#   plan            one run, ALL 12 q elements in one K-split phase (K 2048, NSEG 4 segments, 3 super rows = 6 rows, one
#                   segment per element) placed by the frame return legaliser (tools/s81_dv/frame_return_plan.py, D2):
#                   every row must reach the root, 0 faults, and the ret words must equal the compiler's calendar
#                   (edge, tag, value) exactly
#   all             one run, all 12 q elements share one phase placed by the image writer's LPT (ROWS 8, K-split), which
#                   ignores the return tree -- diagnostic only (D2: F1 collisions without the legaliser)
# Env: SEED (1), ROWS, MATS, KK, CYC (3000), J (build jobs, 8), VFLAGS (extra verilator flags).
# L4=1 (S81-LAND2): bench the successor <MASTER>_l4 (tools/s81_dv/frame_l4.py: column FIFO dsfd_cfifo_crs4, per-lane
#   landings) through its bench wrapper <MASTER>_l4_b with lane strap K = LK (default 2); MUT=xlane re-derives the
#   successor with lanes 1 / 2 swapped (frame_l4.py --mutant xlane).  The vectors and the check are the base master's.
#   NX=1 (with L4=1, BIND/mu4): bench the chain-end variant <MASTER>_l4_nx (no x forward) via <MASTER>_l4_nx_b.
#   L4 drives the lanes as the die does (tb TB_FWD_GATE: hop-0 gate opened at the frame reset release, lane ck_f + data
#   LDLY whole periods late, default 0) and the plan set predicts the crs4 calendar (--land-e LK: x_shift = LK - 6).
set -u
O=$1; MASTER=${2:-col_h9}; MUT=${3:-0}; SET=${SET:-each}
mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
FL=tools/s81_dv/frame_bench.f
TOPF=""; DFR=$MASTER
if [ "${FRAME_LP:-0}" = 1 ]; then
  FR=rtl/dsrom_sys/s81_dv/frame_lp
  case "$MUT" in 0) LM=0;; unland) LM=1;; landread) LM=2;; reset) LM=4;; *) echo "Unknown landed mutant $MUT"; exit 3;; esac
  DFR=${MASTER}_l4_lp_b; SFX=_l4_lp
  TOPF="$FR/${MASTER}_l4_lp_b.sv rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv rtl/common/landed_parent/ot_pl_land.sv"
  # S81-FRAME4 10-19: an LP spec with landing_reset_forest instantiates the kept-copy forest primitives
  grep -q ot_pl_land_reset_forest $FR/${MASTER}_l4_lp.sv && TOPF="$TOPF rtl/common/landed_parent/ot_pl_land_field_copies.sv rtl/common/landed_parent/ot_pl_land_reset_forest.sv"
  # FRRST 10-20: FRAME_LP_SV = a kit-variant bench twin of the LP RTL (tools/s81_dv/frame_kit.py variant --xk-land) in
  # place of <MASTER>_l4_lp.sv (same module name); its xk reset synchronisers need ot_reset_sync
  LPSV=${FRAME_LP_SV:-$FR/${MASTER}_l4_lp.sv}
  grep -q ot_reset_sync $LPSV && TOPF="$TOPF rtl/lib/ot_reset_sync.sv"
  # S81-P7 10-23: a banded seam twin (vgcs, tools/s81_dv/frame_seam_pipe.py) uses ot_pl_seam_w/r; SEAM_SV = a re-timed
  # seam primitive (bench mutant, tools/s81_dv/frame_seam_bench.sh)
  grep -q ot_pl_seam_ $LPSV && TOPF="$TOPF ${SEAM_SV:-rtl/common/landed_parent/ot_pl_seam.sv}"
  VFLAGS="${VFLAGS:-} -DLP_MUT=$LM -DLK=${LK:-2} -DTB_FWD_GATE -DTB_LDLY=${LDLY:-0}"
  # STW-S81c-DIE-FRAME 10-22: FRAME_SCHED = the schedule of a re-cut LP variant (default: the committed one)
  LANDE="--land-e ${LK:-2} --frame-schedule ${FRAME_SCHED:-results/arch/s81_dv_1016/frame_l4_cluster/compiler/${MASTER}_schedule.json}"
elif [ "${L4:-0}" = 1 ]; then
  if [ "$MUT" = 0 ]; then FR=rtl/dsrom_sys/s81_dv/frame_l4; else
    [ -f $O/rtl/${MASTER}_l4.sv ] || python3 tools/s81_dv/frame_l4.py --mutant $MUT --out-rtl $(realpath $O)/rtl > $O/mutant.log 2>&1 || { echo "MUTANT_EMIT_FAILED"; tail -n 3 $O/mutant.log; exit 3; }
    FR=$(realpath $O)/rtl; fi
  TOPF="$FR/${MASTER}_l4_b.sv rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv"
  # col_h9_MX_l4 = the col_h9_l4 RTL in a mirrored-placement wrapper: build both, vectors / check are col_h9's
  case $MASTER in *_MX) TOPF="$TOPF $FR/${MASTER%_MX}_l4.sv"; VMASTER=${MASTER%_MX};; esac
  DFR=${MASTER}_l4_b; SFX=_l4; VFLAGS="${VFLAGS:-} -DLK=${LK:-2} -DTB_FWD_GATE -DTB_LDLY=${LDLY:-0}"; LANDE="--land-e ${LK:-2}"
  # NX=1 (BIND/mu4): the chain-end successor <MASTER>_l4_nx (no xo / xok) through <MASTER>_l4_nx_b (relays re-attached bench-side)
  if [ "${NX:-0}" = 1 ]; then case $MASTER in *_MX) echo "NX has no MX variant"; exit 3;; esac
    TOPF="$FR/${MASTER}_l4_nx_b.sv ${TOPF#$FR/${MASTER}_l4_b.sv }"; DFR=${MASTER}_l4_nx_b; SFX=_l4_nx; fi
elif [ "$MUT" = 0 ]; then FR=rtl/dsrom_sys/s81_dv/frame; else
  [ -f $O/rtl/$MASTER.sv ] || python3 tools/s81_dv/frame_wrap.py emit --mutant $MUT --out-rtl $(realpath $O)/rtl > $O/mutant.log 2>&1 || { echo "MUTANT_EMIT_FAILED"; tail -n 3 $O/mutant.log; exit 3; }
  FR=$(realpath $O)/rtl; fi
# S81-P8 10-23: BF_LEGACY=1 = the BF16 programme MEASUREMENT build of tools/s81_dv/layer_prog/xs/xs_bench.sh on THIS
# frame (e.g. FRAME_LP=1 + the vgcs twin): a patched COPY of the BF core in <outdir>/probe issues on its walker
# availability, + TB_BFTRACE (BFG / BFI / BFPV lines for xs_bf.py measure).  The repository source is untouched.
if [ "${BF_LEGACY:-0}" = 1 ]; then
  CORE=rtl/v41rom/ot_v41_bf_front_core_roots.sv; mkdir -p $O/probe
  sed 's#^    wire issue = (STATIC_PROGRAM != 0) ? prog_issue_u : issue_available;#    wire issue = issue_available;   // XS2 MEASUREMENT PROBE (BF_LEGACY)#' $CORE > $O/probe/ot_v41_bf_front_core_roots.sv
  [ "$(grep -c 'XS2 MEASUREMENT PROBE' $O/probe/ot_v41_bf_front_core_roots.sv)" = 1 ] || { echo "BF_LEGACY_PATCH_FAILED"; exit 3; }
  grep -v "^$CORE\$" $FL > $O/probe/frame_bench.f; echo $O/probe/ot_v41_bf_front_core_roots.sv >> $O/probe/frame_bench.f
  FL=$O/probe/frame_bench.f; VFLAGS="${VFLAGS:-} -DTB_BFTRACE"
fi
if [ ! -x $O/obj/Vtb_s81dv_frame ]; then
  /usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style \
    -Wno-MULTIDRIVEN ${VFLAGS:-} -DFRAME=$DFR -DDSFD_PQ_STATIC_X2 -DDSFD_PQ_HAS_BF_X2 --top-module tb_s81dv_frame -Mdir $O/obj \
    -f $FL ${LPSV:-$FR/$MASTER${SFX:-}.sv} $TOPF rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv rtl/dsrom_sys/s81_dv/frame/test/tb_s81dv_frame.sv \
    --build-jobs ${J:-8} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
    || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
fi
if [ "$SET" = all ] || [ "$SET" = plan ]; then KS="$SET"; else
  KS=$(python3 -c "import sys; sys.path.insert(0, 'tools/s81_dv'); import frame_bench as B; print(' '.join(map(str, B.frame_pairs('${VMASTER:-$MASTER}')[0])))") \
    || { echo "BENCH_SETUP_FAILED frame_pairs $MASTER"; exit 4; }; fi
# fail closed (LANDFIX-SQ/F 10-18): an empty vector set ran nothing -- never a pass, never a caught mutant
[ -n "$KS" ] || { echo "BENCH_SETUP_FAILED no vector sets for $MASTER"; exit 4; }
npass=0; nfail=0
for k in $KS; do
  VD=$O/vec_$k
  if [ "$k" = all ]; then A="--rows ${ROWS:-8} --mats ${MATS:-1} --K ${KK:-2048}"
  elif [ "$k" = plan ]; then A="--plan --nseg ${NSEG:-4} --K ${KK:-2048} ${LANDE:-}"; else A="--rows ${ROWS:-1} --mats ${MATS:-4} --K ${KK:-1024} --only $k"; fi
  [ -f $VD/meta.json ] || python3 tools/s81_dv/frame_bench.py gen --master ${VMASTER:-$MASTER} --out $VD --seed ${SEED:-1} $A \
     --cycles ${CYC:-3000} > $O/gen_$k.log 2>&1 || { echo "BENCH_SETUP_FAILED gen $k"; tail -n 3 $O/gen_$k.log; exit 4; }
  $O/obj/Vtb_s81dv_frame $(cat $VD/ARGS) > $O/run_$k.log 2>&1
  if python3 tools/s81_dv/frame_bench.py check --dir $VD --log $O/run_$k.log > $O/check_$k.log 2>&1; then npass=$((npass+1))
  else nfail=$((nfail+1)); fi
  echo "  [$k] $(tail -n 1 $O/check_$k.log)"
done
echo "FRAME_SET $MASTER MUT=$MUT set=$SET pass=$npass fail=$nfail"
if [ "$MUT" = 0 ]; then [ $nfail = 0 ] && [ $npass -gt 0 ] && { echo "PASS frame $MASTER"; exit 0; }; echo "FAIL frame $MASTER"; exit 1; fi
[ $nfail -gt 0 ] && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$MUT $MASTER"; exit 0; }
echo "NEGATIVE_CONTROL_PASSED MUT=$MUT $MASTER (bench blind)"; exit 1
