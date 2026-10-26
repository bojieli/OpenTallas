export DESIGN_NICKNAME = issuer_boundary
export DESIGN_NAME = dsfd_stage_seq_static_c8
export PLATFORM = asap7
export VERILOG_FILES = /src/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv /src/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_mailbox.sv /src/rtl/dsrom_sys/s81_static_control/dsfd_stage_seq_static_c.sv /src/rtl/dsrom_sys/s81_static_control/dsfd_stage_seq_static_c8.sv
export VERILOG_DEFINES = -DSYNTHESIS
export SDC_FILE = /work/constraint.sdc
export CORE_UTILIZATION = 50
export CORE_ASPECT_RATIO = 1
export CORE_MARGIN = 2
export PLACE_DENSITY = 0.5
export PLACE_DENSITY_LB_ADDON = 0.05
export SYNTH_REPEATABLE_BUILD = 1
export SYNTH_HIERARCHICAL = 0
export SYNTH_MEMORY_MAX_BITS = 65536
export LEC_CHECK = 0
export TNS_END_PERCENT = 100
export HOLD_SLACK_MARGIN = 0
export SETUP_SLACK_MARGIN = 0
export SKIP_REPORT_METRICS = 0
export REPORT_CLOCK_SKEW = 1
export CORNER = WC
export OT_PIN_REGS = 1
export OT_PIN_REGS_CLOCK = ck,ckv
export OT_PIN_REGS_EXCLUDE = ^ckv$$|^(f_ks|f_pw|t_kd|t_st)(\[.*\])?$$
export OT_PIN_REGS_RESET = ^(rst|rsv)(\[.*\])?$$
export OT_PIN_REGS_RESET_PORTS = rst,rsv
.PHONY: boundary_env
boundary_env:
	@/usr/bin/python3 /srv/opentallas-scratch/claude/s81issuer-make-boundary3/proof/c8/dump_make_env.py
