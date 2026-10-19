# qfd_tt_ctlm_dv_safe3 — QW-CTLM3 (LEAD2-QW 10-19) successor of safe2/safe2n

Primary: safe2 geometry with the complete core/hr cone partition (lp_cone_regions.tcl).
RTL = branch claude/qw-ctlm3-1019 (lp regenerated with origin/main lp.py + the QW-CTLM3 fixes); gate tools = origin/main b31708013.

What changed vs safe2/safe2n:
1. **Reset-release bug fixed in RTL** (lp.py `landing_reset_lead`): every ring/read rq now releases at the regional reset
   epoch RB (= the edge a t = 0 child leaves reset); before, it released one edge later, so the word a source presented on
   its first post-reset edge was lost (MUT0 ss5 cycle-19 token / dc 12 mismatches). Same reset stage count (RB-2 + 1 + rq).
   Lockstep MUT0 PASS with the UNCHANGED flat reference (reset depth 3) and a SMALLER warm window (33 vs 36); MUT5
   (old release) FAILS with exactly the old dc signature -> committed witness.
2. **Rings D2 / K = E = 1** (were D4/K2): ring storage 952 b x 2 = 1,904 b (< 2 kb rule; largest logical bank 374 b), every
   landing +2 edges instead of +3. Record compiler offsets: hr outputs +4, tl +2, inputs pw/kok/kwd/native_ret +4, others +0.
3. **No data multicycle** (lp.py `landing_mcp: false`, clock_entry_constraints `no_data_multicycle`): no
   set_multicycle_path anywhere; ring -> read cones (slot data, valid, selectors, reset-adjacent) are single-cycle full-STA
   paths with the 60+150 / 25+150 ps cross-root reserves. Conservative (actual read age = K edges).
4. **native_ret[94:0] N -> E face** (M4, 0.384 pitch, y151.884-187.980) beside u_hr's native_ret pins (E face x734.4,
   y144.7-163): the 48 textbook wire_reach FAILs of safe2n (port -> u_hr comb 518 um) go to ~60 um.
5. Audit: main lp.py had lost the port_regions unlanded-crossing check (the unland mutant PASSED the audit); restored.

## Safe-design checklist (owner 10-19)
| # | Item | Result |
|---|------|--------|
| 1 | Pins registered, reset landed 2 stages | PASS (inherited PINREG / OT_KEEP_PIN_REGS=1; lp regional reset runs rst_n -> root -> 2 per region -> per-child pads). |
| 2 | Reach <= 405 um per cycle | fixed: native_ret recut (518 -> ~60 um). Ring -> read crossings span the region distance (~410 um centre-centre) as one single-cycle STA path; the gate's placed lint decides. |
| 3 | Fanout <= 32, kept copies | inherited lp_reset_copies + same_edge_reset_copies (max 32) and kept CALPIPE selectors; gate re-lints (safe2n lint: u_lprc_u_gi 4,219 loads pre-copy). |
| 4 | Depth <= ~600 ps | WARN (open, not refusing): u_cal tcount -> fire_q ~745 ps estimated (20 levels); timing decides. |
| 5 | Storage > 2 kb in SRAM | PASS: CALPIPE per-user FIFOs / programme store are SRAM rings (4 + 2 x 64x512). Landing rings now 1,904 b total (D2), no flop delay line >= 3 deep. A crossing ring cannot be an SRAM: the library has only single-clock 1R1W/2RW macros. |
| 6 | Floorplan | inherited: macros on the 43.2 lattice, aspect 1.8, fill 46%; E face now native_cmd 5.2/um + native_ret 2.6/um. 64x512 SRAM abstract W/E ~10.2 contacts/um is a macro property (Codex: waiver not accepted) -> route DRC decides. |
| 7 | Clock | two regional roots, landed crossings, io_hold margin 30 ps. OPEN from safe2n: ck_hr pin-flop spread 176/166 ps (h16c child ref 303 ps vs pin flops ~800 ps: TritonCTS gives the hard child pin an early arrival) -> gate measures. |
| 8 | Schedule | static; every landing +2 (was +3): offsets in results/arch/landed_parent_1018/qfd_tt_ctlm_dv_lpf/qfd_tt_ctlm_dv_lpf_lp_record.json "compiler" -> GEN must re-bind (lanes/QW-GEN2.md). |

Gate: pre_route_gate --remote auto --cts (main tools). Not critical (not in critical_tiles.txt).
