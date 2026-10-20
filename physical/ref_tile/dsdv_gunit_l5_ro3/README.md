# dsdv_gunit_l5 whole-model successor (S81-GUNIT, 10-19; FANOUT_SAFE 1 + CONTROL_SAFE 1 + Q4 1)

LEAD-S81 approved the whole-model direction (e6269d903): 3,072-bit base table in 12 native SRAM banks, kept-copy
controls for every > 32-load driver, regional reset ownership, Q4 fault/range stage (+40 HC edges, priced to the
compiler: lower_gu.py HC offsets remeasured with run_gu_bench.sh on this source).  Outline 388.8 x 432 (starting
outline, re-sized from measured synthesis); parent-slot change is S81-DIEPLACE's (lanes/MU-DIE-S81.md INBOX).

## SAFE-DESIGN checklist (owner 10-19)
1. Pins: PASS (source) -- every input lands in a flop, every output leaves a flop (pin_regs recipe opted out: source-
   registered); rst_n lands in 2 registered sync stages (ot_rst_region16 sync_q, reset_landing 2), then 16 kept region
   roots, release edge 3 (= old ot_rst_relay).  The mix write enables / scale write enables are kept copies of the
   cw / mx pin landing (small decode in front of the landing flop, same edge as wv / qm_v).
2. Reach: PENDING gate (tile 388.8 x 432; every pin-to-landing-flop and macro-to-band path << 405 um by construction).
3. Fanout: PENDING mapped census (target <= 24 logical loads, admission <= 32).  L5-level copies: ln -> 3 kept copies
   (tail launch | rj_row/lm | rj_sm); CTL row select -> 6 x 6 kept one-hot copies (22 data bits each) + 2 c_on copies
   (21 header bits each); mix writes -> 8 kept {qm_v, qm_i} copies (16-bit half-word enables); job select -> 8 rank-1 +
   25 rank-2 kept copies (12 bank addresses, 12 scale bytes, 1 lifetime check); scale writes -> 16 kept enables (24
   bits each).  Tail / Sinkhorn copies: see the parent's section.
4. Depth: PENDING mapped census / gate (<= 600 ps).
5. Storage: fixed -- base table 3,072 b -> 12 x ot_sram_1r1w2c_32x64_m1 (rows {set, which}, bank b = base words 2b,
   2b + 1; 24,576 physical bits).  Each bank reads continuously at its own kept rank-2 select copy; the macro's read
   register is the old `bases` capture (select a, rank1 a + 1, rank2 a + 2, rd_out a + 3): 0 edges.  Compiler
   contract: the selected {set, which} word is never written between job select and launch, config settles before the
   first read; a write to the selected word within 4 edges before the tail takes the bases is a sticky `fault`
   (same-edge 1R1W ordering never relied on).  Scales 384 b stay flops (< 2 kb).  No runtime-indexed flop array > 2 kb.
6. Floorplan: 388.8 x 432, one full-width std band y 129.6..302.4 (~54% at the 36k um2 model mass); 12 macros on the
   43.2 lattice outside the band at x 43.2/172.8/302.4, y 43.2 (R0, pins S -> S-edge channel 43.2), 86.4 (MX, pins N
   -> band), 345.6 (R0, pins S -> band), 388.8 (MX, pins N -> N-edge channel 25.9); >= 25.9 um channels, halo 5.4.
   Tile pins: S ~1,174 on 388.8 um (~3.0/um), N 552 (1.4/um), E ~132, W clk/rst_n: all <= 6/um.  NOTE: the macro's
   own S-face pin row is 206 pins on 32 um (6.4/um, intrinsic; escape qualified only by the sram_escape64_1019
   coupon, not for 12 banks).  fill_reason.lattice_channel_bound (overall fill 25%) recorded with LEAD-S81 approval.
7. Clock: PENDING --cts gate (one clk root; 12 x 2 macro clock pins wclk = rclk = clk; pin-flop spread <= 80 TT+FF);
   io_hold_margin 0.03.
8. Schedule: static; 0 edges from the SRAM / reset / L5 copies (pins cycle-exact); Q4 +40 HC edges per job (parent).

# dsdv_gunit_l5 safe2 review candidate

The forbidden old MCP gate used a nine-cycle data exception. Safe1 removed that mask and pipelined Sinkhorn, but failed actual TT setup -54.7ps. Safe2 adds a registered alignment/sticky cut before each positive-add sum/round, including step-zero epsilon, with matched bypass timing. D0=17, DS=15, LAT602; HC adds161edges versus safe1 and216 versus old MCP. No ICG/data timing masks are used.

