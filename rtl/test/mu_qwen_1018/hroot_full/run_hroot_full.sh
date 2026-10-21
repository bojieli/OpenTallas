#!/bin/bash
# KV-MU7 10-20: full multi-user HOST root mechanism bench (tb_mu_hroot_full.sv), Verilator 5.050 (the closure daemon's).
# usage: run_hroot_full.sh ROOT OUT CASE
#   PASS : n32  (PROMPT leaf = the closing native32 netlist qkd_hr_core_prompt_mu4p3_n32 + functional ASAP7 cells)
#          ps3  (PROMPT leaf = its RTL source qkd_hr_core_prompt_mu4_ps3)
#          cells (the 40 combinational functional cell models == the official ASAP7 models, exhaustive, if present)
#   mutants (must FAIL; n32 leaf unless noted):
#     uid0 coordinator POST_UID_SLOT 0 (legacy pos[17:16] POST decode) on the observer's raw-position faces
#     pr1  POST collector keeps release_seen across POSTs        pc1 POST only on the global die drain
#     ts1  token service single-user START position check        ts2 one global peer epoch freshness
#     cd1  coordinator codec holds one terminal at a time        ep3 endpoint terminal release waits for the global drain
#     nx0  POST collector without the next-issue hold (the 10-19 RTL: the scheduler's next issue before POST faults)
#     hm1  (ps3) scheduler attributes a retired step to the last issued slot (not the in-flight FIFO head)
#     cm1  (ps3) package controller retires when ANY die reported (not all 8)
#   KV-PEER12 10-20: PEER tile members (the qkd_hr_core_peer_sram_mu composition, rtl/qwen_sys/host_peer_mu_sram_1020):
#     peer_rr (PASS) = n32 with coordinator -> qkd_host_tp8_coordinator_rr_mu (POST_UID_SLOT 1; _pd codec + MU services),
#             token services -> _rr_mu (pd2 fork), root mux -> _pl_rr, rank codecs -> _rr (the PEER tile's members)
#     mutants on peer_rr (must FAIL): nx0_rr uid0_rr cd1_rr ts1_rr ts2_rr pc1_rr
# The source list is written to OUT/CASE.files (every file Verilator read, from its dependency file).
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
"$V" --version | grep -q 'Verilator 5.050' || { echo "HROOT_FULL $CASE: not Verilator 5.050"; exit 2; }
H=rtl/test/mu_qwen_1018/hroot_full; M=rtl/qwen_sys/mu_qwen_20261018; HC=rtl/qwen_sys/host_cluster_20261017
TB=$H/tb_mu_hroot_full.sv
PC=$M/qkd_host_post_collector_mu.sv; TS=$M/qkd_host_ctrl_token_service_packet_collected_mu.sv
CD=$M/qkd_host_peer_coordinator_codec_mu.sv; EP=$M/qkd_host_native_token_endpoint_cancel_mu.sv
PB=$HC/prompt_safe3/ot_host_if_pb2_observed_ps3.sv; K=rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv
LEAF=n32; SUBS=""; PRR=0
sub(){ SUBS="$SUBS$1"$'\x1f'"$2"$'\x1f'"$3"$'\x1e'; }
NP=rtl/qwen_sys/host_peer_mu_sram_1020; HH=rtl/test/host_peer_main_fixture_1020/historical/rtl/qwen_sys
case "$CASE" in *_rr) PRR=1;; esac
if [ $PRR = 1 ]; then
  sub $TB 'qkd_host_tp8_coordinator_mu #(.MU(1),.POST_UID_SLOT(1)) co(' 'qkd_host_tp8_coordinator_rr_mu #(.POST_UID_SLOT(1)) co('
  sub $TB 'qkd_host_ctrl_token_service_packet_collected_mu #(.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.MU(1))ts(' 'qkd_host_ctrl_token_service_packet_collected_rr_mu #(.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1))ts('
  sub $TB 'qkd_host_peer_root_mux rm(' 'qkd_host_peer_root_mux_pl_rr rm('
  sub $TB 'qkd_host_peer_rank_codec #(.RANK(d))rc(' 'qkd_host_peer_rank_codec_rr #(.RANK(d))rc('
  TS=$NP/qkd_host_ctrl_token_service_packet_collected_pd2_mu.sv; CD=$NP/qkd_host_peer_coordinator_codec_pd_mu.sv
