# FLOW-STRIPBODY-1121 handoff (Opus 5.5) -- STOOD DOWN 11-21 ~18:4x PST -> successor FLOW-STRIPBODY-R2
Goal: strip/body split buildable end to end (lepe_mu_C t1, c1x_C t1..t10; one schema also for KV hub_Eo/Wo, pv; svc lo needs none).
L=epyc10 /srv/opentallas-scratch2/claude/flow-stripbody-1121 (lane clone $L/lc, branch claude/flow-stripbody-1121).

## Step 1 (merge order lever 8) -- push state
PUSHED main @b8643fbba102 (a0a69c899e7 strip_body event + b8643fbba10 port-geometry check), on 97321d8d031.
1. strip_body.py spec / split_axis_plan / split_spec / face_clip, schema strip_body (contents, split_axis, lattice_um,
   members_by_face), type_split strip/body support (clip_windows, tap_mode explicit, band_reshape + monitor slide,
   strapless_pieces, carry_short_fixed, whole_map_to_keep, strip_body key handled, census map_file lookup asbuilt dir then
   plan dir), kit_wave piece_base (<type>__strip_<face> inherits base item_env/type_args).
   Core-tap: my tap_piece was DROPPED in the rebase; main already has SVC-R7's _core_tap_piece (f11e3abd9c3) -- equivalent.
2. Event.port_geometry_check(): schema.validate on the output plan after every split, errors of ports touching a split
   piece fail (PORT-GEOMETRY); spec skip_port_check opts out. Test test_port_geometry_check_fails_split_ports_only.
svc hi4 port faults (A offset-piece mirrored windows, B cut-face port window/order) were landed by SVC-R8 lanes:
f11e3abd9c3 (cut face + core tap geometry), e1e3dfa8c0c (native mirrored windows). Not redone here.

## lepe_mu_C t1 proof (J6r1 plan s81/plan_h2_2249.json sha 44be6051)
- spec $L/spec_lepeC.json; split OK $L/split2 (y cuts 43.2/1183.68, 3 pieces, 17 ports added, 16 cut lanes).
- tree kw45/src_s81_pin_3c913dbdfb23_d8j6r1_1117_work_stripbody1121 (linked child of J6r1, published f67cf6a6).
- strict bind FAILED rc=1: `native stations s_7N_C__strip_N.leafdn_o0: expected one outgoing lane` -- strip pieces have
  no as-built content and no census. PV-R5 3a68739125 (split_bind_routes own cut leg first) may fix this alone.
NEXT: (a) rebuild split from main with spec + `census` (type_split.py census $L/spec_lepeC.json --bind <J6r1 bind>
  --out $L/census_lepeC.json; map_file fix now on main), re-delta the tree, strict bind + LATCHECK ($L/bind_job.sh) on epyc10;
  (b) kit_wave.py private-spec s81 <piece> --tree <tree> for lepe_mu_C__t1__strip_S, body, __strip_N; run-item to floorplan;
  report cell counts to S81-J6-ASSEMBLY-R4 + FAM-S81-LEPE-3.
## c1x_C finding (sent to FAM-S81-SLICE-R5)
Cores/SRAMs sit within ~30 um of faces -> strips only 17-43 um deep, too thin for ~86k band cells. c1x_C (and slice t9 486k)
need core_moves (moving cores inward) before a strip split; the bind/gen path for that is NOT in this push.
Per-type cut limits: t1 y[25.92,1149.12] t3 y[25.92,1200.96] t4 x[17.28,1365.12] t5 y[25.92,1166.4] t6 y[34.56,1192.32]
t7 y[25.92,1183.68] t8 x[25.92,1373.76] t9 y[25.92,1183.68] t10 y[43.2,1192.32].
## Units: none running (bind/census units DIED 10:27/10:29; the 16:15 DIED units under qc-plan-r12/strip_pilot are Codex's, mislabeled).
