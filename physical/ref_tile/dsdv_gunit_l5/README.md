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
