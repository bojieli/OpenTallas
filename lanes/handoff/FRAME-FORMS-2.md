# FRAME-FORMS-2 handoff (S81 frame family col_h9/col_h10; Opus stand-in for FRAME-FORMS-1; COORD) -- 2026-11-13 06:58 .. 2026-11-13 07:26 PST

## Scope (brief, unchanged)
DIEVIEW-S81-1113 F1: 216 frame tiles = 216 plan types (pv variants, one layout per base) in 26 kit items, 0 signed off. ONE template
re-pack under R-STREET (cores move/rotate, never reshape; growth + cycles pre-approved): clear the band streets, use the east strip;
apply to all items; plan delta; G0/G0C; strict bind; latency; 2 private ot-run place/GRT/route proofs; ONE S81 frame event READY
(branch off origin main >= 24b08535da), adopted after 11-15 04:00. Compose with S81-FORMS-1 / DSDV-FORMS-2 / SVC-MACRO-2 by
per-type delta scripts (S81-FORMS-1 06:13 proposal). NOTHING is committed, built or posted yet. No plan file changed.

## Worktree / files (epyc8)
- /srv/opentallas-scratch2/claude/wt/frame-forms-2: branch claude/frame-forms-2-1113 = origin/main 24b08535da, no commits.
- /srv/opentallas-scratch2/claude/wt/frame-forms-2-street: worktree of the same clone, detached origin/claude/rules-street-1113
  8dd3028a50 (R-STREET street_rule.py with face_street / station_alley / transit_street; not on main yet).
- Work dir /srv/opentallas-scratch2/claude/frame-forms-2/: frames_base.json (26 base types + core_conns + core pin groups, from
  FRAME-FORMS-1 extract.py), graph.py (per-type core link list), rframe.py (type renders), w/sr_base.json (R-STREET check, all
  216 col_h types, base plan), w/rep_types.txt (one pv per base, 26 names), logs/.
- Base plan: epyc8 kw45/src_s81_main_7073a6b4a5/physical/die_plan/s81/plan_h2_2249.json sha 18c864518844 (ready12b-A).
- Renders of the 26 base types: epyc7 /srv/opentallas-scratch2/claude/frame-forms-1/base_png/ (FRAME-FORMS-1).
- Useful prior work: epyc7 /srv/opentallas-scratch2/claude/vislayout2-s81/b/ (INTENT_col_h9_r0.md + seed_r0/r2/h9r1/h10r2.py,
  form v5a, route_supply FLAG p99 1.5-1.7 -> ok 0.92-0.94 on col_h9_r0; never built: gen failed on schema key "sites" in
  internal_stations). Pattern for the chain (delta -> reach_fix -> collector -> stage table -> street check -> G0 -> G0C):
  epyc7 /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/chain5.sh (+ g0cmp.py).

## RUNNING (do not cancel; mine, harmless, plan-only, writes only into my work dir)
- epyc8 pid 3809411: street_rule.py legalize dry run (--no-bins, --rs-halving off) on the 26 rep types -> w/leg0_plan.json,
  w/leg0_event.json, w/leg0.tsv, log logs/leg0.log.

## Findings
1. Structure of a frame type (all 6 layout groups: h9 r0 p1-3, h9 r0 p4-6, h10 r0 p1, h10 r0 p4, r1, r2): two rows of ROM-elem
   bands (each row = W pair + E pair; pair = halves u_eK.u_w|u_eK.u_e, 268.38x221.4, all R0, abutted) + one bf band (bf16 halves,
   bf_col3_c, bf_front_roots u_eK, 1100 wide x 199). Elem pins: S face 608 pins in ONE 60-um group (rel x 143-201) = xs_q0/q1 +
   cfg + go; N face 66 pins (rel x 67-80) -> qbank_N u_bnK; W/E faces pinless. Feed per pair: qbank_S u_bsK (60x26, registered
   bank) under the pair junction drives BOTH halves (o_x0/o_x1 549 + o_cfg + o_go); cfg seq u_sK (17x52, W face 356 pins q0-q6)
   reads 7 ROMs u_cK_0..6 (ot_rom_4096x72_m8 38x63, rd_out 72 on S face, 14 addr pins at the W-face bottom corner) and drives
   bsK i_cfg/i_go (55 bits) + elem go_tag/ef (2+2 bits direct). cf (281x69) lands x_i0 1104 bits from the E face and broadcasts
   to the bands; node tree u_n* (43x78) + stations t*/t*__payload (sstn) carry results to frame_int_o.
2. R-STREET base (w/sr_base.json): every col_h type violates; e.g. h9 r0 p1: street 44 (worst: bs 8.64 um under the band S
   pin group, need 43.2), face_street 1, station_alley 2 (e4w.u_c|u_e4 25 um gap, 708 pins, 19 stations); h10 r0 p1 face_street
   17 (u_e0.u_w 17.28 from the W face, 2129 W pins); r1/r2: the E-pair bs (bs7/bs9/bs12) sits in the east strip 450-500 um from
   its elem pin groups (over the 405 reach).
