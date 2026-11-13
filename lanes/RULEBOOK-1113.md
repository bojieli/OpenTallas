# RULEBOOK 11-13: family design rules set by Fable expert lanes

The owner (11-13 03:4x) asked Fable expert lanes to set the few family-level physical design rules that keep recurring, once, up front. COORD and every lane follow these rules. Each rule has an ID, the rule, why, the implementation (tool and sha), its proof kits, and the dies and types it touches. Only the owning Fable lane edits its own section.

Expert review evidence: ~/coord/lanes/EXPERT-REVIEW-1.md

## R-CLOCK (HOLD-TAP-1): cross-tap insertion balance for zero-logic and low-logic pairs
## R-RTL (HARD-S81-SERDES-1): pipelining depth for paths over budget
Written 2026-11-13 03:29 PST by HARD-S81-SERDES-1. Status: rule text final; the S81 serdes proof build is still running (see lanes/handoff/HARD-S81-SERDES-1.md). Numbers are read from existing reports (TIMING-CLASS-1 census 11-12, serdes__t2 attempt_27 4_cts_final.rpt, CORES-HBM-1 rx_bm3 probe); I ran no new STA sweep over the dies.

**R-RTL-1 stage budget (833 ps, TT).** 833 - 60 uncertainty - clk->Q 60..90 - setup ~25 leaves about 650 ps; keep 50 for skew, so 600 ps for cells plus wire. Measured cost: 29..34 ps per logic cell at light load (hidx 757 ps / 22, svc_vm 794 / 27, serdes am_ok 203 / 6), about 60 ps per cell when a cell drives 80+ loads (hd_host_w 617 / 10), about 0.8 ps per um of repeated wire (serdes u_txl 1267..1674 ps over 1.7..2.2 mm). A stage must fit
`32 ps x logic cells + 0.8 ps x um (pin to pin, Manhattan) + fanout terms <= 600 ps`. As a table:

| launch-to-capture distance | max logic cells (buffers not counted) |
|---|---|
| <= 100 um | 16 |
| <= 250 um | 10 |
| 250..405 um | 3 (mux / enable only: this is a relay hop) |
| > 405 um | 0, and one register row per 405 um (12.1e) |

**R-RTL-2 fanout inside a stage.** A net with more than 64 loads is not one cell: give each group of <= 64 loads its own registered copy of the source (enable, select, reset, valid). The copy is placed with its loads. Never close a wide broadcast with buffers.

**R-RTL-3 macro ports.** After a memory or hard-core output (clk->Q measured 365 ps on the serdes dmem): at most 5 cells and 100 um before the next register; if not, register at the port and read one address earlier (0 cycles) or take +1 cycle. Before a macro input (setup 131..194 ps measured): at most 8 cells and 100 um.

**R-RTL-4 where the check runs.** (a) At synthesis, before any place and route: count non-buffer cells per endpoint on the 1_synth netlist (STA with zero wire). Any endpoint over 16 cells or 520 ps of cell delay is an RTL item; the kit does not go to placement. (b) At placement, split every failing path into logic / repeater / wire. Repeater + wire > logic means the path is a reach or placement item (R-REACH, lane rows), not a depth item; adding logic stages will not fix it and rebuilding will not either.

**R-RTL-5 the fix, in this order.** (1) Restructure the cone: parallel-prefix instead of ripple, balanced tree instead of chain, registered partial products for wide XOR matrices. 0 cycles. (2) Retime an existing register into the cone. 0 cycles. (3) Add a register stage, +1 cycle (owner pre-approved). No settings, retries, ECOs or relaxed constraints in place of these.

