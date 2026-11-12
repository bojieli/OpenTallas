#!/usr/bin/env bash
# HBM-CORES-B 11-11 kshare forms A/B/C lock-step bench: dut cores (new RTL + defines) drive the full quadrant system bench
# (tb_hbm_svc_wb_kshare_splitstrap_q: real wb_kport, 32 pc_ctrl_leaf controllers, DRAM fixture); a reference core
# (selrep branch RTL, renamed _REF) shadows each dut core on the same inputs.  Usage: run_lock.sh CFG [SEED...]
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd); cd "$B"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
cfg=$1; shift; seeds=("${@:-1}")
D=(); X=(); exp=pass
case $cfg in
 default) D=(+define+OT_KSH_SELREP); X=(+define+LK_FSHIFT=0 +define+LK_WSHIFT=0);;
 C)  D=(+define+OT_KSH_SELREP +define+OT_KSH_SRDL); X=(+define+LK_FSHIFT=0 +define+LK_WSHIFT=0);;
 A)  D=(+define+OT_KSH_SELREP +define+OT_KSH_SRDL +define+OT_KSH_VMSTG); X=(+define+LK_FSHIFT=1 +define+LK_WSHIFT=0);;
 B)  D=(+define+OT_KSH_SELREP +define+OT_KSH_WCNT2); X=(+define+LK_FSHIFT=0 +define+LK_WSHIFT=1 +define+LK_NO_HBM_EXACT +define+LK_NO_FILL_EXACT);;
 B700) D=(+define+OT_KSH_WCNT2); X=(+define+LK_FSHIFT=0 +define+LK_WSHIFT=1 +define+LK_NO_HBM_EXACT +define+LK_NO_FILL_EXACT);;
 ABC) D=(+define+OT_KSH_SELREP +define+OT_KSH_SRDL +define+OT_KSH_VMSTG +define+OT_KSH_WCNT2); X=(+define+LK_FSHIFT=0 +define+LK_WSHIFT=1 +define+LK_NO_HBM_EXACT +define+LK_NO_FILL_EXACT);;
 mutA) D=(+define+OT_KSH_SELREP +define+OT_KSH_SRDL +define+OT_KSH_VMSTG +define+OT_KSH_MUT_A); X=(+define+LK_FSHIFT=1 +define+LK_WSHIFT=0); exp=fail;;
 mutB) D=(+define+OT_KSH_SELREP +define+OT_KSH_WCNT2 +define+OT_KSH_MUT_B); X=(+define+LK_FSHIFT=0 +define+LK_WSHIFT=1 +define+LK_NO_HBM_EXACT +define+LK_NO_FILL_EXACT); exp=fail;;
 mutC) D=(+define+OT_KSH_SELREP +define+OT_KSH_SRDL +define+OT_KSH_MUT_C); X=(+define+LK_FSHIFT=0 +define+LK_WSHIFT=0); exp=fail;;
esac
s=src
sed -e 's/\bot_hbm_svc_vm_kshare_splitstrap\b/ot_hbm_svc_vm_kshare_splitstrap_REF/g' -e 's/\bot_hbm_svc_pin_skid2_sr\b/ot_hbm_svc_pin_skid2_sr_REF/g' \
    -e 's/\bot_hbm_svc_skid_popg\b/ot_hbm_svc_skid_popg_REF/g' $s/ref_orig.sv > ref_REF.sv
srcs=(tb_lock.sv ref_REF.sv ksh.sv $s/ot_hbm_svc_wb_kport.sv $s/ot_hbm_svc_ring_h9b_ff.sv $s/ot_hbm_svc_wb_cutthrough_cdc.sv $s/ot_hbm_svc_async_fifo.sv
 $s/ot_hbm_svc_native_sector_pipeline_leaves.sv $s/ot_hbm_svc_pc_ctrl_leaf.sv $s/ot_hbm_svc_pc_ctrl_leaf_cfg.sv $s/tb_hbm_svc_command_dram_pipeline_fixture.sv
 $s/ot_hbm_r14_stream_pc_strap.sv $s/ot_hbm_accel_cdc_fifo.sv $s/ot_reset_sync.sv $s/ot_rst_relay.sv $s/ot_sram_1r1w_128x256_m1_r2c2.v)
sha256sum "${srcs[@]}" > src-$cfg.sha256
$vl --binary --timing -j 8 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_ksh_lock --Mdir obj-$cfg -o sim \
  "${D[@]}" "${X[@]}" "+define+LK_CFG=\"$cfg\"" "${srcs[@]}" > build-$cfg.log 2>&1 || { echo "BUILD_FAIL $cfg"; tail -20 build-$cfg.log; exit 2; }
for sd in "${seeds[@]}"; do
 rc=0; obj-$cfg/sim +verilator+seed+$sd > run-$cfg-s$sd.log 2>&1 || rc=$?
 ok=0; grep -q '^PASS tb_hbm_svc_wb_kshare_splitstrap_q' run-$cfg-s$sd.log && [ $rc = 0 ] && ok=1
 v=FAIL; [ $ok = 1 ] && v=PASS
 echo "CASE $cfg seed $sd expect $exp got $v rc=$rc :: $(grep -m1 '^LOCK cfg' run-$cfg-s$sd.log) :: $(grep -m1 'offset dut-ref' run-$cfg-s$sd.log) :: $(grep -m1 -E 'WB_INTEGRITY|^LOCK [a-z]' run-$cfg-s$sd.log)"
done
