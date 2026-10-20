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
