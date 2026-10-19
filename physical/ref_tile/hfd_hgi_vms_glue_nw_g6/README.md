# hfd_hgi_vms_glue_nw_g6 (VM hub glue, HBM d4g, H.STA.BLK.7 / H.STA.BLK.16.1) -- g6

Owner LEAD2-HBM/L2H-PGVM 10-19, branch claude/vm-glue-g6-1019. RTL rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_lt.sv
(g6) + hfd_hgi_vms_glue_tiles.sv (gen_vms_glue_tiles.py), kit spec tools/hbm_die_v16/vms_glue_kit_specs.py (GEN _g6).
Lockstep bench tools/hbm_die_v16/run_vms_glue_g6_benches.sh (same 21 cases as g5, Verilator 5.050), witnesses
results/rtl/vm_glue_1018/bench_g6/.

Why g6: the g5 --cts gates ended GATE_STALL (14400 s: routability GPL 1.7-2.4 h, then hold-repair crawl) and the Codex
census ea05ef46a found 971 / 742 / 743 mapped roots > 32 (SW / E / NW). g6 removes them in SOURCE with the same edges.

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | pins + reset landing | as g4/g5: every port is a pin flop + reach relays; rst_n -> one face flop rst_l0 -> reset forest (replicated second landing per leaf group) |
| 2 | reach <= 405 um | as g4/g5 (reach relays DB 3 / DD 4 / DC 3, ring-stop second landing, hub<->stop relays); CHECK at gate (placed census) |
| 3 | fanout <= 32 | FIXED in source: hub cs/ccs 840/575/563 -> qualified one-hot per (dir, client, 24-b slice); re 280 -> per (client, 23-b slice); writes 260 -> folded into rsel; rseq 108 -> one-hot copies; ring hit 256-b broadcast -> registered per 32-b slice; store enable OR trees 266 -> registered per 32-b slice; hs1 37-38 -> 16-b slices; bank selects 33-36 -> 24-b slices; ring-stop lane / rce selects 35-37 -> 24-b slices; cptr 128 -> one-hot ring pointer; replay 36-39 -> 18-b slices; reset leaves 298/204/196/... -> forest <= 24 leaves per group. Ties (1,485 SETN) = ORFS repair_tie_fanout. CHECK: mapped census of the gate synthesis |
| 4 | depth | unchanged or shallower (AND-OR under registered one-hots); g4 r2 depth 383-395 ps |
| 5 | storage | WAIVED with reason: hub slot store = 1,024 b per client (SW 3 clients = 3,072 b), each client store <= ~2 kb, written by up to 10 same-edge sources (8 banks + 2 ring returns) under a static schedule, read by a registered one-hot; a 1R1W/1RW SRAM cannot take 10 same-edge writes without serialising returns in the compiler (owner-level contract change) |
| 6 | floorplan | WAIVED pin-bound (as g4/g5): ~8,900 ring contacts need ~1,484 um at 6/um; 648 x 1555.2, no macros, one std-cell band; partition into hardened sub-tiles = remaining work (lanes/L2H-PGVM.md VMG6) |
| 7 | clock | spine (g4 r2 measured spread 28.6-28.8 ps); io_hold_margin 0.03; recipe 4 die hold budget |
| 8 | schedule | static; g6 adds NO edge (all copies on the edge of the register they replace); reset assertion +2 / release +5 unchanged |

## g5 notes (base)
## g5 (LEAD-HBM/LH-PGVM2 10-19) -- structural fixes of the g4 r2 --cts gates (ot-epyc7 ...-20261019-065847, in GRT repair)
Branch claude/vm-glue-g5-1019, kit spec tools/hbm_die_v16/vms_glue_kit_specs.py (GEN _g5). g4 r2 findings (SS repair log):
NW -225..-349 ps reg->reg into u_core.u_hub.rsp_grp[1].d_q (hit decode broadcast over 256 data bits per slot from the hub
landing br); E -93..-184 at u_core.u_hub.req_grp[1].bank[4].sl[3].sel (select decode from hub registers straight into
the per-slice copies beside the face); SW -653 at output b3_pq[4] whose relay chain was MERGED with b3_pq[1]
(bk_pq_s1[859].D = bk_pq_s0[856]: 33 ports not single-flop); ~30k port hold violations -169..-203 ps stuck at the
+10 % repair cap with recipe-2 pin hold pads (IO reference QDM SS-mode min arrival 519.9 vs max 1257.9 ps).
- hub response stage 1: per face group, the group's source data / write flags and the hit decode as a REGISTERED ONE-HOT
  per (source, client-slot, 32-b slice), kept copies (32 loads each); stage 2 = AND-OR of local registers. Bank returns
  +1 edge (contract pr_e).
- hub-side registered bank select sel_h (one per bank and client, decoded where qr / be / bc / qvalid live), copied per
  slice one edge later; request copies qr_g1 -> qr_g. pq +1 edge (contract pq_e).
