#!/bin/bash
# xrt_rfj_eq.sh (DIE-S81-52/RF-J 11-03; RL=2 FL=2 senders posedge; mutants rfj_rpos rfj_fpos) <outdir> <HB 0|1> <RL 0|1> [SEED] [NC] [mutant: none|rland_wv|rland_vpin|olat_pos|land_pv]  env OL=1 (default): out-face latches  env PDC=1 (default): DUT built with OT_S81SL_XR_PDC   (cwd = repo root)
# env SPARSE=1: rare full-set valids (few sticky faults), J = verilator build jobs.
# DIE-S81-51/RF-B 11-03 (from xrt_land_eq.sh): ot_s81sl_xrt RING_LAND (+ XR8 predecode) vs the REF_REV module (default
# origin/main, plain, no predecode) with the ring / band inputs one edge later (RL = 1) or undelayed (RL = 0). FACE_LAND 1 both.  Every output bit, every cycle.  base must PASS; mutants FAIL.
set -u; O=$1; H=$2; L=$3; S=${4:-1}; N=${5:-20000}; M=${6:-none}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
command -v $V >/dev/null || V=$HOME/.local/opentallas-tools/bin/verilator
{ if [ "${REF_REV:-origin/main}" = WT ]; then cat rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv
  else git show ${REF_REV:-origin/main}:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv; fi; } | sed -e 's/\bot_s81sl_xrt\b/ref_s81sl_xrt/g' \
  -e 's/\bot_s81sl_xrt1\b/ref_s81sl_xrt1/g' -e 's/\bot_s81sl_xrt3\b/ref_s81sl_xrt3/g' -e 's/\bot_s81sl_xr_cp\b/ref_s81sl_xr_cp/g' \
  -e 's/\bot_s81sl_xr_rcp\b/ref_s81sl_xr_rcp/g' -e 's/^`define OT_S81SL_XR_FOREG_DEF/`define REF_XR_FOREG_DEF/' \
  -e 's/`OT_S81SL_XR_FOREG_DEF/`REF_XR_FOREG_DEF/g' -e 's/OT_S81SL_XRT_PDSK_DEF/REF_XRT_PDSK_DEF/g' -e 's/OT_S81SL_XR_PDC/REF_XR_PDC_OFF/g' -e 's/OT_S81SL_XRT_RLAND/REF_XRT_RLAND_OFF/g' > $O/ref_s81sl_xrt.sv
grep -q "module ref_s81sl_xrt1" $O/ref_s81sl_xrt.sv || { echo "REF_NOT_BUILT"; exit 4; }
DEF="${EQ_DEF:-}"; [ "${PDC:-1}" = 1 ] && DEF="$DEF +define+OT_S81SL_XR_PDC"
case $M in rland_wv) DEF="$DEF +define+OT_S81SL_XRT_MUT_RLAND_WV";; rland_vpin) DEF="$DEF +define+OT_S81SL_XRT_MUT_RLAND_VPIN";;
  land_pv) DEF="$DEF +define+OT_S81SL_XRT_MUT_LAND_PV";; rfj_rpos) DEF="$DEF +define+OT_S81SL_XRT_MUT_RFJ_RPOS";; rfj_fpos) DEF="$DEF +define+OT_S81SL_XRT_MUT_RFJ_FPOS";; olat_pos) DEF="$DEF +define+OT_S81SL_XRT_MUT_OLAT_POS";; none) ;; *) exit 2;; esac
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF -GHB=$H -GLAND=0 -GFL=${FL:-2} -GRL=$L -GOL=${OL:-1} -GSEED=$S -GNC=$N -GSPARSE=${SPARSE:-0} \
  --top-module tb_s81sl_xrt_rfj_eq -Mdir $O/obj rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv \
  $O/ref_s81sl_xrt.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_xrt_rfj_eq.sv --build-jobs ${J:-4} \
  -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
$O/obj/Vtb_s81sl_xrt_rfj_eq > $O/run.log 2>&1
grep -E "^LANDEQ" $O/run.log | head -6
if [ "$M" = none ]; then grep -q '^PASS' $O/run.log && { echo "PASS xrt_rland_eq pdc=${PDC:-1} ol=${OL:-1} hb=$H rl=$L seed=$S"; exit 0; }; echo "FAIL xrt_rland_eq"; exit 1; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