Verilator5.050: Sinkhorn300 mixed cases bit-exact PASS; early-step mutant FAIL63errors40cases. Full GUNIT8cases exact PASS; mutants8/10 FAIL104/73. Actual HOP GU pin-age witness on separate branch codex/s81-gunit-pin-age-1019: candidate975N/973S from common lastHP_N, old759/757 and wrong+1 are negatives; compiler admission remains source-gated and pending native repair.

Safe-design review facts:
1. Registered boundaries/reset: source input/output FFs and two reset-landing stages. Native CTS census is FAIL: worst launch227.2635ps xd_b[9], five outputs exceed220ps; capture96.9404ps vi_n[0], zero captures over190ps, zero combinational pins. This is a material failure, no submit/adoption.
2. Reach: square259.2um; actual gate textbook max31.3um. No hard macros.
3. Fanout: kept108 table-select copies and local T/R/mode copies; no high-fanout gate finding. Exact driver fanout/cap/clock offset of native-failing xe_x/xd_b outputs is under investigation before choosing a fix.
4. Depth/timing: coarse gate WARN, zeroFAIL; TT placement-RC setup+2.8206326ps and hold+33.6654593ps. Logic-depth estimate675.1ps/16levels (tc_q13 to quotient decode w30) remains a warning; no data exception. Separate process-corner sensitivity on the same immutable CTS placement: SS setup-368.0124ps/hold+38.0719ps, FF setup+195.9856ps/hold+29.2094ps. These separate library diagnostics do not replace routed signoff and are not silently conflated with the coarse gate.
5. Storage: delay chains removed. Existing3456bit four-entry base/scale table is static CW configuration, replicated4:1 selection; no new runtime flop array. Existing static-table waiver must remain explicit in owner review, no new waiver inferred here.
6. Geometry: no macros, one contiguous standard-cell area;259.2square. Synth liberty std32414.88294um2 /64963.8144core =49.90%; ODB cell-area estimate29009um2 gives44.65%. Both within owner40–60%. Actual pin geometry1861signal/clock rectangles PASS,0inaccessible/outside/missing. PNGs viewed.
7. Clock/hold: TT/FF pin-flop spread53.1/51.1ps (all-flop55.9/53.1); insertion351.0/294.1ps;19732sinks, guidance only. Route io_hold_margin0.03ns. Native launch FAIL above still blocks adoption. Boundary must match actual parent compensation/landing.
8. Schedule: static, router56 unchanged, reset+2 unchanged; safe2 unit HC964stop/976unit; actual HOP GU boundary uses common lastHP_N to CTL_N975/CTL_S973. All216extraedges versus oldMCP must be reflected in compiler reservations/dependencies/token model after source qualification. No rate/overlap claim.

Trial GRT overflow0, worstM2 utilization49.90%. This is a trial gate, not a routed native qualification. Gate/source binding, exact benches, native library/receipt and SS/FF diagnostics are preserved under results/rtl/s81_safe_fix_1019/gunit_l5/safe2. Critical/repeated-failure tile: no REVIEW or submit before ROOT PNG/checklist/native review and structural repair of the five launch violations.


Safe3 same-edge operand boundary isolation (candidate, not admitted)

The five safe2 native-launch violations share ma_q FFs with arithmetic and
external exp/div outputs. Safe3 PIN_COPY=1 uses two kept fixed-width32-bit
modules capturing the original t[i]/sign operand on the SAME edge. Defaults0
preserve legacy behavior. No added data/reset/calendar edges; HC physical-pin
contract remains north975/south973 from common lastHP_N origin, pending exact
source HOP replay. Compiler759/757 remains unchanged and forbidden for release.
Prebuild sizing and source/cap/fanout census are in safe3/prebuild_model.json
and safe2_path_census.json. 5.050 golden8PASS, mutants8FAIL52/10FAIL37.

SAFE before gate: (1) registered pins/reset2landing retained, independent
output copies added; (2) full259.2square bounds reach below405um; (3) kept
2x32 boundary banks each one dedicated consumer; exact mapped survival audit
required before admission; (4) no new arithmetic/decode depth, existing safe2
textbook675.1ps warning remains disclosed, no threshold relaxation; (5) no new
runtime storage/delay chains; existing static3456bit configuration table waiver
unchanged; (6) no macros, full-width standard rows, same paid259.2square,
prior exact synthesis49.90% plus <=64FF, actual area remeasured by gate;
(7) same centre CTS and 0.03ns hold budgets, native launch/spread must be
remeasured; (8) static calendar unchanged, +0cycles priced. Root review,
native PASS, actual area/copies and final PNG required. No REVIEW or submit.

