# hbfd_pad_r17x115 (LEAD2-HBM/L2H-PAD, 10-19)

HBM d4g exact-N pad ring, worst ring shape of the pad inventory (W=17 b, N=115 edges), `hbfd_pad SAFE_STORAGE=1`.
Successor of codex `0c3eecf04`/`366dc27e7` (functional PASS, structural FAIL: the 8 `ingress_local` copies were an
unpacked array that Yosys aliased to one FF per bit, 17 Q x 115 loads; a9a97c79b audit).

Structure: `i -> face0 -> face1 -> 8 kept hbfd_pad_icopy (17 b each, one per 16 rows) -> 113-row finite ring
(one row written per edge) -> registered capture -> o`. Core = exact 113-edge store; +2 face stages = 115 edges.
Reset: `rs -> rs_s1 -> kept hbfd_pad_rst_land copies` (2 registered stages, async assert, release 2 edges later);
the 2 release edges are paid by face0/face1, so the external contract is unchanged (exact N, II1, async zero reset).

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | Pins registered; reset landing 2 stages | PASS: i -> face0 (1 load/bit), o <- capture flops; rs -> rs_s1 (only sink) -> 4 kept stage-2 copies. Flow pin_regs / reset_landing opted out with reason (RTL does both; a flow stage would add edges the exact-N contract forbids). |
| 2 | Reach <= 405 um / cycle | PASS: 54.0 x 54.0 um outline (util 0.52 of synth 1,273 um2), worst corner-corner Manhattan 108 um. |
| 3 | Fanout <= 32 per register, kept copies | PASS (Yosys 0.68 generic, synth -flatten, all Q audited: `results/rtl/hbfd_pad_storage_1019/l2h_pad/audit.json`): 17x115 max Q loads 16, 8 icopy + 4 rst_land instances kept (keep_hierarchy on the definitions, survives $paramod). Same audit over 1x3, 1x115, 17x4, 34x73, 274x3, 274x14, 136x28: over32 = 0 everywhere. |
| 4 | Depth <= ~600 ps / ~20 levels | PASS (gate2 54x54: post-CTS setup WNS +154 ps, hold +46 ps; gate1 textbook depth 346.7 ps): read path = 7-bit lookahead subtract + 113:1 x 17 mux (~7 mux levels) into capture; write = shared 7-bit row decode. No arbitration, no comb in->out. |
| 5 | Storage | 1,921 bits (113 x 17) < 2 kb: finite circular flop array, one row written per edge (no shift chain, no bulk reset); shapes > 2,048 b use real ot_sram_1r1w_128x256_m1_r2c2 macros (unchanged codex rule). |
| 6 | Floorplan | No macros. Outline 54x54 from synthesis std area 1,273 um2 at util 0.52 (gate2 PASS, uniform density PNG, GRT overflow 0), aspect 1:1, full std-cell band, pins W (ck, rs, i) / E (o). |
| 7 | Clock | Single leaf TritonCTS root, 2,127 sinks; gate2 measured insertion TT 112.9 / FF 90.2 ps, pin-flop spread TT 7.3 / FF 6.8 ps; io_hold_margin 0.03, hold_margin 0.03. |
| 8 | Schedule | Static: no enable/valid/ready, every edge advances; 0 added external edges (N stays 115), reset release constant unchanged (internal +2 paid by face stages). |

Evidence: fleet Verilator 5.050 72-shape x 7000-edge golden bench PASS, ASSERT_MUTANT 1..4 witnesses (all shapes:
`w_mutant<m>.log`; kit shape 17x115: `w_kit_mut<m>.log`), `results/rtl/hbfd_pad_storage_1019/l2h_pad/`.