fi
case "$CASE" in
 peer_rr) ;;
 uid0_rr) sub $TB '.POST_UID_SLOT(1)) co(' '.POST_UID_SLOT(0)) co(';;
 nx0_rr) sub $PC 'wire take_next=(MUT!=4)&&' "wire take_next=1'b0&&";;
 pc1_rr) sub $PC '(drains||!alone)' '(drains)';;
 cd1_rr) sub $CD "if(tq_n==3'd4||term_v[terminal_tag[44:43]])fault<=1;" "if(tq_n!=0||term_v[terminal_tag[44:43]])fault<=1;";;
 ts1_rr) sub $TS 'cmd_head[15:13]!=0' 'cmd_head[17:13]!=0';;
 ts2_rr) sub $TS 'h[245:232]>pe_last[h[231:230]]' 'h[245:230]>peer_last_epoch';;
 n32) ;;
 ps3) LEAF=ps3;;
 cells) ;;
 uid0) sub $TB '.POST_UID_SLOT(1)) co(' '.POST_UID_SLOT(0)) co(';;
 pr1) sub $PC "pr<=pr+1'b1;release_seen<=0;" "pr<=pr+1'b1;";;
 pc1) sub $PC '(drains||!alone)' '(drains)';;
 ts1) sub $TS 'cq[cr][15:13]!=0' 'cq[cr][17:13]!=0';;
 ts2) sub $TS 'h[245:232]>pe_last[h[231:230]]' 'h[245:230]>peer_last_epoch';;
 cd1) sub $CD "if(tq_n==3'd4||term_v[terminal_tag[44:43]])fault<=1;" "if(tq_n!=0||term_v[terminal_tag[44:43]])fault<=1;";;
 ep3) sub $EP '(drains||(|c_act))' 'drains';;
 nx0) sub $PC 'wire take_next=(MUT!=4)&&' "wire take_next=1'b0&&";;   # the 10-19 POST collector (no next-issue hold)
 hm1) LEAF=ps3; sub $PB 'wire [SB-1:0] d_slot = (MU_OUT != 0) ? mq_head : eng_slot;' 'wire [SB-1:0] d_slot = (MU_OUT != 0) ? eng_slot : eng_slot;';;
 cm1) LEAF=ps3; sub $K '(fault_any || &m_seen[m_old])' '(fault_any || |m_seen[m_old])';;
 *) echo "HROOT_FULL $CASE: unknown case"; exit 2;;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
# private copy of the source tree the bench reads (substitutions apply to the copy only)
for d in rtl/qwen_sys rtl/lib rtl/physical rtl/test/mu_qwen_1018 physical/asap7_memory_macros $([ $PRR = 1 ] && echo rtl/test/host_peer_main_fixture_1020/historical); do
  mkdir -p "$W/$(dirname $d)"; cp -a "$ROOT/$d" "$W/$d"; done
if [ -n "$SUBS" ]; then
  python3 - "$W" "$SUBS" <<'PY' || { echo "HROOT_FULL $CASE: substitution did not apply"; exit 2; }
import sys
w, subs = sys.argv[1], sys.argv[2]
for rec in subs.split('\x1e'):
    if not rec: continue
    f, a, b = rec.split('\x1f')
    p = w + '/' + f; s = open(p).read()
    assert s.count(a) == 1, (f, a, s.count(a))
    open(p, 'w').write(s.replace(a, b))
