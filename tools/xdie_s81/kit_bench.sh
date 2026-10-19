#!/bin/bash
# kit_bench.sh <outdir> <pass|board400|chb0>  (cwd = repo root): S81-LINKTO (0hn, 10-18) behavioural bench of the lane tile
# kits dsfd_coll_lane_w / dsfd_coll_lane_e on the TOKEN-XDIE-S81 vehicle tb_xdie_s81: 4 dies x 4 end-slice endpoints
# (ring stop + lep + 2 built lane tiles LCR 1 + 2 ot_pdie_serdes), one-tier switch legs (453 cycles = 377.6 ns), the
# reduced static TP4 calendar (a_allgather + stage_hop, 1 rep; board400: the full calendar) with compiled deadlines; lane tiles strapped ch_b 1.
#   pass      the built tiles (tile-top CH_BOARD 700): every beat bit-exact, in order, by its deadline, no fault -> PASS
#   board400  mutant: the tile top CH_BOARD 700 -> 400 (the pre-0hn tile; sed on the lane RTL) -> ACK timeouts before the
#             switched round trip, go-back-N replays, late landings -> must FAIL
#   chb0      mutant: ch_b strap 0 (CH_UCIE 100 basis on a switched lane) -> must FAIL
# Verdict lines: "PASS xdie_s81: ..." / "FAIL xdie_s81: ..." (+ XDIE_LINK timeouts / replayed flits).  Exit 0 = PASS.
set -u; O=$1; M=${2:-pass}; mkdir -p $O
# board400 runs the FULL dense calendar (12,096 beats, as gate_g5 board400): on the reduced calendar its 32 ACK timeouts
# are absorbed by deadline slack (measured 10-18: PASS with 2,760 replayed flits), so only the full calendar witnesses it.
if [ "$M" = board400 ]; then
  python3 tools/xdie_s81/gen_golden.py --out $O/gm --gap 100 --lat S=556,N=556 --per S=1.345,N=1.345 > $O/gen.txt 2>&1 \
    || { echo "GEN_FAILED"; tail -5 $O/gen.txt; exit 3; }
  A=""
else
  python3 tools/xdie_s81/gen_golden.py --out $O/gm --reps 1 --only a_allgather,stage_hop --lat S=556,N=556 --per S=1.345,N=1.345 \
    > $O/gen.txt 2>&1 || { echo "GEN_FAILED"; tail -5 $O/gen.txt; exit 3; }
  A="-GMAXCYC=40000"
fi
case $M in
  pass) ;;
  chb0) A="$A -GCHB=0" ;;
  board400)
    mkdir -p $O/mut
    # S81-SAFE-FIX/COLL 10-19: the tile tops now end '..CH_BOARD = 700, parameter integer SAFE = 1) (' (both forms matched)
    sed -E 's/parameter integer CH_BOARD = 700(, parameter integer SAFE = [01])?\) \(/parameter integer CH_BOARD = 400\1) (/' rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv > $O/mut/ot_s81ph_coll_lane.sv
    [ "$(grep -c -E 'parameter integer CH_BOARD = 400(, parameter integer SAFE = [01])?\) \(' $O/mut/ot_s81ph_coll_lane.sv)" = 2 ] || { echo "MUTANT_NOT_APPLIED"; exit 4; }
    export LANE=$O/mut/ot_s81ph_coll_lane.sv ;;
  *) echo "usage: kit_bench.sh <outdir> pass|board400|chb0"; exit 2 ;;
esac
J=${J:-6} bash tools/xdie_s81/run_xdie_s81.sh $O $M $O/gm ep $A; rc=$?
grep -h "^XDIE_LINK" $O/$M/run.log 2>/dev/null
exit $rc
