# hdie_svc_vm_kshare (ot_hbm_svc_vm_kshare_splitstrap #(.KRL1(1)), d4g GEN2e4 r11 x16 vmks_*)

HBM-KSHARE8 10-20. Previous gate (822f50b4d, 10-18) failed CTS on the then-current "glue root exceeds large-root
insertion/spread limits" rule (hbm_clk 23,578 sinks, mean sink wire 613 um); main's clock rule (owner 10-17 0dq /
10-20 08:55) now WARNs on >15k sinks / >300 ps insertion and fails only on pin-flop spread > 80 ps within a region.
Kit regenerated on main (native CTS SDCs current; daemon had REFUSED fe1a7da9c for stale native_cts_sdc).
Fallback in parallel: hdie_svc_vm_kshare_h55 (same RTL, 432 x 237.6 outline).

Safe-design checklist (owner 10-19), census numbers from the 10-18 synthesized netlist (same RTL modulo async_fifo
reset-sync edits):
1 Pins: PASS -- every K pin in a 2-entry pin skid, VM/WB commands and straps land in pin flops, fills/fault leave from
  flops; each reset lands on one async-clear flop per domain (srst_q/hrst_q); kit pin_regs/reset_landing opted out
  (two async domains, see spec reasons).
2 Reach: PASS -- worst reg->reg reach 250.5 um (< 405), 0 reach violations.
3 Fanout: WAIVED (guidance, 10-20 09:35 rule freeze) -- u_fill read pointer rd_bin drives the 8:1 x 279 b read mux
  (max 963 loads, buffered by resize); reset fanout 0 over limit, port fanout 0.
4 Depth: PASS -- worst 508 ps / 13 levels; no combinational in->out; c_k_rdy -> g_rd_out 12 levels from the HBM
  controller ready (flow control allowed at the HBM K boundary), hbm_clk period 1024 ps.
5 Storage: WAIVED -- 8 x 279 b Gray-FIFO per lane (2.2 kb) is the async_gray_fifo CDC store at the HBM boundary
  (audited CDC structure; an SRAM macro cannot carry the two-clock Gray FIFO profile).
6 Floorplan: PASS for pins (<= 5.8 pins/um, all faces), no macros; util 9% (pin-bound tile, waived: outline from
  pin demand, not area).
7 Clock: two regional roots (stream_clk, hbm_clk) joined only by Gray FIFOs + fault_cdc; spread <= 80 checked by --cts
  gate; io_hold_margin 0.03.
8 Schedule: HBM K boundary (off-die-equivalent controller port, elastic per HANDOFF 0az); on-die stream side static.