**R-RTL-6 latency bookkeeping for every added stage.**
- The stage is a parameter or define, default off; default off must be flop-for-flop the old netlist.
- Data, valid and the reset that defines the frame or calendar move by the same edges. A stage that moves data but not its reset is a bug even when a loopback still passes.
- One lock-step bench per form: new(t + N) == old(t) on every edge outside reset, through cold reset, warm reset and any local reset sequencer. The bench also carries at least one mutant (a row short, or a reset not moved) and one wrong expected N; both must FAIL.
- One row per added cycle in results/<lane>/latency_rows.json: id, lane, parameter, added_cycles, clock, relative_to. The row goes to the die owner and TOK-VERIFY with the READY.
- The plan type carries the parameter (verilog_defines); after the bind, tools/die_plan/lane_asbuilt_latency.py must PASS on the bound plan. Internal stages of a link (serdes, PHY) that the lane table does not count are still reported as rows.
- Registers added for reach are placed by rule (FIRM at their per-bit lane site before global placement), never left to wirelength-driven placement: it puts all rows of a 2-pin chain at one end.

**Types over the rule today** (source in brackets; "unmeasured" means no path report exists, not that the type passes):
- HBM ot_hidx_s3_q: 22 cells 757 ps, TT -203.5, 160 endpoints. R-RTL-1. Fix: prefix adder for the s3 sum, else +1 stage. [TIMING-CLASS-1]
- HBM ot_hbm_svc_vm_kshare_splitstrap__v700685: 27 cells 794 ps, TT -36.2. R-RTL-1. Fix: balanced priority tree or retime sm_s. [TIMING-CLASS-1]
- HBM ot_hbm_svc_vm_kshare_splitstrap__v8e478a: fanout-64 c_k_rdy broadcast, 475 ps of buffers, TT -68.0. R-RTL-2. [TIMING-CLASS-1]
- HBM hnx_fused_lane_c: e_rd -> SRAM wd_in, 134..291 ps single cell + 137..219 ps pin net + SRAM setup, TT -251.9. R-RTL-3. [TIMING-CLASS-1]
- HBM ot_pdie_serdes_rx_bm3_rest (5 instances): 296 endpoints sc_q -> sp (8 XNOR levels behind 100 + 135 ps fanout buffers), 90 in the rate matcher, TT -171.7. R-RTL-1 and R-RTL-2. Fix forms exist (SPCYC, OT_S81_RM_STAGED), in build by CORES-HBM-1. [CORES-HBM-1 11-12 03:47]
- HEAD hd_host_w: 10 cells 617 ps with fanout-84 and fanout-86 enables, TT -76.2. R-RTL-2. [TIMING-CLASS-1]
- HEAD hd_serdes: FAIL 11-12; same KP4 encoder / syndrome RTL as S81, cones unmeasured by me.
- S81 serdes family, 11 types (serdes__t1 x2 cohorts, t2, t3, t4, t12, t13, t14, t15 x2 cohorts, t16; one shared column RTL): R-RTL-1 row 4. serdes__t2 a27: u_txl r[0] -> q 0 logic cells, 1267..1674 ps of repeaters; PMA face -> u_syn 5..6 cells 203 ps, 1570 ps of repeaters; u_rm r_d -> coll_o register and coll_i register -> u_enc are the same class. This is reach, not depth: the fix is lane rows (this lane). The KP4 cones (dsyn sc_q -> sp, enc ch_q -> pp) are the same RTL that fails on HBM rx_bm3; I measure them on the proof build and add them here if they exceed 16.
- S81 seqhost__t1: reg-to-reg up to 1514 um, 3861 pairs over 405 um; no path report kept. R-RTL-1 row 4, unmeasured. [TIMING-CLASS-1 geom row]
- KV kv3_hub_Ei: 1 cell + 6 repeaters 745 ps, TT -159.5. Reach (R-REACH), not depth. Listed so it is not sent to RTL. [TIMING-CLASS-1]
- QC: the census has no QC setup rows; unmeasured against R-RTL-4a.
- HBM q_spb1, vsN1, vsN2 and the 10 S81 slice_station rows are clock-tap or hold items (R-CLOCK), not R-RTL.
## R-STREET (RULES-STREET-1): macro and pin-face streets, congestion escape
## R-REACH (RULES-REACH-1): fanout and reach locality, face-net buffering
## R-CAP (RULES-CAP-1): partition size, cell cap, outline sizing
## R-FLOW (RULES-FLOW-1): ORFS flow settings for slew, DRV and early buffering
