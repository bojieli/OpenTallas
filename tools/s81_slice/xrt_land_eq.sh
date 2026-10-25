#!/bin/bash
# xrt_land_eq.sh <outdir> <HB 0|1> <LAND 0|1> [SEED] [NC] [mutant: none|land_pv|land_evpin|citwin|fpin]   (cwd = repo root)
# env SPARSE=1: rare full-set valids (few sticky faults), J = verilator build jobs.
# S81-KITS-RTLB 10-24: ot_s81sl_xrt FACE_LAND vs the pre-fix module (REF_REV, default origin/main) with the lo / p / e
# inputs one edge later (LAND = 1) or undelayed (LAND = 0).  Every output bit, every cycle.  base must PASS; mutants FAIL.
set -u; O=$1; H=$2; L=$3; S=${4:-1}; N=${5:-20000}; M=${6:-none}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
command -v $V >/dev/null || V=$HOME/.local/opentallas-tools/bin/verilator
git show ${REF_REV:-origin/main}:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv | sed -e 's/\bot_s81sl_xrt\b/ref_s81sl_xrt/g' \
  -e 's/\bot_s81sl_xrt1\b/ref_s81sl_xrt1/g' -e 's/\bot_s81sl_xrt3\b/ref_s81sl_xrt3/g' -e 's/\bot_s81sl_xr_cp\b/ref_s81sl_xr_cp/g' \
  -e 's/\bot_s81sl_xr_rcp\b/ref_s81sl_xr_rcp/g' -e 's/^`define OT_S81SL_XR_FOREG_DEF/`define REF_XR_FOREG_DEF/' \
  -e 's/`OT_S81SL_XR_FOREG_DEF/`REF_XR_FOREG_DEF/g' > $O/ref_s81sl_xrt.sv
grep -q "module ref_s81sl_xrt1" $O/ref_s81sl_xrt.sv || { echo "REF_NOT_BUILT"; exit 4; }
DEF=""; case $M in land_pv) DEF="+define+OT_S81SL_XRT_MUT_LAND_PV";; land_evpin) DEF="+define+OT_S81SL_XRT_MUT_LAND_EVPIN";;
  citwin) DEF="+define+OT_S81SL_XRT_MUT_CITWIN";; fpin) DEF="+define+OT_S81SL_XRT_MUT_FPIN";; none) ;; *) exit 2;; esac
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF -GHB=$H -GLAND=$L -GSEED=$S -GNC=$N -GSPARSE=${SPARSE:-0} \
  --top-module tb_s81sl_xrt_land_eq -Mdir $O/obj rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv \
  $O/ref_s81sl_xrt.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_xrt_land_eq.sv --build-jobs ${J:-4} \
  -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
$O/obj/Vtb_s81sl_xrt_land_eq > $O/run.log 2>&1
grep -E "^LANDEQ" $O/run.log | head -6
if [ "$M" = none ]; then grep -q '^PASS' $O/run.log && { echo "PASS xrt_land_eq hb=$H land=$L seed=$S"; exit 0; }; echo "FAIL xrt_land_eq"; exit 1; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
