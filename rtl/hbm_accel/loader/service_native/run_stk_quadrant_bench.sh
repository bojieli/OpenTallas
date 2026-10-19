#!/usr/bin/env bash
# RTL-BUILD-HBM/stk 2026-10-18: d4g per-quadrant stack services (plan item 10) -- benches, mutants, default regressions.
# Run from the repo root (fleet, via ot-run):  run_stk_quadrant_bench.sh <out> <case>
#   wbq_e | wbq_w | wbq_e_wopen   ot_hbm_svc_wb_kport_q quadrant WB path + lockstep vs ot_hbm_svc_wb_kport (PASS expected)
#   wbq_mut_quad | wbq_mut_span | wbq_mut_premature | wbq_mut_ksaddr     mutants (must FAIL with WB_INTEGRITY)
#   wb_default    GEN0 regressions on the parameterised cutthrough: run_wb_kshare_bench.sh (baseline + 3 mutants) and
#                 run_wb_cutthrough_cdc_bench.sh (PASS expected)
#   sf_q | sf_mut_pair | sf_mut_share   per-quadrant stack fault lockstep vs the NPC 32 master (+ mutants)
#   sf_default    original tb_hbm_svc_stack_fault on the parameterised master: MUT 0 PASS and MUT 1 rejected
#   rc_q | rc_mut1..rc_mut4             NPC 16 refresh producer lockstep vs the NPC 32 master (+ mutants)
#   equiv_default yosys: parameterised stack_fault / cutthrough at default params == the GEN0 copies (results ref/)
set -euo pipefail
out=$(realpath -m "${1:?out}"); c=${2:?case}; mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
command -v "$vl" >/dev/null 2>&1 || vl=verilator
ys=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}
command -v "$ys" >/dev/null 2>&1 || ys=yosys
n=rtl/hbm_accel/loader/service_native
ref=results/rtl/rbh_stk_1018/ref
wbsrc=("$n/tb_hbm_svc_wb_kshare_qh.sv" "$n/ot_hbm_svc_wb_kport_q.sv" "$n/ot_hbm_svc_wb_kport.sv" "$n/ot_hbm_svc_vm_kshare.sv"
 "$n/ot_hbm_svc_wb_cutthrough_cdc.sv" "$n/ot_hbm_svc_async_fifo.sv"
 "$n/ot_hbm_svc_native_sector_pipeline_leaves.sv" "$n/ot_hbm_svc_pc_ctrl_leaf.sv" "$n/ot_hbm_svc_pc_ctrl_leaf_cfg.sv"
 "$n/tb_hbm_svc_command_dram_pipeline_fixture.sv" rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv
 rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
wbq() {   # wbq <label> <expect pass|fail> <verilator -G args...>
 local L=$1 E=$2; shift 2
 sha256sum "${wbsrc[@]}" > "$out/source.sha256"
 "$vl" --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style \
  --top-module tb_hbm_svc_wb_kshare_qh --Mdir "$out/obj-$L" -o sim "$@" "${wbsrc[@]}" > "$out/build-$L.log" 2>&1
 local rc=0; "$out/obj-$L/sim" > "$out/$L.log" 2>&1 || rc=$?
 rm -rf "$out/obj-$L"
 cat "$out/$L.log" | tail -20
 if [[ $E == pass ]]; then test "$rc" = 0 && grep -q '^PASS tb_hbm_svc_wb_kshare_qh' "$out/$L.log" && echo "STK_WBQ PASS $L"
 else test "$rc" != 0 && grep -q 'WB_INTEGRITY\|FAIL tb_hbm_svc_wb_kshare_qh' "$out/$L.log" && echo "STK_WBQ MUTANT_REJECTED $L"; fi
}
ivl() {   # ivl <label> <expect> <top> <files...> (-P params in IVP)
 local L=$1 E=$2 T=$3; shift 3
 iverilog -g2012 -s "$T" ${IVP:-} -o "$out/$L.vvp" "$@" > "$out/build-$L.log" 2>&1
 local rc=0; vvp -n "$out/$L.vvp" > "$out/$L.log" 2>&1 || rc=$?
 if grep -q 'FAIL\|MISMATCH\|fatal' "$out/$L.log" && [[ $rc == 0 ]]; then rc=1; fi
 tail -5 "$out/$L.log"
 if [[ $E == pass ]]; then test "$rc" = 0 && echo "STK_IVL PASS $L"; else test "$rc" != 0 && echo "STK_IVL MUTANT_REJECTED $L"; fi
}
case "$c" in
 wbq_e)             wbq "$c" pass -GQE=1 ;;
 wbq_w)             wbq "$c" pass -GQE=0 ;;
 wbq_e_wopen)       wbq "$c" pass -GQE=1 -GWOPEN=1 ;;
 wbq_mut_quad)      wbq "$c" fail -GQE=1 -GWBMUT=2 ;;
 wbq_mut_span)      wbq "$c" fail -GQE=1 -GWBMUT=3 ;;
 wbq_mut_premature) wbq "$c" fail -GQE=1 -GWBMUT=1 ;;
 wbq_mut_ksaddr)    wbq "$c" fail -GQE=1 -GKSMUT=4 ;;
 wb_default)
  bash "$n/run_wb_kshare_bench.sh" "$out/kshare_q" | tee "$out/wb_default.log"
  test "$(grep -c '^QUALIFIED' "$out/wb_default.log")" = 4
  bash "$n/run_wb_cutthrough_cdc_bench.sh" "$out/cutthrough" | tee -a "$out/wb_default.log"
  grep -q 'WB_PIPELINE_CDC_MUTANT rejected' "$out/wb_default.log"
  echo "STK_WB_DEFAULT PASS" ;;
 sf_q)        ivl "$c" pass tb_hbm_svc_stack_fault_q "$n/tb_hbm_svc_stack_fault_q.sv" "$n/ot_hbm_svc_stack_fault.sv" "$n/ot_hbm_svc_async_fifo.sv" rtl/lib/ot_reset_sync.sv ;;
 sf_mut_pair) IVP="-Ptb_hbm_svc_stack_fault_q.MUT=1" ivl "$c" fail tb_hbm_svc_stack_fault_q "$n/tb_hbm_svc_stack_fault_q.sv" "$n/ot_hbm_svc_stack_fault.sv" "$n/ot_hbm_svc_async_fifo.sv" rtl/lib/ot_reset_sync.sv ;;
 sf_mut_share)
  # mutant applied to the quadrant instances only (module renamed so the references stay the master)
  sed -e 's/^module ot_hbm_svc_stack_fault /module ot_hbm_svc_stack_fault_mut /' -e 's/if(|sh_q)sh<=1;//' "$n/ot_hbm_svc_stack_fault.sv" > "$out/sf_mut.sv"
  grep -q 'if(|sh_q)sh<=1;' "$out/sf_mut.sv" && { echo 'mutant not applied'; exit 1; }
  sed -e 's/ot_hbm_svc_stack_fault #(.MUT(MUT),.OWN_W(6),.NPC(16)/ot_hbm_svc_stack_fault_mut #(.MUT(MUT),.OWN_W(6),.NPC(16)/' "$n/tb_hbm_svc_stack_fault_q.sv" > "$out/tb_sf_mut.sv"
  ivl "$c" fail tb_hbm_svc_stack_fault_q "$out/tb_sf_mut.sv" "$out/sf_mut.sv" "$n/ot_hbm_svc_stack_fault.sv" "$n/ot_hbm_svc_async_fifo.sv" rtl/lib/ot_reset_sync.sv ;;
 sf_default)
  ivl sf_default_m0 pass tb_hbm_svc_stack_fault "$n/tb_hbm_svc_stack_fault.sv" "$n/ot_hbm_svc_stack_fault.sv" "$n/ot_hbm_svc_async_fifo.sv" rtl/lib/ot_reset_sync.sv
  grep -q '^PASS tb_hbm_svc_stack_fault MUT=0' "$out/sf_default_m0.log"
  iverilog -g2012 -s tb_hbm_svc_stack_fault -Ptb_hbm_svc_stack_fault.MUT=1 -o "$out/sf_default_m1.vvp" "$n/tb_hbm_svc_stack_fault.sv" "$n/ot_hbm_svc_stack_fault.sv" "$n/ot_hbm_svc_async_fifo.sv" rtl/lib/ot_reset_sync.sv
  vvp -n "$out/sf_default_m1.vvp" > "$out/sf_default_m1.log" 2>&1 || true
  grep -q '^FAIL tb_hbm_svc_stack_fault MUT=1' "$out/sf_default_m1.log"
  echo "STK_SF_DEFAULT PASS" ;;
 rc_q)          ivl "$c" pass tb_hbm_pc_refresh_cfg_q "$n/tb_hbm_pc_refresh_cfg_q.sv" "$n/ot_hbm_pc_refresh_cfg.sv" rtl/lib/ot_rst_relay.sv ;;
 rc_mut[1-4])   IVP="-Ptb_hbm_pc_refresh_cfg_q.MUT=${c#rc_mut}" ivl "$c" fail tb_hbm_pc_refresh_cfg_q "$n/tb_hbm_pc_refresh_cfg_q.sv" "$n/ot_hbm_pc_refresh_cfg.sv" rtl/lib/ot_rst_relay.sv ;;
 equiv_default)
  for m in stack_fault wb_cutthrough_cdc; do
   sed "s/^module ot_hbm_svc_${m} /module gold_${m} /" "$ref/ot_hbm_svc_${m}.gen0.sv" > "$out/gold_${m}.sv"
   sed "s/^module ot_hbm_svc_${m} /module gate_${m} /" "$n/ot_hbm_svc_${m}.sv" > "$out/gate_${m}.sv"
  done
  cat > "$out/equiv.ys" <<EOF
