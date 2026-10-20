#!/bin/bash
# lepenh_parent_checks.sh <outdir> <what: bind|lockstep|slep|slep_swap>  (cwd = repo root; FLEET only via ot-run)
# S81-SLICE3-LEPENH 10-19: checks of the landed dsdv_slice_lepe_nh parent ot_s81sl_slice_lepe_nh_x_lp.
#   bind       tools/die_port_bind.py on the landed parent AND on the flat expansion (no tied / open / unbound child pin)
#   lockstep   lp.py lockstep bench landed vs flat + mutants + region audit (Verilator 5.050)
#   slep       slice_lep 2-die composition, die B = the landed parent (expect BENCH_PASS slice_lep)
#   slep_swap  same with OT_S81SL_LEP_MUT_SWAP (expect NEGATIVE_CONTROL_FAILED_AS_EXPECTED)
set -u; O=$1; W=$2; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version | head -1
L=rtl/dsrom_sys/s81_dv/slice/landed/lepe_nh
case $W in
bind)
  # the RTL closure the 2-die bench compiles (one definition per master: the bench's files win)
  rc=0
  for t in ot_s81sl_slice_lepe_nh_x_lp:$L/ot_s81sl_slice_lepe_nh_x_lp.sv ot_s81sl_slice_lepe_nh_x:$L/ot_s81sl_slice_lepe_nh_x.sv; do
    top=${t%%:*}; f=${t#*:}
    python3 tools/die_port_bind.py $f --top $top --define DSFD_PQ_STATIC_X2 --define OT_S81PH_LANE_CR \
      --rtl-file rtl/common/landed_parent/ot_pl_land.sv --prefer rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv \
      --prefer-list tools/s81_slice/slice_lep_bench.sh --out $O/bind_$top.json > $O/bind_$top.log 2>&1
    r=$?; echo "BIND $top exit $r"; tail -5 $O/bind_$top.log; [ $r -eq 0 ] || rc=1
  done
  echo "BIND_EXIT $rc"; exit $rc;;
lockstep)
  SIM=verilator VERILATOR=$V VL_JOBS=${J:-16} bash $L/ot_s81sl_slice_lepe_nh_x_lp_bench.sh $O;;
slep)      J=${J:-16} bash tools/s81_slice/slice_lep_bench.sh $O none lepe_nh_lp;;
slep_swap) J=${J:-16} bash tools/s81_slice/slice_lep_bench.sh $O swap lepe_nh_lp;;
*) echo "unknown $W"; exit 2;;
esac
