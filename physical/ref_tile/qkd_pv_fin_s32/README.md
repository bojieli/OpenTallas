# qkd_pv_fin_s32 (R14: actual shipping-config native census PASS max32/0 viol; kit regenerated with main tools)

Native census of R6 must pass before generation or gate. The source proof,
mutant witnesses, prior failed native census, and model sizing live in
results/rtl/kv_pvfin_sram_1020. Original module and kit stay unchanged.

Inherited 259.2-square slot; R5 synthesis total34,863um2 including4275um2
SRAM leaves~30,588um2 standard cells /48.6% utilisation of free silicon.
R6 adds bounded control images; its actual area must be checked.
Four macros at43.2um-grid origins, 51.408x39.96um each, 199 pins/39.96um =4.98 signal
pins/um per full SHORT data face (<6). The dense predecessor was9.57/um
and is forbidden in this kit. The new view prices added M4 lead RC/cap. Central full-width band is unobstructed.
All pin faces and timing uncertainties inherit the original interface.
Token age delta0; bounded reset requires2 extra boot edges. Source safety
review and current census numbers must be finalised before any gate.

## R10 status (KV-PARAMS5 10-20, claude/kv-pvfin-s32-1020)
Census history: R5 FAIL 166/117, R6 FAIL 33/1, R7 FAIL 38/1, R8 FAIL 37/2 (command_cal[3] compare -> max/abs muxes 37;
single output take node 34), R9 FAIL 64/3 (lane-invariant operand-select decodes merged onto one node each).
R10 mapped native census (ep5 src_r10, netlist sha 3da5208a...): PASS max 32, 0 violations, 0 role errors, 174,632 roots
(results/rtl/kv_pvfin_sram_1020/r10_native_pass.json.gz). Mapped area 39,374.6 um2 incl. 8,217 um2 SRAM -> 31,158 um2 cells
= 52.8% of the 58,968 um2 free silicon in the inherited 259.2 square. No growth.
R10 V5.050 suite (r10_proof): m0 PASS (40 + 48 stretched commands bit-exact vs qkd_pv_fin_s, NEG1-3 fault), MUT1-5 detected.

Safe-design checklist (R10, pre-gate):
1 Pins: inputs land in the RTL's own pin flops (tap 0 / cal copies / control q); outputs are registers; generic pin regs OFF (no added age).
  Reset: kit 2-stage face landing + two ot_rst_relay_bounded32 farms (leaves <= 32). Boot-only reset release grows (legacy 1 edge);
  token ages unchanged.
2 Reach: 259.2 square, diagonal 366.6 um < 405; routed reach audit after CLOSED.
3 Fanout: PASS mapped census max 32 / 0 violations (kept per-4-lane cal copies, kept out_active copies, kept select/operand copies).
4 Depth: arithmetic cuts unchanged (LAT-7 add, LAT-6 mul); gate measures.
5 Storage: 16 kb runtime-indexed sum bank -> 4 x 32x128 SRAM (p192 view, 4.98 pins/um short face); operand taps are fixed-age.
6 Floorplan: 4 macros at 43.2-lattice origins, full-width central std-cell band, util ~53% (synthesis), square.
7 Clock: single ck root, centre band; spread/insertion measured by --cts gate; io_hold_margin 0.03.
8 Schedule: static; token-age delta 0 (MUL_AGE / output beat ages unchanged); only boot reset release grows.

## R14 status (KV-PARAMS6 10-20, claude/kv-pvfin-r14-1020) -- supersedes the R10 checklist below where they differ
Actual shipping-config census (gate config: OT_KEEP_PIN_REGS, 2 plain reset landing stages, regional farms) history:
R10 FAIL 49/9, R11 FAIL 34/1, R12 FAIL 40/3, R13 FAIL 48/4 (command_accept[2..5] each enabled 24 payload flops:
P0/P1 8 + ADD/SUM date 8 + product date 8). R14 (cfaa9a3cb): the two date groups take their own acceptance nodes built
from same-phase kept start_lane[8..15] images -> 8 flops per node. Census PASS max 32 / 0 violations / 182,258 roots
(r14_proof/native_census.json.gz). Mapped area 41,099.9 um2 incl. 8,217 SRAM -> 32,883 um2 cells = 55.8% of the
58,968 um2 free silicon (std_area_um2 in spec). +0 FF vs R13 (R13 = R10 + 400 FF).
R14 V5.050 shipping suite (run_shipping.sh, r14_proof): m0 PASS (328 commands / 10,496 beats incl. stretch, NEG1-3),
MUT1-5 detected, cold seeds 1/29/53 PASS.
Corrections (Codex 08:14 audit): boot reset release = raw release -> landing E1/E2, farm roots E3, second E4, leaf E5,
first start capture E6 / accept E7: +5 command edges vs legacy E1/E2 (+2 vs unwrapped R10), not +2. Token ages unchanged.
Reach: the 259.2 square's 366.6 um diagonal is not a Manhattan bound; the routed registered-stage reach audit (<=405)
is required after CLOSED.
Checklist R14: 1 Pins PASS (kit landing + pin flops; outputs registered) 2 Reach: post-route audit owed 3 Fanout PASS census
max32 4 Depth unchanged (LAT-7 add, LAT-6 mul) 5 Storage PASS 4x32x128 SRAM 6 Floorplan PASS lattice macros, band, 55.8%,
square 7 Clock single centre root, gate --cts measures spread 8 Schedule static, token delta 0, boot +5 edges (die boot
calendar owner KV-BIND8).

