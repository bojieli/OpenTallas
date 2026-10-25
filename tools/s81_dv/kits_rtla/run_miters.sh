#!/bin/bash
# S81-KITS-RTLA (2026-10-24): old-vs-new lockstep miters of the 0-cycle pin-register fixes, with one sed mutant each
# (the duplicated state update dropped) that must FAIL.   run_miters.sh <work dir> <old kit rtl root> [cycles]
#   <old kit rtl root>/<kit>/rtl/ holds the exact RTL the c2 kits synthesised (the "old" side).
# Run from the repo root (fixed RTL = the working tree).  Prints MITERS PASS when every base PASSes and every mutant FAILs.
set -u
W=$(realpath -m ${1:?work}); K=${2:?old kit root}; N=${3:-40000}; mkdir -p $W
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
G=tools/s81_dv/kits_rtla/miter_gen.py
MAC=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
# kit -> top, old file, sources (fixed, repo paths; the kit's own list with the macro bb -> behavioural model)
srcs() {  # $1 kit dir: VERILOG_FILES of its config.mk mapped to repo paths
  for f in $(sed -n 's/^export VERILOG_FILES = //p' $K/$1/config.mk); do
    b=$(basename $f)
    case $b in *_bb.v) echo $MAC;; *) git ls-files "rtl/*$b" | grep "/$b$" | grep -v '/test/' | head -1;; esac
  done
}
declare -A TOP=([ot_s81sl_vsw_c]=ot_s81sl_vsw [ot_s81sl_vn_c]=ot_s81sl_vn [ot_s81sl_ve_c]=ot_s81sl_ve
                [ot_dsrom_su_hcpost_lane_pr_c]=ot_dsrom_su_hcpost_lane_pr)
declare -A EXTRA=([ot_dsrom_su_hcpost_lane_pr_c]=":ot_dsrom_su_hcpost_lane")
declare -A OLDF=([ot_s81sl_vsw_c]=ot_s81sl_vsw.sv [ot_s81sl_vn_c]=ot_s81sl_vn.sv [ot_s81sl_ve_c]=ot_s81sl_ve.sv
                 [ot_dsrom_su_hcpost_lane_pr_c]=ot_dsrom_su_hcpost_lane_pr.sv+KITRTL/ot_dsrom_su_hcpost.sv)
declare -A NEWF=([ot_s81sl_vsw_c]=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vsw.sv [ot_s81sl_vn_c]=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv
                 [ot_s81sl_ve_c]=rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv [ot_dsrom_su_hcpost_lane_pr_c]=rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv)
# mutant: file, exact old text, new text (drop the duplicated state update; ve: the pin flop loads the old state instead
# of the next value -- dropping ve's fault_s update is masked: every OR term but f_lock is itself sticky in ve's units)
declare -A MF=([ot_s81sl_vsw_c]=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vsw.sv [ot_s81sl_vn_c]=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv
               [ot_s81sl_ve_c]=rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv [ot_dsrom_su_hcpost_lane_pr_c]=rtl/hdc/v41x/ot_dsrom_su_hcpost.sv)
declare -A MO=([ot_s81sl_vsw_c]='od_h <= od_n;' [ot_s81sl_vn_c]='fault_s <= fault_n;' [ot_s81sl_ve_c]='fault <= fault_n; fault_s'
               [ot_dsrom_su_hcpost_lane_pr_c]='else q <= q | x;')
declare -A MN=([ot_s81sl_vsw_c]='od_h <= od_h;' [ot_s81sl_vn_c]='fault_s <= 1'"'"'b0;' [ot_s81sl_ve_c]='fault <= fault_s; fault_s'
               [ot_dsrom_su_hcpost_lane_pr_c]='else q <= 1'"'"'b0;')
declare -A DEF=([ot_s81sl_ve_c]="+define+OT_S81_VE_LOADSAFE5")
declare -A PACK=([ot_s81sl_vn_c]="--pack y" [ot_s81sl_ve_c]="--pack o_y")
ok=1
for k in ${KITS:-ot_s81sl_vsw_c ot_s81sl_vn_c ot_s81sl_ve_c ot_dsrom_su_hcpost_lane_pr_c}; do
  for v in base mut; do
    O=$W/$k/$v; mkdir -p $O
    S=$(srcs $k | tr '\n' ' ')
    if [ $v = mut ]; then
      python3 - "${MF[$k]}" "${MO[$k]}" "${MN[$k]}" $O/mut.sv <<'PY'
import sys; f, o, n, out = sys.argv[1:]; t = open(f).read(); assert t.count(o) == 1, (f, o); open(out, "w").write(t.replace(o, n))
PY
      S=$(echo " $S " | sed "s| ${MF[$k]} | $O/mut.sv |")
    fi
    python3 -I $G $O ${TOP[$k]} $K/$k/rtl/$(echo ${OLDF[$k]} | sed "s|KITRTL|$K/$k/rtl|")${EXTRA[$k]:-} --new ${NEWF[$k]} --cycles $N ${PACK[$k]:-} > $O/gen.log 2>&1 || { echo "$k $v GEN_FAIL"; cat $O/gen.log; ok=0; continue; }
    $V --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
       ${DEF[$k]:-} --top-module tb_miter -Mdir $O/obj $S $O/old_top.sv $O/tb_miter.sv --build-jobs ${J:-8} \
       -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "$k $v BUILD_FAIL"; tail -8 $O/build.log; ok=0; continue; }
    $O/obj/Vtb_miter > $O/run.log 2>&1
    r=$(grep -h "^MITER " $O/run.log); echo "$k $v: $r"; grep -h "^MITER_ACT" $O/run.log | sed 's/^/    /'
    if [ $v = base ]; then echo "$r" | grep -q "MITER PASS" || ok=0; else echo "$r" | grep -q "MITER FAIL" || ok=0; fi
  done
done
[ $ok = 1 ] && echo "MITERS PASS" || echo "MITERS FAIL"
