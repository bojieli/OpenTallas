#!/usr/bin/env bash
# Minimum actual gate of the native VM8 service path (producer + root + checker + 4 PIPE1 sinks).
# Usage: run_native_e2e.sh <outdir> [baseline beats.txt]   (on a fleet host; wrap in ot-heavy)
set -uo pipefail
out=$1;BASE=${2:-/srv/opentallas-scratch/codex/xload-vm8-flow-1013/beats.txt}
HASH=1c1d69aa905b131e6dd4c11d0a9c2c87c0ae20ab8e78dadc7dd304c16aac5570
here=$(cd "$(dirname "$0")";pwd);root=$(cd "$here/../../../..";pwd)
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$out";if [[ -e $out/source.sha256 ]];then echo refuse_overwriting_receipt;exit 2;fi
S="rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_wrd.sv rtl/lib/ot_rst_relay.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/proto/ot_fp32_add_rne_pipe.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/hbm_accel_die_views/vm/service13/vm_service_root.sv physical/hbm_accel_die_views/vm/service13/vm_service_wordbank.sv physical/hbm_accel_die_views/vm/service13/vm_service_slice.sv physical/hbm_accel_die_views/vm/checker9/vm_ck4.sv rtl/hbm_accel/generic/adapters/native_b2/ot_hbm_b2_vm8_sm_sink.sv physical/hbm_accel_die_views/vm/service13/tb_vm8_native_e2e.sv"
# the real native SM (E2E_XSM build): sources and production defines of run_xcommit.sh
SM=$(cd "$root";python3 - <<'P'
import os, sys
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
sys.path.insert(0, "tools")
import dshbm_sm_pq_seq as P
print(" ".join([s for s in P.SRC if not s.startswith("rtl/test/")] + P.SMH_SRC + ["rtl/hdc/ot_hdc_cg.sv", "rtl/hbm_accel/cg/ot_cg_tile.sv"]))
P
)
SMDEF="-DE2E_XSM -DOT_SMH -DOT_SMH_CG -DOT_SMH_PRODUCTION_SHAPE -DOT_SMH_FC_HIER -DOT_SMH_CG_ENREG -DOT_SMH_XLK -DOT_FP_DATA_NORST -DOT_SMH_DRST0 -DOT_SMH_RSTRELAY -DOT_SMH_HIER -DOT_SMH_PTW_OHDLY"
S="$S rtl/hbm_accel/generic/adapters/native_b2/ot_hbm_b2_xcommit.sv"
SX=$(for f in $SM $S;do echo $f;done|awk '!seen[$0]++'|tr '\n' ' ')
cd "$root";sha256sum $SX tools/dshbm_sm_pq_seq.py physical/hbm_accel_die_views/vm/service13/run_native_e2e.sh tools/vm8_service/xload_flow_compare.py >"$out/source.sha256"
# name | build define | plusargs | expectation (pass / quar / stale / fail)
runs=(
"rate|xsm|+SEL=0|pass"
"m_xc_short|xsm|+SEL=1|fail"
"m_xc_nodrain|xsm|+SEL=2|fail"
"m_xc_norel|xsm|+SEL=3|fail"
"m_xc_dropcount|xsm|+SEL=4|fail"
"m_x_dropcommit|xsm|+DROP_X=4000|fail"
"rate_nosm|exact||pass"
"ack_skew|exact|+ACK_DELAY=5 +ACK_SKEW=3|pass"
"ack_slow|exact|+ACK_DELAY=40|pass"
"tap_half|exact|+TAP_LFSR=2463534242 +TAP_BITS=1|pass"
"tap_quart_ack|exact|+TAP_LFSR=88172645 +TAP_BITS=2 +ACK_DELAY=17 +ACK_SKEW=2|pass"
"corrected|exact|+INJ_CE=7|pass"
"ue_publication|exact|+INJ_UE=3000 +EXPECT_FAULT=3|quar"
"ue_verify|exact|+INJ_UEV=700 +EXPECT_FAULT=2|quar"
"wrong_write|exact|+INJ_WR=1200 +EXPECT_FAULT=2|quar"
"expected_ue|exact|+INJ_EXP=450 +EXPECT_FAULT=3|quar"
"stale_ticket|exact|+INJ_STALE=100 +ACK_DELAY=5 +EXPECT_FAULT=4|quar"
"stale_owner|exact|+STALE_SINK=3|stale"
"m_sink_data|MUT_SINK_DATA||fail"
"m_sink_ticket|MUT_SINK_TICKET||fail"
"m_sink_earlyack|MUT_SINK_EARLYACK||fail"
"m_xw_credit|MUT_XW_CREDIT|+ACK_DELAY=40|fail"
"m_xw_rdpin|MUT_XW_RDPIN|+ACK_DELAY=40|fail"
"m_earlyrel|MUT_SVC_EARLYREL|+ACK_DELAY=5 +ACK_SKEW=3|fail"
"m_ack3|MUT_SVC_ACK3|+ACK_DELAY=5 +ACK_SKEW=3|fail"
"m_noverify|MUT_SVC_NOVERIFY|+INJ_WR=1200 +EXPECT_FAULT=2|fail"
"m_ck_ignore|MUT_CK_IGNORE|+INJ_UE=3000 +EXPECT_FAULT=3|fail"
"m_serial|MUT_SERVICE_SERIAL||fail"
"m_noquar|MUT_SVC_NOQUAR|+INJ_UE=3000 +EXPECT_FAULT=3|fail"
"m_stale|MUT_SVC_STALE|+INJ_STALE=100 +ACK_DELAY=5 +EXPECT_FAULT=4|fail"
"m_ticket_reuse|MUT_SVC_TICKET_REUSE|+ACK_DELAY=40|fail"
"m_fastorder|MUT_SVC_FASTORDER|+TAP_LFSR=2463534242 +TAP_BITS=1|fail"
)
[[ -n ${ONLY:-} ]]&&{ sel=();for r in "${runs[@]}";do [[ " $ONLY " == *" ${r%%|*} "* ]]&&sel+=("$r");done;runs=("${sel[@]}"); }
builds=$(for r in "${runs[@]}";do IFS='|' read -r _ b _ _ <<<"$r";echo "$b";done|sort -u)
for b in $builds;do
 ( d=;src=$S;[[ $b != exact ]]&&d=-D$b;[[ $b == xsm ]]&&{ d=$SMDEF;src=$SX; }
   /usr/bin/time -v $V --binary --timing -O1 -CFLAGS -O1 -j ${BUILD_J:-4} -Wno-fatal -DOT_MEM_NO_INIT -DVM_SVC_FAULT_HOOK $d --top-module tb_vm8_native_e2e --Mdir "$out/obj_$b" $src >"$out/build_$b.log" 2>&1
   echo $? >"$out/build_$b.rc" ) &
 while (( $(jobs -rp|wc -l) >= ${BUILD_PAR:-5} ));do wait -n;done
