#!/usr/bin/env bash
# HBM-CORES-B 11-12 kshare LCREP system lock-step bench: dut cores = LCREP 1 (abcr / pfr defines), reference = the same
# RTL with LCREP 0 (all modules renamed _REF), shadowing each dut core on the same inputs; every output compared EXACT
# (hbm K ports every hbm edge, u_wcmd writes, u_fill writes + hf, stream fills in order).  Usage: run_lock_lcrep.sh CFG [SEED...]
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd); cd "$B"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
cfg=$1; shift; seeds=("${@:-1}")
X=(+define+LK_FSHIFT=0 +define+LK_WSHIFT=0); exp=pass
ABCR=(+define+OT_KSH_SELREP +define+OT_KSH_VMSTG +define+OT_KSH_WCNT2 +define+OT_KSH_SRDL +define+OT_KSH_RCMD)
PFR=(+define+OT_KSH_SELREP +define+OT_KSH_SRDL +define+OT_KSH_PFREE +define+OT_KSH_STSEL +define+OT_KSH_WCNT2 +define+OT_KSH_RCMD)
case $cfg in
 LABCR) D=("${ABCR[@]}" +define+OT_KSH_LCREP);;
 LPFR)  D=("${PFR[@]}" +define+OT_KSH_LCREP);;
 LPFRV) D=("${PFR[@]}" +define+OT_KSH_VMSTG +define+OT_KSH_LCREP);;
 mutL)  D=("${ABCR[@]}" +define+OT_KSH_LCREP +define+OT_KSH_MUT_LCREP); exp=fail;;
 mutLP) D=("${PFR[@]}" +define+OT_KSH_LCREP +define+OT_KSH_MUT_LCREP); exp=fail;;
esac
s=src
python3 -I mkref.py ksh.sv ref_REF.sv > /dev/null
srcs=(tb_lock.sv ref_REF.sv ksh.sv $s/ot_hbm_svc_wb_kport.sv $s/ot_hbm_svc_ring_h9b_ff.sv $s/ot_hbm_svc_wb_cutthrough_cdc.sv $s/ot_hbm_svc_async_fifo.sv
 $s/ot_hbm_svc_native_sector_pipeline_leaves.sv $s/ot_hbm_svc_pc_ctrl_leaf.sv $s/ot_hbm_svc_pc_ctrl_leaf_cfg.sv $s/tb_hbm_svc_command_dram_pipeline_fixture.sv
 $s/ot_hbm_r14_stream_pc_strap.sv $s/ot_hbm_accel_cdc_fifo.sv $s/ot_reset_sync.sv $s/ot_rst_relay.sv $s/ot_sram_1r1w_128x256_m1_r2c2.v)
sha256sum "${srcs[@]}" > src-$cfg.sha256
$vl --binary --timing -j 8 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_ksh_lock --Mdir obj-$cfg -o sim \
  "${D[@]}" "${X[@]}" "+define+LK_CFG=\"$cfg\"" "${srcs[@]}" > build-$cfg.log 2>&1 || { echo "BUILD_FAIL $cfg"; tail -20 build-$cfg.log; exit 2; }
for sd in "${seeds[@]}"; do
 rc=0; obj-$cfg/sim +verilator+seed+$sd +GN=${GN:-480} > run-$cfg-s$sd.log 2>&1 || rc=$?
 ok=0; grep -q '^PASS tb_hbm_svc_wb_kshare_splitstrap_q' run-$cfg-s$sd.log && [ $rc = 0 ] && ok=1
 v=FAIL; [ $ok = 1 ] && v=PASS
 echo "CASE $cfg seed $sd expect $exp got $v rc=$rc :: $(grep -m1 '^LOCK cfg' run-$cfg-s$sd.log) :: $(grep -m1 'offset dut-ref' run-$cfg-s$sd.log) :: $(grep -m1 -E 'WB_INTEGRITY|^LOCK [a-z]' run-$cfg-s$sd.log)"
done
