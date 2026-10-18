#!/bin/bash
# HBM-NATIVE 2026-10-17: lockstep benches old (raw rst_n pin) vs new (2-flop pin reset synchroniser), one case per call.
#   usage: run_rsync_lockstep.sh OUT CASE [MUT]
#   CASE: col_sfu | col_idx (collar XSER=0, MUT 8 = mid-run reset misses the core) | cmd (cp_svg, MUT 1 = RSMUT) |
#         aq13 (x-load quantiser fmt wrapper, MUT 1 = RSMUT) |
#         cmd_ingress (the cp1 real-ingress bench tb_static_cmd_target with t_svg at RSYNC=1; MUT = its own -DMUT)
# Prints the bench's own line ("... RSYNC_LOCKSTEP PASS|FAIL"); exit 0 on PASS.
set -u
cd "$(dirname "$0")/../../.."
O=${1:?out}; c=${2:?case}; m=${3:-0}; mkdir -p "$O"
D=rtl/hbm_accel/host_static_20261015; T=rtl/test/hbm_native_rsync_1017; P=rtl/hbm_accel/generic/peers; A=physical/hbm_xp_aq_tree13_1014
case "$c" in
 col_sfu) a="-Ptb_rsync_collar.CASE=0 -Ptb_rsync_collar.MUT=$m $T/tb_rsync_collar.sv $D/ot_hbm_static_cfg_collar.sv $D/ref_ot_hbm_static_cfg_collar_r1.sv";;
 col_idx) a="-Ptb_rsync_collar.CASE=1 -Ptb_rsync_collar.MUT=$m $T/tb_rsync_collar.sv $D/ot_hbm_static_cfg_collar.sv $D/ref_ot_hbm_static_cfg_collar_r1.sv";;
 cmd)     a="-Ptb_rsync_cmd.RSMUT=$m $T/tb_rsync_cmd.sv $D/ot_static_cmd_target.sv $D/ref_ot_static_cmd_target_r1.sv";;
 aq13)    a="-Ptb_rsync_aq13.RSMUT=$m -Ptb_rsync_aq13.NCYC=20000 $T/tb_rsync_aq13.sv $P/ot_hbm_xp_aq_tree13_fmt.sv $P/ref_ot_hbm_xp_aq_tree13_fmt_f1.sv $A/ot_hbm_xp_aq_tree13.sv $A/ot_hbm_xp_aq_scale13.sv rtl/hdc/ot_hdc_delay.sv";;
 cmd_ingress) a="-DMUT=$m -DTGTPIN=1 $T/cmd_rsync_defparam.sv $D/tb_static_cmd_target.sv $D/ot_static_cmd_target.sv $D/ot_hbm_host_static_ingress.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv";;
 *) echo "RSYNC_ONE $c: unknown case"; exit 2;;
esac
iverilog -g2012 $a -o "$O/$c.vvp" > "$O/$c.build" 2>&1 || { echo "RSYNC_ONE $c: BUILD-ERR"; cat "$O/$c.build"; exit 1; }
# fleet iverilog 12 prints '$finish called ...' after the result line: keep only the bench's own lines
r=$(vvp -n "$O/$c.vvp" | grep -v 'finish called' | tee "$O/$c.log" | grep -E 'RSYNC_LOCKSTEP (PASS|FAIL)|TB_STATIC_CMD_TARGET (PASS|FAIL)' | tail -1)
echo "$r"
case "$r" in *" PASS"*) exit 0;; *) exit 1;; esac
