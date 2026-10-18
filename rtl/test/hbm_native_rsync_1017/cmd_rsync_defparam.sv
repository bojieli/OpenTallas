// HBM-NATIVE 2026-10-17: run the cp1 ingress bench (tb_static_cmd_target, unchanged) with its command targets in the
// hardened cp_svg r2 reset shape (RSYNC=1: 2-flop pin reset synchroniser). The bench times every x-load / DMA command
// against the svg target's free-running `cycle` export, which counts from that target's reset release, so all four
// targets take RSYNC=1 (one common release edge, as for targets sharing one reset relay); with only t_svg at RSYNC=1
// its counter runs 2 counts behind the others and the bench's absolute-cycle checks (not the targets) are off.
// In the die the cp_svg `cycle` output is unconnected and MODE 1 schedules use their own target's counter.
module ot_cmd_rsync_defparam;
defparam tb_static_cmd_target.t_svg.RSYNC = 1;
defparam tb_static_cmd_target.t_xl.RSYNC = 1;
defparam tb_static_cmd_target.t_dma.RSYNC = 1;
defparam tb_static_cmd_target.t_neg.RSYNC = 1;
endmodule
