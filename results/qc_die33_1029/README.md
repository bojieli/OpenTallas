# DIE-QC-33 (QC die owner) — 2026-10-29

## PROG native-interface candidate 2 review (before any build)
Candidate intel2:/srv/opentallas-scratch2/claude/codex-qc-prog-native-0858/native_pin_reach.odb
(sha 6a2f8b49..., Codex unit 3676935; 354 existing FFs moved, max 98.766 um; no RTL/pin/outline/cycle/macro/clock-cell change).
Source = archived s8b 5_2_route.odb copy (source.odb, sha 9fe17a8c...).
Checks (own run of main tools/autopilot geom_dump.tcl + geom_rules.py --all-kits --outline-self, max layer M5; UNCHECKED-independent):

| rule | source | candidate 2 |
|---|---|---|
| r2r max (<=405) | 446.36 FAIL | 404.51 ok (margin 0.49 um) |
| r2r count >405 | 89 FAIL | 0 ok |
| pin_reg p90 / max | 32.74 FAIL / 42.47 | 25.93 ok / 35.46 ok |
| relay_collapse, cells_on_macros, comb_loops | 0 | 0 |
| clock_reach | 499.35 FAIL | 499.35 FAIL (unchanged, E-side sinks x~253 vs S entry x 35.3) |
| channel_h / channel_v / col_v | 0.777 / 1.643 / 1.643 FAIL | unchanged FAIL |
| partial_face, fill/empty (absolute all-kits) | FAIL | unchanged FAIL |
| pin_density | WARN 10.5/um | unchanged WARN |

check_placement on candidate: clean (prog/check_placement.log). Renders viewed: prog/source_auto_geom.png, prog/native_pin_reach_auto_geom.png
(south input FFs pulled into the two S pin bands x 5-65 / 195-230; worst r2r now the E-column path ~(205,37)->(230,112)).
Owner verdict: the candidate fixes the reach/pin-distance failure it targeted, with no new failure. It is NOT ready for P&R:
(1) independent GEOM review (12.17); (2) the existing protected-instance PG hook (216 terms) must be applied to this candidate;
(3) moved clock sinks need real leaf routing (old SPEF invalid); (4) unchanged clock_reach 499.35 and channel/col_v FAILs
are old-native interface issues that the route must show as GRT0 (the 47 h DRT failure of the wide form is not this vehicle).
r2r margin 0.49 um: no ECO; treated as PASS by the existing rule.

## A0 native selected-source proof (NL)
intel2 codex-qc-proof-0831/native_nl (Codex build unit 2507986, REGROOT=3 ICG=2, no FP1, mapped rawfault_m3, real ROM masks).
Controls run by DIE-QC-33 (ot-run unit oth-ubuntu-4047962, exit 0), a0_proof/nl_controls.tsv:
mut0 PASS (12000 checks, 0 qualified errors, 55% gated), mut7 (unsafe main-clock hop) CAUGHT (4164 errors),
mut8 SURVIVED, mut3 SURVIVED (conservative controls; the open proof gaps COORD named before any ICG=2 sign-off).
Note n_valid=0 in every NL run: the bench never drives the n path, so mutants 8/3 are not exercised on NL. NK build still live.

## BTAB F3b routed (QC-014)
intel1 qc-fix-2-1029/kits/qfd_dv_s8x_btab_f3b, unit 1217062 exit 0, btab/f3b_signoff.json: NOT SIGNED.
TT setup +306.07, FF hold +7.22 (F2 was -1.68: fixed), pair skew TT/FF 33.9/35.3 (limit 80), DRC 5 (4 M4 Short at SRAM
g_btb[1].u_m x~253.4 y 25-29 and g_btb[3].u_m x~160 y 95.2, 1 VDD/net4045 M4 spacing), DRV slew TT 46 / FF 24 (u_twpd tw-data class,
F2 was 88/45), PIN_AUDIT extra 5 = ck + ft_* ports absent from plan pins. F3r still routing (DRT iter ~44, 14 violations at 09:3x).

## A0 native selected-source proof (NK) — controls by DIE-QC-33 (unit oth-ubuntu-186213, exit 0)
mut0 PASS (0/12000 qualified errors, n_valid 63), mut7 CAUGHT (4165), mut3 CAUGHT (5342: t_out 4487 + n_y 856), mut8 SURVIVED.
So on the actual selected source: mutant 3 is closed on NK (its n path is driven) but open on NL (n_valid 0); mutant 8
(ROM-only) survives on both -> the bench needs a ROM-first-read stimulus before mut8 can be called caught. No PASS claim beyond these.

## BTAB F3b DRC diagnosis (own odb probe, CHECKED against 6_final.odb)
All 4 M4 shorts sit inside the SRAM macro edge strip: g_btb[1].u_m bbox x 159.84-254.664 -> shorts x 253.38-254.59 (east edge,
y 25-29, nets of place4047/_5463_, u_twpd q[272] D); g_btb[3].u_m -> short x 159.91-161.03 (west edge, y 95.2, wire10840->_4335_).
Std-cell signal M4 wires clip the ~1.3 um M4 edge strip of the macro (the macro-edge halo/keep-off does not cover M4 at the
E/W edges). Structural fix = macro-edge M4 routing blockage/halo in the kit macro placement (existing kit mechanism), not an ECO.
