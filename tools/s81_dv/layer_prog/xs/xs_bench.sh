#!/bin/bash
# xs_bench.sh <outdir> <vecdir>... (cwd = kit / repo root): LB2-S81/CC-xs frame bench.  ONE Verilator build of the die
# frame master's _l4 successor (rtl/dsrom_sys/s81_dv/frame_l4/<MASTER>_l4_b.sv: dsfd_cfifo_crs4, lane strap LK) in the
# frame testbench rtl/dsrom_sys/s81_dv/frame/test/tb_s81dv_frame.sv (TB_FWD_GATE: the die's forwarded lanes), exactly
# the build of tools/s81_dv/frame_bench.sh L4=1; then one run per vector dir made by
#   python3 tools/s81_dv/layer_prog/lower_xs.py gen --frame <die frame> --out <vecdir> [--mutant swap|shift]
# (real L0 a_proj rows, the lowering's images and return calendar).  Logs: <outdir>/run_<vec>.log; the check is
#   python3 tools/s81_dv/layer_prog/lower_xs.py check --dir <vecdir> --log <outdir>/run_<vec>.log
# Env: MASTER (col_h9), LK (5), XS_DEFS (extra defines, e.g. -DTB_PVTRACE: element PV edge trace), LDLY (3: the landing window (LK - 4) T < dL < LK T, LANDING-CONTRACT; LDLY 0 at LK 5 is the
# window violation of landing/frame_l4_bench b2/h9_k5_d0), J (8).  Verilator = the closure daemon's 5.050.
set -u
O=$(realpath -m $1); shift; mkdir -p $O
MASTER=${MASTER:-col_h9}; LK=${LK:-5}; LDLY=${LDLY:-3}
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > $O/verilator.version
FR=rtl/dsrom_sys/s81_dv/frame_l4
TOPF="$FR/${MASTER}_l4_b.sv rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv"
SRCS="$FR/${MASTER}_l4.sv $TOPF rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv rtl/dsrom_sys/s81_dv/frame/test/tb_s81dv_frame.sv"
# BF_LEGACY=1 (TOK-S81-GAPS/XS2): the BF16 programme MEASUREMENT build -- a patched COPY of the BF core in the build dir
# whose issue is its own walker availability (the legacy calendar the compiled programme must reproduce), + TB_BFTRACE.
# The repository source is untouched; production benches never set it.
FL=tools/s81_dv/frame_bench.f
if [ "${BF_LEGACY:-0}" = 1 ]; then
  CORE=rtl/v41rom/ot_v41_bf_front_core_roots.sv
  mkdir -p $O/probe
  sed 's#^    wire issue = (STATIC_PROGRAM != 0) ? prog_issue_u : issue_available;#    wire issue = issue_available;   // XS2 MEASUREMENT PROBE (BF_LEGACY)#' $CORE > $O/probe/ot_v41_bf_front_core_roots.sv
  [ "$(grep -c 'XS2 MEASUREMENT PROBE' $O/probe/ot_v41_bf_front_core_roots.sv)" = 1 ] || { echo "BF_LEGACY_PATCH_FAILED"; exit 3; }
  grep -v "^$CORE\$" tools/s81_dv/frame_bench.f > $O/probe/frame_bench.f; echo $O/probe/ot_v41_bf_front_core_roots.sv >> $O/probe/frame_bench.f
  FL=$O/probe/frame_bench.f; XS_DEFS="${XS_DEFS:-} -DTB_BFTRACE"
fi
if [ ! -x $O/obj/Vtb_s81dv_frame ]; then
  /usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style \
    -Wno-MULTIDRIVEN -DLK=$LK -DTB_FWD_GATE -DTB_LDLY=$LDLY -DFRAME=${MASTER}_l4_b ${XS_DEFS:-} -DDSFD_PQ_STATIC_X2 -DDSFD_PQ_HAS_BF_X2 \
    --top-module tb_s81dv_frame -Mdir $O/obj -f $FL $SRCS \
    --build-jobs ${J:-8} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
    || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
fi
# every file the build read (the .f list + the top files), hashed
{ grep -v '^+incdir' $FL; echo $SRCS | tr ' ' '\n'; } | sort -u | xargs sha256sum > $O/sources.sha256
for VD in "$@"; do
  n=$(basename $VD)
  $O/obj/Vtb_s81dv_frame $(sed "s#+OT_ROM_DIR=[^ ]*#+OT_ROM_DIR=$(realpath $VD)#" $VD/ARGS) > $O/run_$n.log 2>&1
  echo "XS_RUN $n rc=$? $(grep -m1 '^END' $O/run_$n.log)"
done
echo XS_BENCH_DONE