3. Pure legalize (order-keeping) CANNOT fix the family without growth: dry run grows h9 r0 p1 1226.88 -> 1425.60 (+16.2%),
   h9 r0 p2 -> 1391.04 (+13.4%), h10 r1 +3.5% with 60 street errors left. The frame tile is on the rigid die lattice and the die
   (25.44 mm tall) is near the 26 mm reticle, so height growth is effectively unavailable. A re-pack (cores change order) is
   required; legalize is only the final polish.
4. Reach limits where ROMs can go: ROM -> seq <= 405 um (do NOT add stations: it changes the seq read latency) and seq -> bs /
   elem go_tag,ef <= 405, with the seq inside its pair span (both halves are 268 um apart). So the W-pair ROM groups CANNOT go to
   the east strip (850+ um); only E-pair groups can, with their seq at the E pair east end (x <= ~1065) and the ROMs at
   x ~1120-1300 near the seq height. DIEVIEW F1 fix ("move the small-core rows into the empty east strip") is right for E pairs
   only.

## Template design so far (FT1 "two-tier cfg rows + east strip"; not yet coded)
Height budget checked by hand on h9 r0 p1: fits at the CURRENT band positions (0 growth):
- bs of every pair: centred under its pair junction, top exactly 43.2 below the band S face (R-STREET-1, 1208 facing pins).
  Pull r1/r2 east bs back from the east strip.
- Tier 1: ROMs (R0, pins down) ABUT the band S face only on its pinless spans outside the fan region
  [u_w.x+143-8.64, u_e.x+201+8.64]; pitch 56.16 (18.12 gap, tap-legal for the 14 addr pins). W pair: 2 at the W span, 1 at the
  E end, plus 2 on the E pair W span [579,705] (reach ok from a W seq at the junction). E pair: E-end slot + east strip x >= 1120.
- Tier 2 (rest, ~2 per pair): under the fan region but not under bs: inter-band = MX hugging the lower band N face (avoid its
  N pin groups at rel 60-90 and the bn); bottom zone = R0 at y >= 93.3 above the ft1-ft5 corridor (ft regs y 15-89).
  Inter-band check: T1 bottom B_S-63, T2 top A_N+63, no x overlap; T2 pins face the fan at 104 um; bs faces A N face at 98 um.
- seq beside its bs (right side, W face 43.2 from bs), top 43.2 below the band; E-pair seq MY at the east end feeding the
  east-strip ROMs.
- bf feed (seq_bfp + 7 ROMs, 72 bits): Tier 1 abutting the bf S face on its pinless spans [100,410) / [770,870) within reach
  of the seq near e4 (bf fan region ~[420,760]); t2/t2p 43.2 below the bf S face under e4; bn of the band below side by side.
- bf band: widen e4w.u_c|u_e4 (25 -> >= 43.2) and the e4e side (VISLAYOUT2 moved u_e4 +25.92 / e4e +43.2).
- East strip: E-pair ROMs, cf (VISLAYOUT2: cf up 604.8 -> 665.28 opens a 78 um street), node tree, stations; then
  core_place.py --seed (hand seed for ROMs/seq/bs/bands, --fixed on them, search for nodes/cf/stations, --gap-pinface
  43.2:17.28:16), then street_rule.py legalize (rules-street branch) for residuals, then taps re-seed (clock added_taps are fixed
  points: ROMs must not land on them; grid taps carrying 3-4.4k sinks must be split; VISLAYOUT2 had move_taps.py/taptune.py).
- Not handled yet: face_street on W/S faces (h10 r0 p1 W face 2129 pins: elems 17.28 off the W face; r1 frame_int_i1 1264 bits
  on the S face under e5w.u_ha at 17.28), "land the S D-pin group at the street centre" (r2 frame_int_i0 1230 bits x 6-273).

## Next steps (for FRAME-FORMS-1)
1. Read w/leg0.tsv when pid 3809411 ends (confirms growth numbers per group).
2. Code the FT1 seed generator per base type (roles by inst name: u_eK.u_w/u_e, u_eK + u_eKw/u_eKe bf, u_sK, u_cK_j, u_bsK, u_bnK,
   u_n*, u_cf, u_rg*, u_t*), render, check reach (core_place TypeModel.llen, Manhattan between pin-group centroids) and R-STREET.
3. Apply per base to all pv types (layouts identical per base), as one per-type delta script; chain as hard-s81-dsdv-1/chain5.sh
   (+ street_rule sidecar for the landed sidecar collector types; strict bind because the reset collector tree follows cores).
4. Private ot-run place/GRT/route on 2 frames (one r0, one r1/r2), view renders; post the READY.

HANDBACK 2026-11-13 07:26 to FRAME-FORMS-1
