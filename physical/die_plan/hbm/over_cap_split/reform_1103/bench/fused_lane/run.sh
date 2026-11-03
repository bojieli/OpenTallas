#!/usr/bin/env bash
# DIE-HBM-61/SPLIT fused_lane bench (fleet host, Verilator 5.050, python3 + numpy).
#   run.sh BUNDLE OUT [STAGES]
# BUNDLE = dir with: kit/ (hnx_fused_lane kit rtl/*.sv, the uncut REFERENCE), sram/ot_sram_1r1w_128x256_m1_r2c2{,_bb}.v
#          (physical/asap7_memory_macros_v2), tools/hdc_golden.py, tools/hdc_golden_v41.py, tools/hbm_next/hnx_fused_vec.py
#          (golden vectors, f6d6de957c / bd3b74e138 lineage, main copies).
# Stages: K   = ot_hnx_fused_top_k (32 kit lanes) + SHADOW kit lane SH 0      -> HNX_FUSED PASS + SHADOW PASS (harness check)
#         S   = ot_hnx_fused_top_s (32 split lanes) + SHADOW kit lane SH 4    -> HNX_FUSED PASS + SHADOW PASS (the proof)
#         S1  = split SMUT 1 (x_v not re-timed by the 4-edge round trip)      -> must FAIL
#         S2  = split SMUT 2 (y_v re-timed 3 instead of 4)                    -> must FAIL
# Cases: HC_PRE_NORM and HC_POST, N = 1, 2, 4, rgap 0 (golden words, every sector once, no fault).
set -u
BU=$(realpath "$1"); O=$(realpath -m "$2"); STAGES=${3:-"K S S1 S2"}; mkdir -p "$O"
H=$(cd "$(dirname "$0")" && pwd); R=$H/../..; RT=$(cd "$H/../../../../../../../rtl/hbm_accel/cores_split/reform_1103/hnx_fused_lane" && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
KR=$BU/kit; LEAF=$(ls $KR/*.sv)
python3 "$H/mk_top.py" "$KR/ot_hnx_fused_eng.sv" "$O/tops.sv" || exit 1
YF="$RT/hnx_fused_lane_split.sv $(ls $KR/*.sv | grep -v 'hnx_fused_lane__') $BU/sram/ot_sram_1r1w_128x256_m1_r2c2_bb.v"
python3 "$H/facewrap_fl.py" --top hnx_fused_lane_c --out "$O/c__fs.sv" --pass-param SMUT $YF > "$O/c_ports.json" || exit 1
python3 "$H/facewrap_fl.py" --top hnx_fused_lane_elp --out "$O/elp__fs.sv" $YF > "$O/elp_ports.json" || exit 1
SRC="$H/tb_fused_split.sv $O/tops.sv $LEAF $RT/hnx_fused_lane_split.sv $RT/hnx_fused_lane__split.sv $O/c__fs.sv $O/elp__fs.sv $BU/sram/ot_sram_1r1w_128x256_m1_r2c2.v"
VF="$H/fused_split.vlt --hierarchical -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb_fused_split"
build(){ # tag defs
  local d=$O/obj_$1; rm -rf $d
  $V --binary --timing -O1 -j 16 $VF $2 -Mdir $d -o V$1 $SRC > $O/build_$1.log 2>&1
  echo "build $1 rc=$? bin=$( [ -x $d/V$1 ] && echo ok || echo MISSING)" | tee -a $O/verdict.txt
}
run(){ # tag op n
  local c=$2_n$3_g0 od=$O/run_$1_$2_n$3; rm -rf $od; mkdir -p $O/cases $od
  [ -f $O/cases/$c/plus.txt ] || python3 -I $BU/tools/hbm_next/hnx_fused_vec.py --op $2 --n $3 --rgap 0 --out $O/cases/$c > $O/cases/$c.gen.log 2>&1
  cp $O/cases/$c/* $od/
  ( cd $od && timeout 3000 ./../obj_$1/V$1 $(cat plus.txt) > run.log 2>&1
    echo "$1 $c: $(grep -h 'HNX_FUSED_CYCLES\|HNX_FUSED PASS\|HNX_FUSED FAIL\|SHADOW PASS\|SHADOW FAIL' run.log | tr '\n' ' ') $(grep -h MISMATCH run.log | head -1)" | tee -a $O/verdict.txt
    rm -f vmi.mem vme.mem )
}
for st in $STAGES; do
  case $st in
    K)  build K  "+define+TOPM=ot_hnx_fused_top_k +define+SHADOW -GSH=0" ;;
    S)  build S  "+define+TOPM=ot_hnx_fused_top_s +define+SPLIT +define+SHADOW -GSH=4 -GSMUT=0" ;;
    S1) build S1 "+define+TOPM=ot_hnx_fused_top_s +define+SPLIT +define+SHADOW -GSH=4 -GSMUT=1" ;;
    S2) build S2 "+define+TOPM=ot_hnx_fused_top_s +define+SPLIT +define+SHADOW -GSH=4 -GSMUT=2" ;;
  esac
done
for st in $STAGES; do for op in pre post; do for n in 1 2 4; do run $st $op $n & done; done; done; wait
sha256sum $SRC $BU/tools/hbm_next/hnx_fused_vec.py $BU/tools/hdc_golden_v41.py > $O/sources.sha256
echo "SUMMARY $(for st in $STAGES; do echo -n "$st: fused_pass=$(grep -c "^$st .*HNX_FUSED PASS" $O/verdict.txt) shadow_pass=$(grep -c "^$st .*SHADOW PASS" $O/verdict.txt)/6  "; done)" | tee -a $O/verdict.txt
