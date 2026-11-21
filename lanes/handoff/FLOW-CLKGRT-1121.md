# FLOW-STRIPBODY-1121 handoff (Opus 5.5, started 11-21 ~16:4x PST) -- ACTIVE
Goal: strip/body split buildable end to end (lepe_mu_C t1, c1x_C t1..t10; COORD: one schema for KV hub_Eo/Wo, pv too).
L=epyc10 /srv/opentallas-scratch2/claude/flow-stripbody-1121 (lane clone $L/lc, branch claude/flow-stripbody-1121, NOT pushed yet).

## Form (decided, posted 17:4x)
Notched strip cannot be a kit (ORFS block = rectangle, die partitions tile). strip_body key -> `strip_body.py spec` -> type_split
one-axis split: face strips = full-length rectangles, depth = band clipped to nearest hard core / plan-sited content macro (+halo),
floored to 8.64 lattice; body = keep piece (names, origin, START). Pieces <type>__strip_<face>; kit_wave piece_base() inherits base env.
lepe_mu_C t1 (J6r1): y cuts 43.2 / 1183.68; W/E infra stays in body.

## Code (lane clone, uncommitted until bind green)
strip_body.py (split_axis_plan, split_spec, spec CLI, contents cutouts, members_by_face), schema.py (+dump), type_split.py
(clip_windows, explicit tap mode, band_reshape, monitor slide, strapless_pieces, carry_short_fixed, whole_map_to_keep,
relay_depth to body, core taps follow their core = COORD svc hi4 defect), kit_wave.py (piece_base); tests in test_strip_body,
test_type_split, autopilot/test_kit_wave_strip_piece.

## Proof
- split OK: $L/split2 (report.json: 2 windows clipped 5.56 pins/um, 16 cut lanes, latency rows latency_rows.json).
- tree kw45/src_s81_pin_3c913dbdfb23_d8j6r1_1117_work_stripbody1121 (linked child of J6r1, published f67cf6a6).
- strict bind + LATCHECK: ot-run unit oth-ubuntu-319614-1795284804 epyc10, $L/bind_job.sh, logs $L/bind1.log, latcheck1.*
Next: on green -> ot-push-main, then rt private-spec s81 <piece> --tree <tree> --plan <tree>/physical/die_plan/s81/stripbody_lepeC/plan_c.json
--bind-out $L/bind1 for strip_S, body, strip_N; run-item to floorplan; cell counts.

## Update after stand-down (hook arm unit oth-ubuntu-1261313-1795279984 ended rc 1)
- Clock-first route itself COMPLETED: phase 1 158 s, whole two-phase route 4783 s (base arm still at iteration ~15 then).
- Then the harness's start/end_incremental usage report died GRT-0116: grt::read_segments resets allow-congestion. Fixed in the
  epyc10 lane clone (hook re-arms ::grt::set_allow_congestion 1 after the merge); kits with grt_allow_cong.tcl were already covered.
  The clkfirst arm will die the same way at its report step: its segments (out/clkfirst_p1.seg, clkfirst_p2.seg, clkfirst.seg)
  survive. R2: add `grt::set_allow_congestion 1` before the report in h/arm.tcl, rerun hook (fixed tcl to <W>/h/), compare with base.