## SVCGU regen (10-19, branch claude/s81-svcgu-gunit-1019) -- SAFE-DESIGN checklist
Input: gate2 d9ef27598 (CTS, ot-epyc7) FAIL only on fill 28% / band density (outline 388.8 x 432 for 40,172 um2 std +
6,643 um2 macros); TT setup WNS +13 ps, FF hold +35 ps, GRT overflow 0, pin-flop spread TT 63.5 / FF 59.7 ps.
1 Pins: PASS (source-registered faces, reset_landing 2 stages, io_hold_margin 0.03).
2 Reach: PASS by construction (tile 388.8 x 259.2; longest pin->landing / macro->band path << 405 um); gate measures.
3 Fanout: fixed for the dominant family -- native census 2eb2bda2b: 118 of 153 FF roots > 32 were the Sinkhorn quotient
  Q2 shift copies g_shc (<= 72 loads) + 15 g_lt (<= 46): copies doubled (lt 4 -> 8, Q2 shift 6 -> 15 slices + 2 sub),
  kept via ot_skf_kr (* keep_hierarchy *) -- the gate's keep_modules / native census must show 17 g_shc + 8 g_lt
  per quotient. Remaining 20 FF roots (fp32 mul/add keep-stage regs <= 101, 2 reset regions 39/38) and 424 comb roots:
  buffered by repair_design (set_max_fanout 32 in the kit SDC), WAIVED with reason: gate2 closed post-CTS with
  positive setup/hold at GRT 0; shared fp32 mul/add modules are used by many closed tiles.
4 Depth: WAIVED-with-reason: worst stage Sinkhorn u_zq -> u_eps 648 ps at 20 levels (guideline ~600 / ~20 levels),
  post-CTS TT setup positive in gate2.
5 Storage: PASS (3,072-bit base table in 12 native 32x64 SRAM banks; scales 384 b flops < 2 kb).
6 Floorplan: fixed -- outline 388.8 x 259.2 (aspect 1.5) from MEASURED synthesis area, fill ~46 %; S face keeps
  388.8 um for ~1,173 S pins (~3.0/um); 12 macros on the 43.2 lattice (x 43.2/172.8/302.4, y 43.2/86.4/172.8/216);
  the whole core is the std band (band exception removed).
7 Clock: gate2 spread 63.5/59.7 ps PASS; single centre root re-measured by this --cts gate.
8 Schedule: static; 0 edges (Sinkhorn LAT 642, GUNIT hc_lat 1004 unchanged -- bench_svcgu witnesses).

## REFILL-1830/FALLBACK dsdv_gunit_l5_ro3 (10-19 18:4x) -- parallel fallback of dsdv_gunit_l5 (S81.STA.PAR.3)
Why: gate 8623463ca/94214ef94 (ot-epyc8 ref_gate/dsdv_gunit_l5-20261019-163404) reported cts_run FAIL, but that was the
docker client returning rc=1 at 17:09; the ORFS container finished 3_5_place_dp (DPL util 50.3%) and 4_1_cts at 17:45
(hold ws +30 after repair). GPL at 388.8 x 259.2 still showed routing overflow in 7.6% of tiles (1.09M pins). This kit
is the same RTL/params/benches/witnesses with one more 43.2 row pair: outline 388.8 x 302.4, top macro pair y 216 / 259.2.
SAFE-DESIGN checklist (same RTL as dsdv_gunit_l5; only items 6/7 change):
1 Pins: PASS (source-registered pins, reset_landing 2).  2 Reach: PASS by construction (tile 388.8 x 302.4, pins to landing
flops << 405 um).  3 Fanout: as dsdv_gunit_l5 (kept copies; gate checks keep_modules survive).  4 Depth: as dsdv_gunit_l5
(textbook 650 ps / 19 levels Sinkhorn stage WARN disclosed, no data exception).  5 Storage: PASS (12 SRAM banks).
6 Floorplan: 12 macros on the 43.2 lattice (x 43.2/172.8/302.4, y 43.2 R0 / 86.4 MX / 216 R0 / 259.2 MX), full-width std band
y ~103.7..216, N-edge channel 25.9, fill ~41% (synth std 41,144 + macros 6,643 / 117,573), aspect 1.29, S face 1,221 pins on
388.8 um (3.1/um).  7 Clock: centre-fed CTS, pin-flop spread <= 80 checked at gate; io_hold_margin 0.03.  8 Schedule: static, 0 edges.
