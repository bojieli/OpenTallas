QC over-cap clock-tap class, ONE class event (DIE-QC-84, 2026-11-06). Candidate only: plan_qc52 POR untouched.

Problem (census of the latest attempt of every QC wave kit, clock_taps.tcl "keeps N sinks > cap" lines, 6 hosts):
50 types keep taps far over the cap (1.2k..17k sinks on one tap; CB* types still run at cap 3000). The plan's
density taps only see planned face/ft sinks, so the real soft register inventory piles onto a few taps; the FF hold
misses are this tap/tree skew (QC-HOLDCLS-1, Codex east_event: crh1->crh2 -410 ps = 300 ps insertion difference
between two over-cap taps). Codex tap_split_1106 measured 5 types; this event applies the same recipe to all.

Recipe per type (model_class.py, one script for the class):
- measured register inventory (DFF/ICG/SDF/DHL/DLL cells) of the type's latest retained 3_place.odb, 8.64 um bins
  -> bins/<type>.json (clock.sink_bins_file; existing taps.py mechanism);
- clock: tap_mode density, tap_max_sinks = min(plan cap, 1200), tap_target_sinks 0.75 cap (0.65 / 0.55 only when
  the reach check needs it), tap_radius_um 200, tap_chain_affinity {radius 200, max_group 128} (default-off support
  already on main, bounded per-bit chain grouping, never adds cross-tap boundaries);
- new taps = taps.density_taps (unchanged code); check = taps.assign (python mirror of clock_taps.tcl) of every
  measured sink: max load <= cap and max reach <= 200 um.
Result (model_run.log / model.json): 50/50 PASS, 5501 taps. 47 at radius 200; the 3 first-run reach misses
(cbf_q00__cl870de686 200.8, sle_hc1__cl7d360508 206.9, slw_fw_v3 203.0 um) were bin quantisation (density_taps sees
8.64 um bin centres, a member register sits up to 8.64 um L1 from its centre): COORD 10:0x asked for all 50, so these
3 use tap_radius_um 191 (= 200 - one bin), giving actual reach 174.9 / 185.8 / 170.1 um, load <= 1200 (update
11-06 10:3x, model_class.py retries radius 191 after the target fractions).

apply_event.py replaces only partition_types[<type>].clock for the 50 types, each guarded by the sha256 of the
base type (refuses on any change). validate.py applies it to plan_qc52, reloads with schema.Plan and recomputes the
taps (counts equal the model) -> new_taps.json. tap_class_geometry.png = per-type sinks (gray), hard cores (blue),
new taps (red x).

NOT claimed: no CTS/STA/route, no hold or sign-off credit. Remaining zero-logic cross-tap pairs and the 120/160 ps
source windows still need actual CTS + ordinary hold repair. New tap ports change type interfaces: adoption needs ONE
native re-bind + parent clock composition (ROOT/wave), then ONE batch relaunch of the 50 rows. Types re-formed in
the meantime (CBN/CBF ring split, SU2, START4) must be re-measured on their new 3_place before their patch applies
(the hash guard refuses a changed base type).
