# S81-LP-3 (2026-10-29): LP lane kits, centre-clock variants, east lane, parent LP estimate

Successor of S81-LP-2 (claude/s81-lp-2-1029@c1a5825a83e). COORD rulings on the LP-2 ASKs: (a) the kit-local `keep` drop
is OK, because the kit LEC proves the result equal (see below); (b) the east lane = a copy of the chosen west variant;
(c) centre clock entry = a parallel variant. GEOM-55: PASS-COND for PLACE, prefer B (wider streets), centre entry
is a must (the old tile measured 818 ps), move the landing windows under the lanes.

## Lane kits (intel2 /srv/opentallas-scratch2/claude/s81-lp-{2,3}-1029/kits)
| kit | outline | clock entry | max entry->corner reach | state |
|---|---|---|---|---|
| lp2a (LP-2) | 345.6 x 561.6 | N face centre M5 | 734.4 um | PLACE running (LEC stage) |
| lp2b (LP-2) | 302.4 x 630.72 | N face centre M5 | 781.9 um | PLACE running (LEC stage) |
| lp3ac | = A | centre M5 (172.812, 280.8), channel 162.5-183.2 | 453.6 um | PRE-PLACE PASS 0; PLACE running |
| lp3bc | = B | M5 (123.132, 315.36), column channel 112.3-133.9 (the geometric centre is over a macro column) | 494.6 um | PRE-PLACE PASS 0; PLACE running |
| lp3ebc (east) | = B | = lp3bc | 494.6 um | PRE-PLACE PASS 0; PLACE running |

- Centre variants (`centre_variants.py`) use the same RTL, macros, plan pins and LEF as LP-2 A/B. Only one single-root
  master-plan core slice is added (HCPL precedent delta_hcpl_clkentry_1027.py): a 4.32-um `ck_entry` island with an
  M5 entry. There is no pushdown, so the in-core tree is the kit's standard CTS (no new script).
  `--master-slice` moves the ck[0] line in io.tcl to the entry. The plan pins and LEF keep ck[0] on the N face, as
  in the HCPL precedent; the parent reaches the entry from M6/M7 over the lane.
- The east kit (`east_variant.py BC`) copies BC under the module name dsfd_coll_lane_e_safe8_ntf. The e wrapper body
  is identical to the w wrapper (ot_s81ph_coll_lane_safe4 CH_BOARD 700 TF_CLEANUP 1 REACH 2 CORE_CRED 12). run_kit
  checks LEC against the east RTL. The parent orients the lane (MX on an N link face); the kit does not change.
- `keep` drop (ruling (a)): this is a kit-local rtl_patch on ot_link_credit_{rx_b64,tx_rc}.sv (1-bit output reg
  attribute only), and run_kit's LEC (legacy_gate lec on the RAW netlist) proves the result equal. A plan/RTL
  follow-up should remove the need for the patch.
- Insertion ESTIMATE (UNCHECKED): ~19.7k sinks + 55 SRAMs. Assumed ~5 fanout-4 levels x 25-30 ps plus trunk wire
  at ~0.12 ps/um buffered M5. Centre entry: ~150 + 0.12 x 454-495 = ~205-210 ps TT, inside 250 +- 40.
  N-face entry: ~150 + 0.12 x 734-782 = ~240-245 ps plus root imbalance, marginal. The old 818-ps tile (W face,
  1015-um reach, old flow) does not scale linearly to these numbers. CTS measures it.

## Parent LP kits: ESTIMATE before build (`parent_estimate.py` -> parent_estimate.json)
- On every one of the 3 cut types, the link face carries other plan windows besides coll_*: s_0S_LP has ft0..ft3 +
  unit_i0 (S), s_0N_LP has ca_o0/cb_o0/tl_i0 (N), s_7N_LP has ft0 + tp_i0/tp_o0 (N). A uniform 4-lane row covers
  them all, and the ft slots need stations every <=450 um, so a feedthrough cannot fly over a 630-um lane.
- Today's coll windows are not under the lanes. A uniform row gives a mean sideways landing of 170 / 337 / 216
  um per bit (s_0S / s_0N / s_7N; 4 x 1027 bits).
- Proposed layout (all 3 types): L0 L1 | one street with all the other link-face windows | L2 L3, variant B
  lanes. The coll_iK window sits under lane K's rx pins and coll_oK under its tx pins, so the sideways landing is 0.
  The lane gaps are 4.0 / 12.0 / 12.3 um and the street is 212 / 189 / 188 um wide. Variant A (4 x 345.6 = 1382.4)
  cannot also fit the >=176-um street, so B is required for the parent, not just preferred.
- This needs a plan event (bus windows on the link face of the 3 LP types, plus the matching windows on their
  link-face neighbours). ASK to DIE-S81-23 / COORD.
