# QC-FIX-2: BTAB F2 routed gate, F3/F3b tree re-plans, capture-drift census (2026-10-29)

Lane QC-FIX-2 (successor of QC-FIX-1, `results/qc_fix_1_1029`). Runs live on intel1
`/srv/opentallas-scratch2/claude/qc-fix-2-1029` (kits/, f3/, f3a/, f3b/, f3r/, probe/). The F2 kit is still in
`qc-fix-1-1029/kits/qfd_dv_s8x_btab_f2`.

## 1. F2 routed result: NOT SIGNED (CHECKED, `f2_signoff_summary.json`)
ot-run oth-ubuntu-4041114 ended 06:46 with rc 2 from `do-gds-merged` only: the SRAM LEF has no GDS cell, and
GOAL=finish merges GDS while the turntree run used GOAL=route, which does not. Route, fill, RCX, 6_final and STA were
done before that step. `signoff.py` was then run by itself with the same command as `run_kit.sh`
(signoff/ written 07:0x).

| gate (GEOM-54/55 PASS-COND) | F2 routed | turntree | verdict |
|---|---|---|---|
| insertion TT (230-270), STA RCX pin-flop mean | 285.82 (all regs 283.55) | - | FAIL (plan 270.49, +15.33) |
| insertion FF (182.5-222.5) | 227.85 (all 226.44) | - | FAIL (plan 212.19, +15.66) |
| related-pair skew <= 80 | TT 65.63 / FF 60.77 | 84.4 | PASS |
| FF hold >= 0, measured frame | -1.68 / 1 EP | -27.50 / 1060 | FAIL |
| DRV | TT slew 88 / FF 45, cap 0 | slew 31, cap 3 | FAIL |
| DRC | 1 (M4 short inside g_btb[1] E pin edge x 253.5-254.6 y 21.4) | 6 | FAIL |
| setup TT | +305.76 | | PASS |
The spice_cell clock number was not run because the STA insertion is already out of band.

* Hold: write landing `u_twpd/q[1023]` sits on leaf Tpqrs (CLK 195.9). It drives `g_btb[3].u_m/wd_in[255]`, and that
  SRAM's clock arrives on Tqqsp at 223.3 (+27.4). So the landing and its SRAM are on different subtrees.
* Slew (CHECKED on 3_place, 4_cts, 5_1_grt and 6_final with `slewnets.tcl`): F2 anchors the write landings (case b) at
  the SRAM pin faces. That leaves single-sink tw_data nets of up to about 175 um from the S IO band, driven by BUFx3
  (place4020 (203,6) -> (264,120)). The post-GRT `repair_design` did not fix them.

## 2. Two tree re-plan variants (no pad)
Both use `core_family_slice.py run --replan-cal` (12.3 calibrated re-plan for a core built HIGH). The offset is the F2
routed result: TT +15.33, FF +15.66 (`*_replan_cal.json`). Both legalize through `finish_form.py`, which now passes
`--ndr 2,2` when the chosen wire class is ndr2w.

| form | anchors | census placement | plan (PLAN MODEL, UNCHECKED) | placement check |
|---|---|---|---|---|
| F3b | read + write (as F2) | F2 own 3_place | 2,2,4,4 ndr2w, 9 st, 409 cells, pred built TT 262.97 / FF 204.69, w 4.9 / 6.9 | leaf->sink max 30.2 um (1 leaf >30), btcap max 29.8; AUTO-GEOM as F2 class; render VIEWED |
| F3 | read only (`OT_MPF_CASES=a`) | F3a (F2 tree + read-only anchors) | 2,2,4,4 ndr2w, 8 st, 291 cells, pred TT 249.07 / FF 193.71, w 8.6 / 14.8 | drift: 6 leaves >30 um, max 67.2 -> GEOM FAIL (own check) |
| F3r | F3 + `post_place_rebind exact_count` | F3a | same as F3 | CTS run to measure the rebind |

The new opt-in `OT_MPF_CASES` in `physical/common_flow/macro_pin_flops.tcl` is a shared tool change: default `ab`
leaves behaviour unchanged, `a` anchors read captures only. It needs ROOT-MERGE review.
F3 moves the core clock pin to (157.164, 36.732). F2 and F3b move it to (158.22, 61.02). In both cases the parent tap
move is a plan event for DIE-QC-30.

## 3. Capture-drift census of QC hard cores with macros (`macro_capture_geo.tcl`, read-only, 3_place)
A capture is a macro output pin that reaches one flop D through at most 4 single-fanout INV/BUF/HB cells, as in case (a)
of `macro_pin_flops.tcl`.

| core (kit) | captures | median / p90 / max um | >30 um | signature |
|---|---|---|---|---|
| btab turntree (unanchored) | 1024 | 30.3 / 157.4 / 166.5 | 517 | YES |
| btab F2 / F3a / F3b / F3 | 1024 | about 10 / 11.4 / 12-17 | 0 | fixed |
| vmr f4k2 (signed) | 512 | 7.5 / 9.4 / 12.7 | 0 | no |
| prog l2h3 | 914 | 10.1 / 11.4 / 13.4 | 0 | no |
| crh_rp1 f4g (signed) | 512 | 7.4 / 8.1 / 9.1 | 0 | no |
| native59 rstB | 4096 | 7.1 / 8.9 / 10.2 | 0 | no |
| romleaf a0k7s (signed) | 256 | 7.2 / 11.3 / 25.8 | 0 | no |
| rawleaf a0k7s (signed) | 0 | - | - | n/a |
| NL a0c native / NK a0c k12 | 512 / 1024 | 101 / 444 median | 379 / 1024 | NOT this class: the "macro" is a hard child (rawleaf / node) and the flop is the tile's registered t_out face port (intended, GEOM44/46). macro_pin_flops case (a) would pull face flops off the face, so do NOT apply it. |

Result: no other current QC core shows the BTAB capture-drift signature, so F2 or F3 is not applied anywhere else.