done
wait
for r in "${runs[@]}";do
 IFS='|' read -r name b args exp <<<"$r"
 ( mkdir -p "$out/$name";cd "$out/$name"
   if [[ $(cat "$out/build_$b.rc") != 0 ]];then echo build_failed >verdict;exit;fi
   /usr/bin/time -v "$out/obj_$b/Vtb_vm8_native_e2e" $args >run.log 2>&1;rc=$?;echo $rc >run.rc
   crc=-;if [[ -s beats.txt ]];then python3 -I "$root/tools/vm8_service/xload_flow_compare.py" --expect-sha256 $HASH "$BASE" beats.txt >compare.json 2>compare.err;crc=$?;sha256sum beats.txt >beats.sha256;fi
   echo $crc >compare.rc;rm -f beats.txt
   case $exp in
    pass) [[ $rc == 0 && $crc == 0 ]]&&grep -q 'E2E PASS records=9' run.log&&v=ok||v=BAD
          [[ $name == rate && $v == ok ]]&&{ grep -q 'rate_ok=1' run.log||v=RATE_OVER; };;
    quar) [[ $rc == 0 ]]&&grep -q 'E2E QUARANTINE PASS' run.log&&v=ok||v=BAD;;
    stale) [[ $rc == 0 ]]&&grep -q 'E2E STALE_OWNER PASS' run.log&&v=ok||v=BAD;;
    fail) if [[ $rc != 0 || ( $crc != 0 && $crc != - ) ]];then v=ok;else v=BAD;fi;;
   esac
   echo "$v $name exp=$exp rc=$rc compare=$crc :: $(grep -E 'E2E (FAIL|QUARANTINE|STALE_OWNER|SUMMARY)|%Error|%Fatal' run.log|head -1|cut -c1-260)" >verdict ) &
done
wait
rm -rf "$out"/obj_*
fail=0;for r in "${runs[@]}";do n=${r%%|*};cat "$out/$n/verdict";grep -q '^ok ' "$out/$n/verdict"||fail=1;done
echo GATE_FAIL=$fail;date >"$out/DONE";exit $fail
