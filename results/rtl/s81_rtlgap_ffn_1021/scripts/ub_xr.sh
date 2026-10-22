#!/bin/bash
# RG-FFN: existing XR bench (tools/s81_slice/xr_bench.sh / tb_s81sl_xr.sv) against ot_s81sl_xrt1 / xrt3 (tb copy with the
# module names substituted).  ub_xr.sh <tag> <mode> <seed> <HB>; base must PASS, mutants must FAIL.
set -u; S=$(pwd); M=$2; SD=$3; H=$4; O=$S/ub_xr_$1_${M}_s${SD}_h$H; mkdir -p $O; cd $S/src
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
# legal-program constraint of the transport (new): random send configs keep body[44] (s_local) = 0 and never form the pair
# mode (dir V only + kind RD) -- those are covered by the transport cut bench (ub_rdp.sh); everything else is unchanged
sed -e 's/ot_s81sl_xr3 u (/ot_s81sl_xrt3 u (/' -e 's/ot_s81sl_xr1 u (/ot_s81sl_xrt1 u (/' \
    -e 's/^\( *\)body\[43\] = ru(3) == 0;/&\n\1body[44] = 1'"'"'b0; if (body[3:0] == 4'"'"'b0100 \&\& body[6:4] == 3'"'"'d4) body[6:4] = 3'"'"'d0;/' \
    -e 's/^\( *\)i_vv\[n\] = 1; i_vb\[n\]\[3:1\] = 3'"'"'d1 + ru(7);/&\n\1if (i_vb[n][3:1] == 3'"'"'d4) i_vb[n][3:1] = 3'"'"'d5;   \/\/ RG-FFN: V RD = transport word (ub_rdp)/' \
    rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_xr.sv > $O/tb_s81sl_xr.sv
grep -n "RG-FFN: V RD" $O/tb_s81sl_xr.sv >> $O/constraint.txt || { echo CONSTRAINT2_NOT_APPLIED; exit 4; }
grep -n "body\[44\]" $O/tb_s81sl_xr.sv >> $O/constraint.txt || { echo CONSTRAINT_NOT_APPLIED; exit 4; }
DEF=""; case $M in hops) DEF="+define+OT_S81SL_XR_MUT_HOPS";; row) DEF="+define+OT_S81SL_XR_MUT_ROW";;
  porder) DEF="+define+OT_S81SL_XR_MUT_PORDER";; nocol) DEF="+define+OT_S81SL_XR_MUT_NOCOL";;
  bwide) DEF="+define+OT_S81SL_XR_MUT_BWIDE";; xhold) DEF="+define+OT_S81SL_XR_MUT_XHOLD";; soen) DEF="+define+OT_S81SL_XR_MUT_SOEN";; base) ;; *) echo BAD; exit 2;; esac
$V --version > $O/verilator.version
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF -GHB=$H -GSEED=$SD -GNC=6000 --top-module tb_s81sl_xr \
  -Mdir $O/obj rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv $O/tb_s81sl_xr.sv --build-jobs 4 \
  -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED $M"; grep -m8 "%Error" $O/build.log; exit 3; }
$O/obj/Vtb_s81sl_xr > $O/run.log 2>&1
grep -E "MISMATCH" $O/run.log | head -4
if [ "$M" = base ]; then grep -q '^PASS' $O/run.log && { echo "PASS xrt base hb=$H seed=$SD"; exit 0; }; echo "FAIL xrt base hb=$H seed=$SD"; exit 1; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M hb=$H"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M hb=$H (bench blind)"; exit 1