## R15a status (KV-PVFIN15 10-20, claude/kv-pvfin15-1020) -- supersedes R14 where they differ
R14 gate 084503 (ep7) FAILED at CTS: OT_HOLD_STALL NEEDS_RTL after 3 h of hold repair (25,810 hold buffers, +4.6% area,
util 65.6%; 23,931 endpoints inside the 30 ps margin; FF hold -50.3 ps/1345 -> -27.2/78). Worst R2R = zero-logic copies
u_mul.u_c2.q -> s2_shoh/s2_ms/s2_mr/s2_err (launch leaf 262.5 ps vs capture leaf 322.9 ps at FF, adjacent flops).
Classification: copy-hop + clock-structure hold problem, not logic depth: (i) the mul carried 144 mask bits + 24 fl bits
per lane through two flop ranks with no logic between them (c2 -> s2); (ii) default max-cap sink clustering made 1,959
leaves of 3..29 sinks (8 levels), insertion 250..390 ps, report_clock_skew 136-140 ps, ~60 ps between neighbour leaves.
R15a structural fix (both):
 (a) RTL rtl/hdc/ot_hdc_fp32_mul_lat_pvfin.sv: S2a only clamps the subnormal shift amount (6 b per group of 8 indexes, own
     kept s1_power copy) into c2; the round / sticky / one-hot masks are decoded in S2b from the registered amount straight
     into s2_mr / s2_ms / s2_shoh; c2 carries fl46 only, S2b registers fl47 = fl46 + 1, S3a forms fl46 = fl47 - 1.
     Same expressions, same values, same cycle: MUL_LAT 6, token-age delta 0, no schedule change. c2 271 -> 151 bits
     (-1,920 reset flops over 16 lanes). Remaining copy hops are single control bits (v/byp/err/sign), hold-buffer sized.
 (b) clock: balanced register-sink clustering route.cts_sink size 20 / 40 um / 2 levels / buffer every 60 um /
     unbalance 0.5 (measured on dsdv_sh_lk, one root over 25k sinks: pin-flop spread TT 21.7 / FF 21.3 vs 84 default).
R15a proof (V5.050, ep7, r15_proof): shipping m0 PASS (40 + 48 stretched commands bit-exact, NEG1-3), MUT1-5 detected,
cold seeds 1/29/53 PASS; mul unit corner bench vs ot_hdc_fp32_mul_lat (LAT 6) 3 seeds x 11,997 checked, 0 errors.
Parallel fallback R15b (claude/kv-pvfin15b-1020) = R14 RTL + (b) only; bind whichever closes first.
R15a native census (shipping config, ep7 native_a, r15_proof/native_census.json.gz): PASS max 32 / 0 violations /
180,725 roots; mapped area 40,291.1 um2 incl. 8,217 SRAM -> 32,074 um2 cells = 54.4% of the 58,968 um2 free silicon.
Safe-design checklist R15a: 1 Pins PASS (kit landing + RTL pin flops; outputs registered) 2 Reach: 259.2 square,
post-route registered-stage audit owed 3 Fanout PASS census max32/0 4 Depth FIXED: mul stage-2 zero-logic copy hops
removed (masks/fl now have logic on both hops); arithmetic cuts unchanged (LAT-7 add, LAT-6 mul) 5 Storage PASS 4x32x128
SRAM 6 Floorplan PASS (lattice macros, central band, 54.4% synthesis util, square) 7 Clock FIXED: single centre root,
balanced 20-sink / 40 um leaves; spread measured by --cts gate (<=80 within the region); io_hold_margin 0.03
8 Schedule static, token delta 0 (MUL_LAT 6 unchanged), boot +5 command edges (KV-BIND8 die boot calendar).
