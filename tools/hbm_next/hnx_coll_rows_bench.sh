#!/bin/bash
# HBM-NEXT-UNITS-COLL 2026-10-19: N-row COLL endpoint train (ROW_GATHER / ARGMAX_MERGE) on the UNCHANGED die-bound
# native V4 COLL quadrants (q3 SW host_v4 + q2 host_v4; ctl_v5 / issuer_v6 / hard_v8 parents are cycle-locked to them by
# tb_hgi_coll_q_hard_v5). Fork of rtl/hbm_accel/generic/collective/p2p/run_q_static_host_v4_rows_bench.sh with
#  - the hnx bench rtl/hbm_next/coll/tb/tb_hnx_coll_rows.sv (ARGMAX lane-count verdict fixed),
#  - N = 1, 2, 3, 4, 6 for both ops (cycles(N) scan) and the mutants at N = 4,
#  - the q3 TKM as a KMAX-64 copy (as run_q_hard_v5_bench.sh: ROW_GATHER / ARGMAX never start the TKM; the ctl faults
#    on p_tkm_start in ARG mode), so the build is small.
# Run from a bundle root (git archive of the lane branch):  tools/hbm_next/hnx_coll_rows_bench.sh OUT [R] [W]
#   CASES="P1 P4 ..." selects cases. Verilator 5.050 (fleet).
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); R=${2:-623}; W=${3:-453}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null) R=$R W=$W"
p=rtl/hbm_accel/generic/collective/p2p; t=rtl/hbm_accel/generic/collective/tkm
sed 's/parameter integer KMAX=2048/parameter integer KMAX=64/' "$t/ot_hgi_coll_tkm_static.sv" > "$O/ot_hgi_coll_tkm_static_k64.sv"
grep -q 'parameter integer KMAX=64' "$O/ot_hgi_coll_tkm_static_k64.sv" || { V "KMAX64 copy failed"; exit 2; }
src=(rtl/hbm_next/coll/tb/tb_hnx_coll_rows.sv "$p/ot_hfd_coll_q3_static_host_v4.sv" "$p/ot_hfd_coll_q2_static_host_v4.sv"
 "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hfd_coll_q_static_v4.sv" "$p/ot_hgi_coll_static_issuer.sv"
 "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_reduce_static.sv"
 "$p/ot_hgi_coll_pring_captured_static.sv" "$p/ot_hgi_coll_pring_static_state_capture.sv" rtl/hdc/ot_hdc_fp32_mul_lat.sv
 "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv"
 "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv"
 "$p/ot_hgi_coll_argmax_static.sv" rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv
 "$O/ot_hgi_coll_tkm_static_k64.sv" "$t/ot_hgi_coll_tkm.sv" "$t/ot_hgi_coll_tkm_buffer.sv" rtl/lib/ot_rst_relay.sv
 rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
sha256sum "${src[@]}" "$t/ot_hgi_coll_tkm_static.sv" "$p/static_uop_layout_v4.json" tools/hbm_next/hnx_coll_rows_bench.sh \
 tools/hbm_coll_static/row_gather_rows.py tools/hbm_coll_static/argmax_rows.py > "$O/sources.sha256"
FL=(--binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -GNE=2 --top-module tb_hnx_coll_rows)
verilator "${FL[@]}" -j "${JOBS:-16}" --Mdir "$O/obj" "${src[@]}" > "$O/build.log" 2>&1 || { sleep 5;   # PCH race: retry once
 verilator "${FL[@]}" -j 4 --Mdir "$O/obj" "${src[@]}" > "$O/build.log" 2>&1; }
[ -x "$O/obj/Vtb_hnx_coll_rows" ] || { V "BUILD_FAILED"; tail -40 "$O/build.log"; exit 2; }
V "build ok"
one(){ # case
 local case=$1 kind P mut op tag g nq3 nq2
 kind=${case:0:1};P=${case%%_*};P=${P#?};mut=${case#?$P};mut=${mut#_}
 if [[ $kind == P ]];then op=0;tag=ROWGATHER_ROWS
  g=(python3 tools/hbm_coll_static/row_gather_rows.py "$O/$case/prog" --P "$P" --R "$R" --wire "$W")
 else op=1;tag=ARGMAX_ROWS
  g=(python3 tools/hbm_coll_static/argmax_rows.py "$O/$case/prog" --P "$P")
 fi
 [[ -n "$mut" ]] && g+=(--mutant "$mut")
 "${g[@]}" > "$O/$case.compile.log" 2>&1 || { V "$case: COMPILE_FAILED $(tail -1 $O/$case.compile.log)"; return; }
 nq3=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['parents']['d0q0']['rows'])" "$O/$case/prog/manifest.json")
 nq2=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['parents']['d0q1']['rows'])" "$O/$case/prog/manifest.json")
 "$O/obj/Vtb_hnx_coll_rows" +DIR="$O/$case/prog" +P="$P" +R="$R" +W="$W" +NRQ3="$nq3" +NRQ2="$nq2" +OP="$op" > "$O/$case.log" 2>&1
 echo "RUN_RC=$?" >> "$O/$case.log"
 local m; m=$(grep -E "^(ROWGATHER_ROWS|ARGMAX_ROWS)_MEASURE" "$O/$case.log" | head -1)
 if [[ -z "$mut" ]];then
  if grep -Eq "^ *$tag PASS" "$O/$case.log";then V "$case: PASS rows=$nq3/$nq2 | $m";else V "$case: FAIL (expected PASS) | $m";fi
 else
  if grep -Eq "^ *$tag FAIL" "$O/$case.log";then V "$case: mutant FAIL (rejected, expected) | $m";else V "$case: MUTANT SURVIVED | $m";fi
 fi
}
for c in ${CASES:-P1 P2 P3 P4 P6 A1 A2 A3 A4 A6 P4_row_stride P4_link_step A4_vm_step};do one $c & done
wait
grep -h "_MEASURE" "$O"/*.log > "$O/cycles_N.txt"
rm -rf "$O/obj"
V "done"
