#!/bin/bash
# A2-F / hop-1 VM parent gate (S-VM-RTL 2026-10-16).  Usage: a2f_parent_gate.sh SRCDIR OUTDIR
# SRCDIR is a pinned FLAT source snapshot (git show <rev>:<path> of every file in FILES_* below).  Run on an admitted
# ot-run host.  Verilator only (two 128-SRAM VMs per differential binary).
#   diff_h1_w1  s1 s2 s3   tb_dsfd_vm_a2f_diff  A2-F hop-1 core vs legacy core WSCATTER_PIPE 1 (profile s81_vm_r4_c2_w1)
#   diff_h1_w0  s1         ... vs legacy WSCATTER_PIPE 0 (profile s81_vm_r4_c2_w0)
#   diff_h0_w1  s1         A2-F hop-2 core vs legacy w1 (isolates the A2 deltas)
#   mut_lane / mut_commit / mut_rel   DUT mutants on diff_h1_w1: wrong lane, dropped commit, missing hop-1 edge: must FAIL
#   par_a2f     tb_dsfd_sp_vm_a2f (S-FUNC master program) on dsfd_sp_vm_a2f READ_PIPE 4 CAP_PIPE 2 HOP1 1: seeds 1 2,
#               fault witnesses 1..8; mutants capword / wfcpair / x43phase must FAIL
#   par_legacy  tb_dsfd_sp_vm_static on the legacy dsfd_sp_vm (same snapshot, READ_PIPE 4 CAP_PIPE 2 WSCATTER_PIPE 1): seeds 1 2
set -uo pipefail
S=${1:?source}; O=${2:?output}; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
NMIX=${NMIX:-2400}
COMMON="dsfd_vm_static_fsr_bank8.sv dsfd_vm_static_fsr_quartets.sv dsfd_vm_static_read_leaf.sv dsfd_vm_static_read_quartets.sv dsfd_vm_static_read_valid.sv dsfd_vm_static_read_valid_quartets.sv dsfd_vm_static_read_router.sv dsfd_vm_static_read_quartets_p.sv dsfd_vm_static_read_valid_quartets_p.sv dsfd_vm_static_read_router_p.sv dsfd_vm_static_suhc_fsr.sv dsfd_vm_static_suhc_return_map.sv dsfd_vm_static_scatter_b8_out.sv dsfd_vm_static_bank128.sv dsfd_vm_static_relay128.sv dsfd_vm_static_relay128_b8.sv dsfd_vm_static_relay128_b4.sv dsfd_vm_static_return.sv dsfd_vm_static_return32_native_lanes.sv dsfd_vm_static_return_bank8_profiles.sv dsfd_vm_static_return_bank8.sv ot_sram_1r1w_512x128_m4_r2c2.v dsfd_vm_static_rsched.sv dsfd_vm_static_landing.sv dsfd_vm_static_landing_lane.sv dsfd_vm_static_landing_fault_join.sv dsfd_vm_static_landing_joined.sv dsfd_vm_seq_static.sv dsfd_vm_seq_tile.sv ot_s81_vm_x34.sv ot_s81_vm_x43.sv ot_s81_vm_fault_transports.sv dsfd_vm_static_capl_pipe.sv dsfd_vm_static_capl_pre.sv dsfd_vm_static_capl.sv dsfd_vm_static_cap_leaf.sv dsfd_vm_static_cap.sv dsfd_vm_capture_fault_serial.sv dsfd_vm_native_valid_diag.sv dsfd_vm_static_wfc.sv dsfd_vm_static_xio.sv dsfd_vm_xio_request.sv dsfd_vm_xio_return.sv dsfd_vm_xio_serial.sv dsfd_vm_xio_fault_join.sv"
LEGACY="dsfd_vm_static_write_capture128.sv dsfd_vm_static_scatter_lane.sv dsfd_vm_static_scatter.sv dsfd_vm_static_slice128_suhc.sv dsfd_vm_static512_suhc.sv dsfd_vm_static_wdispatch128.sv dsfd_vm_static_wstage128.sv dsfd_vm_static_w0.sv dsfd_vm_static_wcontrol.sv dsfd_vm_static_wsched.sv dsfd_vm_static_core.sv"
A2F="area_a2_controlled.sv area_a2f.sv area_a2f_field4.sv area_a2f_control_resetlocal.sv area_a2f_split4m_composed.sv area_a2f_payload33_composed.sv dsfd_vm_a2f_payload33.sv dsfd_vm_a2f_rsched.sv dsfd_vm_a2f_mem.sv dsfd_vm_a2f_core.sv"
NATIVE="+define+OT_VM_NATIVE_READ +define+OT_VM_NATIVE_READ_L16 +define+OT_VM_NATIVE_CAP +define+OT_VM_NATIVE_CAP_PINREG"
build() {  # name top files defines...
  local name=$1 top=$2 files=$3; shift 3
  local F=(); for f in $files; do F+=("$S/$f"); done
  "$V" --binary --timing -O1 -Wno-fatal -j 8 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" --top-module "$top" \
    --Mdir "$O/obj_$name" -o tb "$@" "${F[@]}" > "$O/build_$name.log" 2>&1 || { echo "BUILD FAIL $name"; tail -20 "$O/build_$name.log"; return 2; }
  echo "BUILT $name"
}
DIFF="$COMMON $LEGACY $A2F tb_dsfd_vm_a2f_diff.sv"
PAR="$COMMON $A2F dsfd_sp_vm_a2f.sv tb_dsfd_sp_vm_a2f.sv"
PLEG="$COMMON $LEGACY dsfd_sp_vm_static.sv tb_dsfd_sp_vm_static.sv"
# A full differential Verilator frontend measured 3.76 GB. Eleven overlapping frontends/compiler pools
# exceeded a 32 GB cgroup; bound the build working set without dropping any configuration or mutant.
MAX_BUILDS=${MAX_BUILDS:-3}
[[ "$MAX_BUILDS" =~ ^[1-9][0-9]*$ ]] || { echo 'MAX_BUILDS must be positive' >&2; exit 2; }
pids=(); bfail=0
flush_builds() {
  local p
  for p in "${pids[@]}"; do wait "$p" || bfail=1; done
  pids=()
}
queue_build() {
  build "$@" & pids+=($!)
  if [ "${#pids[@]}" -ge "$MAX_BUILDS" ]; then flush_builds; fi
}
queue_build diff_h1_w1 tb_dsfd_vm_a2f_diff "$DIFF" +define+A2F_HOP1=1 +define+A2F_REF_WSP=1
queue_build diff_h1_w0 tb_dsfd_vm_a2f_diff "$DIFF" +define+A2F_HOP1=1 +define+A2F_REF_WSP=0
queue_build diff_h0_w1 tb_dsfd_vm_a2f_diff "$DIFF" +define+A2F_HOP1=0 +define+A2F_REF_WSP=1
queue_build mut_lane   tb_dsfd_vm_a2f_diff "$DIFF" +define+A2F_HOP1=1 +define+A2F_REF_WSP=1 +define+DSFD_VM_A2F_MUT_LANE
queue_build mut_commit tb_dsfd_vm_a2f_diff "$DIFF" +define+A2F_HOP1=1 +define+A2F_REF_WSP=1 +define+DSFD_VM_A2F_MUT_COMMIT
queue_build mut_rel    tb_dsfd_vm_a2f_diff "$DIFF" +define+A2F_HOP1=1 +define+A2F_REF_WSP=1 +define+DSFD_VM_A2F_MUT_HOP1_REL
queue_build par_a2f      tb_dsfd_sp_vm_a2f "$PAR" $NATIVE
queue_build par_capword  tb_dsfd_sp_vm_a2f "$PAR" $NATIVE +define+OT_VM_CAPL_MUT_WORD
queue_build par_wfcpair  tb_dsfd_sp_vm_a2f "$PAR" $NATIVE +define+OT_VM_WFC_MUT_PAIR
queue_build par_x43phase tb_dsfd_sp_vm_a2f "$PAR" $NATIVE +define+OT_VM_X43_MUT_PHASE
queue_build par_legacy tb_dsfd_sp_vm_static "$PLEG" $NATIVE +define+OT_VM_NATIVE_WSCATTER
flush_builds
[ $bfail = 0 ] || { echo 'A2F_GATE FAIL (build)'; exit 2; }
# ---- runs (all in parallel)
declare -A RUN
run() { local key=$1 bin=$2; shift 2; "$O/obj_$bin/tb" "$@" > "$O/$key.log" 2>&1 & RUN[$key]=$!; }
for s in 1 2 3; do run diff_h1_w1_s$s diff_h1_w1 +seed=$s +nmix=$NMIX; done
run diff_h1_w0_s1 diff_h1_w0 +seed=1 +nmix=$NMIX
run diff_h0_w1_s1 diff_h0_w1 +seed=1 +nmix=$NMIX
for m in lane commit rel; do run mut_$m mut_$m +seed=1 +nmix=600; done
for s in 1 2; do run par_a2f_s$s par_a2f +mode=0 +seed=$s; run par_legacy_s$s par_legacy +mode=0 +seed=$s; done
for m in 1 2 3 4 5 6 7 8; do run par_a2f_m$m par_a2f +mode=$m; done
for m in capword wfcpair x43phase; do run par_$m par_$m +mode=0 +seed=1; done
for k in "${!RUN[@]}"; do wait "${RUN[$k]}"; done
bad=0
chk() { if grep -q "$2" "$O/$1.log"; then echo "PASS $1"; else echo "FAIL $1"; tail -8 "$O/$1.log"; bad=1; fi; }
for s in 1 2 3; do chk diff_h1_w1_s$s '^TB_A2F_DIFF PASS$'; done
chk diff_h1_w0_s1 '^TB_A2F_DIFF PASS$'
chk diff_h0_w1_s1 '^TB_A2F_DIFF PASS$'
for m in lane commit rel; do chk mut_$m '^TB_A2F_DIFF FAIL$'; done
for s in 1 2; do chk par_a2f_s$s '^TB_SPVM PASS mode 0$'; chk par_legacy_s$s '^TB_SPVM PASS mode 0$'; done
for m in 1 2 3 4 5 6 7 8; do chk par_a2f_m$m "^TB_SPVM PASS mode $m "; done
for m in capword wfcpair x43phase; do chk par_$m '^TB_SPVM FAIL mode 0$'; done
grep -h '^TB_A2F_DIFF LAT\|^TB_A2F_DIFF RESULT\|^TB_SPVM RESULT' "$O"/*.log | sort | uniq -c
[ $bad = 0 ] && echo 'A2F_GATE PASS' || echo 'A2F_GATE FAIL'
exit $bad