read_verilog -sv -DSYNTHESIS $out/gold_stack_fault.sv $out/gate_stack_fault.sv
chparam -set OWN_W 6 gold_stack_fault gate_stack_fault
prep; async2sync
equiv_make gold_stack_fault gate_stack_fault eq_sf
hierarchy -top eq_sf
equiv_simple -seq 2; equiv_induct; equiv_status -assert
design -reset
read_verilog -sv -DSYNTHESIS -lib physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
read_verilog -sv -DSYNTHESIS rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/lib/ot_reset_sync.sv $out/gold_wb_cutthrough_cdc.sv $out/gate_wb_cutthrough_cdc.sv
hierarchy -check
proc; flatten gold_wb_cutthrough_cdc gate_wb_cutthrough_cdc; opt_clean; memory -nomap; async2sync; opt -fast
equiv_make -blacklist /dev/null gold_wb_cutthrough_cdc gate_wb_cutthrough_cdc eq_ct
hierarchy -top eq_ct
equiv_simple -seq 2; equiv_induct; equiv_status -assert
EOF
  "$ys" -q -l "$out/equiv.log" "$out/equiv.ys"
  echo "STK_EQUIV_DEFAULT PASS (stack_fault OWN_W 6, wb_cutthrough_cdc STACK 0: parameterised == GEN0)" ;;
 *) echo "unknown case $c"; exit 2 ;;
esac