PY
fi
# PEER members: the coordinator's MU body sits one level down in the _rr wrapper (co.u_m.g_mu); bench probes follow it
if [ $PRR = 1 ]; then python3 - "$W/$TB" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read(); n = s.count('co.g_mu.'); assert n > 0
open(p, 'w').write(s.replace('co.g_mu.', 'co.u_m.g_mu.')); print('PEER_RR probes', n)
PY
fi
cd "$W"
if [ "$CASE" = cells ]; then
  python3 "$H/gen_cell_check.py" "$H/asap7_func_cells.v" "${ASAP7_CELLS:?ASAP7_CELLS=dir of official asap7sc7p5t_*.v}" cell_check.sv > "$OUT/$CASE.gen.log" 2>&1 \
    || { echo "HROOT_FULL cells: GEN-ERR"; tail -5 "$OUT/$CASE.gen.log"; exit 1; }
  "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_cell_check -Mdir obj -o sim cell_check.sv > "$OUT/$CASE.build" 2>&1 \
    || { echo "HROOT_FULL cells: BUILD-ERR"; grep -E '%Error' "$OUT/$CASE.build" | head; exit 1; }
  ./obj/sim > "$OUT/$CASE.log" 2>&1; rc=$?; echo "HROOT_FULL cells rc=$rc: $(grep -E '^(PASS|FAIL)' "$OUT/$CASE.log" | tail -1)"
  rm -rf obj; [ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"; exit
fi
Y=""; for d in $M $M/host_cluster_mu rtl/qwen_sys/host_integrated_20261014 rtl/qwen_sys/host_20261013 rtl/qwen_sys/redesign_qwen \
  rtl/qwen_sys/static_kv_20261014 rtl/qwen_sys/system_20261008 rtl/qwen_sys rtl/physical rtl/lib \
  $HC/prompt_safe3 $HC/prompt_safe $HC/prompt_rr $HC/prompt_pd \
  physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 \
  physical/asap7_memory_macros/ot_sram_1rw_256x64_m4_r2c2 physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192; do Y="$Y -y $d"; done
[ $PRR = 1 ] && for d in $NP $HH/host_cluster_20261017/peer_rr $HH/host_cluster_20261017/peer_pd $HH/host_integrated_20261014; do Y="$Y -y $d"; done
if [ $LEAF = n32 ]; then LF="rtl/qwen_sys/host_prompt_mu4p3_n32_1020/qkd_hr_core_prompt_mu4p3_n32.sv $H/asap7_func_cells.v"; DEF=""
else LF="$HC/prompt_safe3/qkd_hr_core_prompt_mu4_ps3.v rtl/physical/ot_qwen_host_ctl.sv rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv"; DEF="+define+PROMPT_PS3"; fi
"$V" --binary --timing -O2 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  -Wno-PINMISSING $DEF --top-module tb_mu_hroot_full -Mdir obj -j ${VJ:-8} -o sim $Y +libext+.sv+.v \
  $TB $LF $M/qkd_kv_mu_rowoff.sv > "$OUT/$CASE.build" 2>&1 \
  || { echo "HROOT_FULL $CASE: BUILD-ERR"; grep -E '%Error' "$OUT/$CASE.build" | head -20; exit 1; }
# every source file the build read
sed 's/^[^:]*://' obj/Vtb_mu_hroot_full__ver.d 2>/dev/null | tr ' ' '\n' | grep -E '\.(sv|v|svh|vh)$' | grep -v '^/' | sort -u > "$OUT/$CASE.files"
( cd "$W" && sha256sum $(cat "$OUT/$CASE.files") ) > "$OUT/$CASE.sha256"
./obj/sim ${PA:-} > "$OUT/$CASE.log" 2>&1; rc=$?
r=$(grep -E '^(PASS|FAIL)|^%Error|Fatal|fatal' "$OUT/$CASE.log" | tail -1)
echo "HROOT_FULL $CASE rc=$rc: $r"
rm -rf "$W"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
