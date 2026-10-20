# hbm_wbk_q2_1020 -- d4g wbk_<q> x4 (ot_hbm_svc_wb_kport_q), HBM-WBK2 structural successor (RELEASE_TREE H.STA.BLK.5)

Why: route hbm_wbk_ql_1019-ql1 was cancelled. Its mapped netlist failed native32 (1,411 drivers > 32, max 1,696) and
synthesis spent 8.5 h on 5.7M CDC pairs: each of the 16 K ports selected from all 32 cross-domain FIFO heads through a
one-cycle storage-dependent 32-way mux, the payload crossed in 288-b x 4 flop FIFOs, and control fanned out to 32 lanes.

Design (ot_hbm_svc_wb_kq2.sv): the VMG7-5 option "dual-clock payload SRAM" is not admissible under reviewed_gray_fifos
(a declared macro must have exactly one Liberty clock pin). Instead copy + lane->PC crossbar stay in the stream family,
and only per-PC output streams cross, each in 9 reviewed ot_link_afifo (<= 32 b, AW 3, RCOPY 4 kept read-pointer copies).
Per lane a registered head-PC one-hot (from base + row*32 + lane, never from storage); per PC a lowest-lane arbiter with a
FIFO credit counter; the grant is registered as a one-hot lane select per (PC, 32-b slice) in kept arrays; AND-OR
crossbar into a relay register xr, then the FIFO. hbm side: 32-b sliced 2-entry K pin skids, outstanding <= 64 and
true-completion ack via meta/ack link FIFOs. Lane l sits in SRAM column l[2:1], so DMA slot s writes only column s/2.


Benches (Verilator 5.050, fleet, source 05a31c4c9; results/rtl/hbm_wbk2_1020/): wbq_e / wbq_w / wbq_e_wopen PASS
(8 blocks, 5,563 sectors, lockstep vs the GEN0 master); 7 mutants rejected with WB_INTEGRITY (quad, span, premature,
ksaddr, slice, commit, credit), committed fail witnesses.
Price (one block at a time, same stimulus, ql1 RTL vs this RTL): 640-sector block fence 137 -> 142 stream edges (+5),
1984-sector block 286 -> 289 (+3); with group traffic the sum of 8 block fences is +0.35%.

## SAFE-DESIGN checklist (owner 10-19)
1. Pins: PASS. Every pin registered in RTL (stream pin flops, kept pin copies for fill_start x8 / wb_fill_bank x6 /
   reserve bank x2; outputs from flops; K ports leave from the sliced skid head; w_k_wr_done pin flops). Each reset lands
   in 2 registered stages on its own clock (kit reset_landing opt-out with reason, as ql1).
2. Reach: by construction the lane -> PC crossbar has a relay register (xr) between the SRAM columns and the PC FIFOs;
   DMA slots feed one SRAM column each. Measured by the gate (clock_span WARN: one root per family over 777 um; regional
   roots stream_fifo_clk[k] carry SRAM column k and PC group k, which share x).
3. Fanout: designed to <= 32 per driver (kept copies: fill FSM x5, fault x5, copy bank x3, per-column copy controls,
   select arrays 32 loads, reset relays <= 16/32). Mapped native32 census: by the gate at PRE_FLOORPLAN (record below).
4. Depth: no storage-dependent select; arbiter is a 32-b lowest-one over registered bits into flops; crossbar is a
   registered-select AND-OR into xr; no combinational in -> out.
5. Storage: payload in 32 SRAM macros. Crossing FIFOs are reviewed flop FIFOs of 8 x 32 b (256 b each, 144 FIFOs):
   WAIVED-with-reason: the reviewed CDC policy admits no dual-clock macro, and each FIFO is < 2 kb with kept read copies.
6. Floorplan: unchanged from ql1 (4 abutted 8-high SRAM columns on the 43.2 lattice, 78 um channels, aspect 1.5:1).
7. Clock: regional roots per family; crossings only through reviewed FIFOs, ot_reset_sync and the 2 declared level
   synchronisers; io_hold_margin 0.03; gate --cts for pin-flop spread <= 80 TT+FF.
8. Schedule: static on the DMA side; K-side ready/credit only at the HBM boundary. Added cycles priced above
   (copy start +2, per sector +3 stream edges in flight; reservation data stored 1 edge later, fills start >= 10 edges later).
