#!/bin/bash
# xrt_bench.sh <outdir> [base|hops|row|porder|nocol|bwide|xhold|landpv|dsk] [SEED] [HB 0|1] [NC] [raw]  (cwd = repo root)
# env XR_LAND=1: FACE_LAND = 1 DUT + OT_XR_LAND_TB tb; extra mode landpv (+define+OT_S81SL_XRT_MUT_LAND_PV) must FAIL.
# env XR_DSK (TOK-DS NORM-DESKEW 10-25; the masters default to the per-leaf norm deskew PDSK = 15'o01234):
#   1 (default) = OT_XR_DSK_TB tb (staggered partial sets, xfin +4, 3 more illegal cases); extra mode dsk
#     (+define+OT_S81SL_XRT_MUT_DSK, leaf 2 one edge too deep) must FAIL.
#   0 = legacy: +define+OT_S81SL_XRT_NO_DSK (PDSK = 0, the pre-deskew masters) + the aligned-set tb.
#   2 = evidence only: the aligned-set tb against the default deskew masters; base must FAIL (old schedule now faults).
# STW-S81-COLLA-XRT 10-21: the existing XR control-plane bench (tb_s81sl_xr.sv, xr_bench.sh flow) against the FFN result
# transport masters ot_s81sl_xrt1 / ot_s81sl_xrt3 -- the RG-FFN ub_xr.sh recipe (results/rtl/s81_rtlgap_ffn_1021/scripts):
# tb copy with the module names substituted + the transport legal-program constraint (random send configs keep
# body[44] = 0 and never form the pair mode; random V kind never draws RD).  XR_FOREG=1 -> +define+OT_S81SL_XR_FOREG.
# base must PASS; mutants must FAIL ('raw' = report the mutant's own verdict: exit 1 on FAIL, for expect=fail benches).
set -u; O=$1; M=${2:-base}; S=${3:-1}; H=${4:-0}; N=${5:-6000}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
sed -e 's/ot_s81sl_xr3 u (/ot_s81sl_xrt3 u (/' -e 's/ot_s81sl_xr1 u (/ot_s81sl_xrt1 u (/' \
    -e 's/^\( *\)body\[43\] = ru(3) == 0;/&\n\1body[44] = 1'"'"'b0; if (body[3:0] == 4'"'"'b0100 \&\& body[6:4] == 3'"'"'d4) body[6:4] = 3'"'"'d0;/' \
    -e 's/^\( *\)i_vv\[n\] = 1; i_vb\[n\]\[3:1\] = 3'"'"'d1 + ru(7);/&\n\1if (i_vb[n][3:1] == 3'"'"'d4) i_vb[n][3:1] = 3'"'"'d5;/' \
    rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_xr.sv > $O/tb_s81sl_xrt.sv
grep -q "ot_s81sl_xrt[13] u (" $O/tb_s81sl_xrt.sv && grep -q "body\[44\] = 1'b0" $O/tb_s81sl_xrt.sv \
  && grep -q "i_vb\[n\]\[3:1\] = 3'd5" $O/tb_s81sl_xrt.sv || { echo "CONSTRAINT_NOT_APPLIED"; exit 4; }
DEF=""; case $M in hops) DEF="+define+OT_S81SL_XR_MUT_HOPS";; row) DEF="+define+OT_S81SL_XR_MUT_ROW";;
  porder) DEF="+define+OT_S81SL_XR_MUT_PORDER";; nocol) DEF="+define+OT_S81SL_XR_MUT_NOCOL";;
  bwide) DEF="+define+OT_S81SL_XR_MUT_BWIDE";; xhold) DEF="+define+OT_S81SL_XR_MUT_XHOLD";; landpv) DEF="+define+OT_S81SL_XRT_MUT_LAND_PV";;
  dsk) DEF="+define+OT_S81SL_XRT_MUT_DSK";; base) ;; *) echo "BAD_MODE $M"; exit 2;; esac
case ${XR_DSK:-1} in 1) DEF="$DEF +define+OT_XR_DSK_TB";; 0) DEF="$DEF +define+OT_S81SL_XRT_NO_DSK";; 2) ;;
  *) echo "BAD_XR_DSK ${XR_DSK}"; exit 2;; esac
[ "$M" = dsk ] && [ "${XR_DSK:-1}" != 1 ] && { echo "BAD_MODE dsk needs XR_DSK=1"; exit 2; }
[ "${XR_FOREG:-0}" = 1 ] && DEF="$DEF +define+OT_S81SL_XR_FOREG"
[ "${XR_PDC:-0}" = 1 ] && DEF="$DEF +define+OT_S81SL_XR_PDC"   # STW-S81c-COLLA 10-22: pin predecode (XR8)
# S81-KITS-RTLB 10-24: XR_LAND=1 -> the DUT with FACE_LAND = 1 (lo / p / e leaf-interface landing, +1 cycle) and the tb in
# OT_XR_LAND_TB mode (the compiler issues lo / p one cycle earlier; expected outputs unchanged)
if [ "${XR_LAND:-0}" = 1 ]; then DEF="$DEF +define+OT_XR_LAND_TB"
  sed -i -e 's/ot_s81sl_xrt3 u (/ot_s81sl_xrt3 #(.FACE_LAND(1)) u (/' -e 's/ot_s81sl_xrt1 u (/ot_s81sl_xrt1 #(.FACE_LAND(1)) u (/' $O/tb_s81sl_xrt.sv
  grep -q "FACE_LAND(1)) u (" $O/tb_s81sl_xrt.sv || { echo "LAND_NOT_APPLIED"; exit 4; }; fi
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF -GHB=$H -GSEED=$S -GNC=$N --top-module tb_s81sl_xr \
  -Mdir $O/obj rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv $O/tb_s81sl_xrt.sv --build-jobs ${J:-4} \
  -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
$O/obj/Vtb_s81sl_xr > $O/run.log 2>&1
grep -E "MISMATCH" $O/run.log | head -8; grep -E "^XRB|^XRILL" $O/run.log
if [ "$M" = base ]; then grep -q '^PASS' $O/run.log && { echo "PASS xrt base hb=$H seed=$S"; exit 0; }; echo "FAIL xrt"; exit 1; fi
[ "${6:-}" = raw ] && { grep -q '^PASS' $O/run.log && exit 0; exit 1; }
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