- every tile relay chain bit is a kept register (one chain per port bit; no merged relays).
- kit recipe 4 + hold_budget die (owner-approved FLOW-HOLD 10-16 die boundary hold budget; no pin hold pads), io_hold_margin 0.03.
- benches bench_g5 (Verilator 5.050, ot-epyc7): SW / NW / SE / NE PASS 37520 / 33768 / 33768 / 33768; rmut / land / sid /
  g3 / g4 / g5 (new: select copies without the hub-side register) all FAIL.
- latency vs g4 (handed to H-D4G / LH-REPRICE3 input note): pq out +1, bank returns pr -> cr +1 (client round trip +2);
  everything else unchanged.
- checklist deltas vs the g4 table below: 3 FIXED (+ hit one-hot copies, sel_h fanout 8), 4 FIXED (decode and AND-OR now in
  separate stages), 7 boundary hold = die budget (recipe 4), 8 latency handed over. Items 2 / 5 / 6 as g4.

## SAFE-DESIGN checklist (owner 10-19; g4 table, g5 deltas above)
| # | item | result |
|---|---|---|
| 1 | pin regs + reset landing | PASS: every port is a pin flop (RTL: tile reach chains, ring-stop stage A); reset lands in the RTL at the face (rst_n -> rst_l0 -> rst_l1, plain) -> ot_rst_relay 2 sync + 1 tree, 11 regional copies (hub, CW/CCW header band, CW/CCW lower/upper lane-band halves, replay+status, hub E/N/S face groups) |
| 2 | reach <= 405 um per cycle | FIXED (structural): bank-side ports = pin flop + 2 relays (xq_done/xq2_done + 3), hub client ports (cq, cr, schedule controls, status outputs, sid strap) = pin flop + 2 relays, hub island <-> ring-stop header band 1 relay each way (pi, ri, cco, rce, faults), ring stop header band -> lane bands through one relay copy per ring-face half, band valid bits through one relay per band, rce = 3-level tree. Planned hop <= ~390 um on the 648 x 1555 outline; re-checked by a placed reach census after the gate |
| 3 | fanout <= ~32 per critical register | FIXED: kept copies per slice -- ring-stop band selects (8 x 35-b slices), rce valid gate (8 x 36-b), hub bank selects (8 x 36-b slices), hub response slot select (one-hot of response_seq per client, slot, 32-b; was rseq 1,088 loads in the first g4 synthesis), replay selects (8 x 36-b), hub slot clears (per client, slot, 32-b). Gate check: Yosys must keep them (paramod names) |
| 4 | depth / no runtime arbitration | FIXED: every select is a REGISTERED ONE-HOT decoded a stage ahead from the static schedule (hub bank_enable/bank_client qualified with valid/local/bank, ring tx_enable/tx_source with the bank match folded in, replay_source); data stages are AND-OR. Two clients on one bank or an unscheduled flit is a status fault, never an arbitration. Measured at the gate (TT setup) |
| 5 | storage | FIXED: commit mask/source delay line (COMMIT_DELAY 13) is a ring buffer. WAIVED: hub slot accumulators (N x 4 x 256 b; SW 3 kb, E/NW 1 kb) take up to 10 OR-writes + 1 clear per edge, and their slot index is the compiler's static seq, so they are accumulators, not an indexed array an SRAM can hold. Reach relays are spatial wires, not delay storage |
| 6 | floorplan | WAIVED, pin-bound: 648 x 1555.2 (2.4:1, about 6 % util). The ring face carries 8,950 lane bits, which need >= 1,492 um at 6 pins/um, and the die slot is fixed by H-D4G. Widening to 2:1 only lengthens the E-W bank hops. No macros: the whole core is one std-cell band |
| 7 | clock | spine, centre-fed beside the ring-stop register mass (g3 measured spread 28.9 ps at CTS); gate rule: pin-flop spread <= 80 ps TT + FF; io_hold_margin 0.03 |
| 8 | static schedule | PASS: no credits or backpressure. Latency deltas vs g3 were handed to H-D4G / TW5-HBM-DIE (lanes/H-D4G.md, HBM-SAFE-VMGLUE entry) |

## Latency contract vs g3 (compiler / calendar)
- Bank-side ports: pq out +2, pr in +2, eg in +2, xq/xq2 out +2, xq_done/xq2_done in +3 (COMMIT_DELAY 8 -> 13: WACK +5), bank_status +2.
- Hub client ports +3 each way: cq, cr, client_seq, response_enable/seq, bank_enable/client, hub_ring_*, replay_*, sid strap, hub_status/vmstat/mirror_busy/ring_fault outputs. Schedule controls stay aligned with cq.
- Ring: stop inputs +1 (ring transit +1 per hub). Hub->ring injection pi +2, replay return ri +2, cco -> hub +2, rce -> replay +3, eject xq +3 (stop +1, tile +2), mirror egress eg +3. tx_enable/source keep their offset relative to the flit.
- Client round trip cq -> pq -> pr -> cr: +10 vs g3. Reset: assertion +2 edges, release +5 edges after the port (landing 2 + relay 3; g3 release +3).
