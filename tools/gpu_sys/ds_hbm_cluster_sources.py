"""Explicit source-only closure; no inference/prepare/build side effects."""
from pathlib import Path
import os
ROOT=Path(__file__).resolve().parents[2]
VERILATOR=Path(os.environ.get("OPENTALLAS_TOOL_ROOT",Path.home()/".local/opentallas-tools"))/"verilator-5.050/bin/verilator"
BASE=['rtl/gpu_sys/ot_gpu_bd_line.sv', 'rtl/gpu_sys/ot_gpu_cdc_fifo.sv', 'rtl/gpu_sys/ot_gpu_cmdproc.sv', 'rtl/gpu_sys/ot_gpu_coll_endpoint.sv', 'rtl/gpu_sys/ot_gpu_coll_fabric.sv', 'rtl/gpu_sys/ot_gpu_coll_mux.sv', 'rtl/gpu_sys/ot_gpu_hbm_partition.sv', 'rtl/gpu_sys/ot_gpu_hbm_system.sv', 'rtl/gpu_sys/ot_gpu_host_bridge.sv', 'rtl/gpu_sys/ot_gpu_l2_slice.sv', 'rtl/gpu_sys/ot_gpu_memsys.sv', 'rtl/gpu_sys/ot_gpu_mreq_cdc.sv', 'rtl/gpu_sys/ot_gpu_reset_ctrl.sv', 'rtl/gpu_sys/ot_gpu_simt_divlane.sv', 'rtl/gpu_sys/ot_gpu_simt_lane.sv', 'rtl/gpu_sys/ot_gpu_simt_sm.sv', 'rtl/gpu_sys/ot_gpu_sys_glue.sv', 'rtl/gpu_sys/ot_gpu_xbar.sv']
PRIMITIVES=['rtl/gpu/ot_gpu_sm.sv', 'rtl/gpu/ot_gpu_bulk_copy.sv', 'rtl/gpu/ot_gpu_fadd.sv', 'rtl/gpu/ot_gpu_barrier_node.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv', 'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/gpu/ot_gpu_tree.sv', 'rtl/gpu/ot_gpu_issue.sv', 'rtl/gpu/ot_gpu_stack.sv', 'rtl/gpu/ot_gpu_tc_col.sv', 'rtl/hdc/ot_hdc_fpu.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv', 'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_sfu.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_prefix.sv', 'rtl/abi3/ot_a3_fp32_div_rne_pipe.sv', 'rtl/abi3/ot_a3_fp32_sqrt_rne.sv', 'rtl/gpu/ot_gpu_sm_bd.sv', 'rtl/gpu/ot_gpu_bd_col.sv', 'rtl/hdc/v41/ot_hdc_blockdot.sv', 'rtl/v41rom/ot_v41_bterm.sv', 'rtl/v41rom/ot_v41_bterm2.sv', 'rtl/link/ot_link_afifo.sv', 'rtl/link/ot_link_nvls_switch.sv', 'rtl/hdc/kv/ot_hdc_hbm_model.sv', 'rtl/host/ot_host_if.sv', 'rtl/experimental/w2_nc6_completion_20261003/ot_hdc_qwen_pc_exact_completion.sv']

def sources20():
    return BASE+PRIMITIVES+[
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_simt_sm20.sv',
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cluster20.sv',
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_source_entry20.sv',
        'rtl/test/gpu_sys/tb_ds_hbm_cluster20.sv']
