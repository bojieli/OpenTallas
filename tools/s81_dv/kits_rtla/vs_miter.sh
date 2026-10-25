#!/bin/bash
# S81-KITS-RTLA 10-24: ot_s81sl_vs old (OLD_REF, default HEAD~0 of the edit = the pre-fix commit) vs fixed (working tree)
# lockstep miter + one mutant (um_q's state copy not updated on an accepted command -> the um_q pin reverts to the stale state on the next hold
# edge; random commands rarely reach QB, the only op on which x_wa / x_wm / x_wd hold -- the slice benches cover those).
#   vs_miter.sh <work dir> <old ref> [cycles]   (cwd = repo root)   prints VS_MITERS PASS when base PASS + mutant FAIL
set -u
W=$(realpath -m ${1:?work}); REF=${2:?old ref}; N=${3:-40000}; mkdir -p $W
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
VS=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vs.sv
S="rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv"
S2=""; for b in ot_dsrom_fp32_add_l6.sv ot_dsrom_su_norm.sv; do S2="$S2 $(git ls-files "rtl/*$b" | grep "/$b$" | grep -v /test/ | head -1)"; done
for f in $S; do [ -f $f ] || { b=$(basename $f); f2=$(git ls-files "rtl/*$b" | grep "/$b$" | grep -v /test/ | head -1); S=$(echo " $S " | sed "s| $f | $f2 |"); }; done
git show $REF:$VS > $W/vs_old_src.sv
ok=1
for v in base mut; do
  O=$W/$v; rm -rf $O; mkdir -p $O; NV=$VS
  if [ $v = mut ]; then
    python3 - $VS $O/mut.sv <<'PY'
import sys; f, out = sys.argv[1:]; t = open(f).read()
o = "um_q_s <= c_imm[12];"; assert t.count(o) == 1
open(out, "w").write(t.replace(o, "um_q_s <= um_q_s;"))
PY
    NV=$O/mut.sv
  fi
  python3 -I tools/s81_dv/kits_rtla/miter_gen.py $O ot_s81sl_vs $W/vs_old_src.sv --new $NV --cycles $N --pack ve_rh --pack ve_ah \
    --oldin "s_d={s_d[157:62],1'b0,s_d[61],1'b0,s_d[60:0]}" > $O/gen.log 2>&1 || { echo "vs $v GEN_FAIL"; cat $O/gen.log; ok=0; continue; }
  $V --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -DSYNTHESIS \
     --top-module tb_miter -Mdir $O/obj $S $S2 $NV $O/old_top.sv $O/tb_miter.sv --build-jobs ${J:-8} \
     -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "vs $v BUILD_FAIL"; grep -m5 %Error $O/build.log; ok=0; continue; }
  $O/obj/Vtb_miter > $O/run.log 2>&1
  r=$(grep -h "^MITER " $O/run.log); echo "vs $v: $r"; grep -h "^MITER_ACT\|^MISMATCH\|DROPPED" $O/run.log | head -60 | sed 's/^/    /'
  if [ $v = base ]; then echo "$r" | grep -q "MITER PASS" || ok=0; else echo "$r" | grep -q "MITER FAIL" || ok=0; fi
done
[ $ok = 1 ] && echo "VS_MITERS PASS" || echo "VS_MITERS FAIL"
