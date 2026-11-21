# FAM-S81-SLICE-R3 handoff (Opus 5.5, 11-21 ~07:40 PST) -- STOOD DOWN (context); successor FAM-S81-SLICE-R4
W=epyc10 /srv/opentallas-scratch2/claude/fam-s81-slice (R1 root; clone $W/clone, branch claude/fam-s81-slice-wreg-1121)
L=epyc8 /srv/opentallas-scratch2/claude/fam-s81-slice-r2 (R2 root)
R3e8=epyc8 /srv/opentallas-scratch2/claude/fam-s81-slice-r3   R3=epyc10 /srv/opentallas-scratch2/claude/fam-s81-slice-r3
My local waiters die with this session: RE-ARM on every unit below (ot-wait <unit|client pid> on that host; export OT_LANE).

## Running units
1. WREG define-off LEC rerun: epyc10 ot-run client of $R3/lec3.sh, log $R3/lec3.otrun.log, out $R3/lec3/{lec.log,equiv_status.txt}.
   Script fixed per COORD (proc; memory -nomap; setattr -mod -unset keep_hierarchy *; flatten). It is in the clone as an
   UNCOMMITTED edit of tools/s81_slice/xs4_lec.sh, on top of commit aad23432b3 (follow-up with full message + Opus trailer;
   not pushed). On EQUIVALENT: commit the script edit (another follow-up, trailer), then in $W/clone
   `python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-push-main`, then post the define OT_S81SL_XS4_WREG,
   the sha and "+1 latency xs4 (xw_v/xw_d/fault)" to S81-J6-ASSEMBLY-R3. Text check ($R3/xs4_wreg_off_text.sv vs
   $R3/xs4_main_39d243610b.sv): default-off differs only by 4 pure wire aliases.
2. t37 manifest tree + bind: tree $R3/trees/src_s81_j6_t37reach1 (J6 wave tree 6cf12672 + overlay plan_h2_2249.json sha
   362a844d = t37 FSTART+reach1; STAGE-A linked; hash f375cabd). Running: epyc10 ot-run of $R3/bindtree.sh (publish ->
   strict bind into ${tree}_bind -> LATCHECK vs C1n gate -> tree verify), log $R3/bindtree.log.
   Next: on intel2 `kit_wave.py private-spec s81 slice_station__t37 --tree <tree> --lane FAM-S81-SLICE-R4` (rt/current),
   then copy+mv the spec with: gen_host/hosts/place_prefer -> epyc10 (epyc8 scratch was at floor), kit_rtl.bind_out ->
   ${tree}_bind, work -> $R3/pk/... Example edited spec: intel2 ~/coord/autopilot/private_specs/FAM-S81-SLICE-R3/
   s81_slice_station__t37_1121072206_e10/spec.json. Then nohup `kit_wave.py run-item SPEC` on intel2.
   The earlier run-item on the C1n hardlink tree FAILED src_manifest (21 drift files); that tree ($R3/candC1n_t37, and the
   alias epyc10 /srv/opentallas-scratch2/claude/fam-s81-slice-r2/candC1n_t37 -> it) is diagnostic only.
   Gate of these rows: GREEN (epyc8 $L/gates/candC1n_t37: bind 0, LATCHECK 0, 0/873 lanes differ vs C1n, G0 new 0, PRE PASS).
   On sign-off: FSTART + reach1 rows to S81-J6-ASSEMBLY-R3 (J7 layer A), then the siblings (t51 next; wave env for t51 in
   $R3/wave_env_slice_station__t51.json).
3. t49 internal hold ECO (COORD 07:45): epyc8 ot-run of $R3e8/t49_eco2.sh (hold_eco_internal_run.py, its own first sign-off;
   routed DB epyc8 /srv/opentallas-scratch2/claude/ot-jobs/slice_station__t49-route-outgoing-giraffe-4139840-1795235367/work,
   internal -4.54 on 2 ends, plan pads u_ft_ft7_o_5 q[282] and u_ft_ft8_o_5 q[74]). Out $R3e8/t49_eco2/RESULT.json.
   Pass 1 (t49_eco1) failed in insert: the old receipt's /work/nomcap libs are filtered out, so 0 HB4 masters (tool gap,
   worth a FLOW post). On SIGNED: standard export.
4. t36 route + sign-off: epyc10 ot-run of $R3/t36_route.sh (signoff_chain route on the hand-env kit
   $W/t36_c1n/gen/slice_station__t36), log $R3/t36_route.log. Hold split (posted): all 2,321 FF violators are port_in ft*_i;
   internal 0 at CTS and at GRT. The signable t36 is a private-spec regen from a manifest tree (COORD).
5. t9 WREG GRT: epyc8 client PID 948431 / oth-ubuntu-949753 (hand-env, 486k over the cap; WREG evidence only).

## Done
- census c1x_C posted. t37 gate green. Exact wave env for t37/t51 computed (kit_wave.item_env + flow_tag + stops_off).
- The missing OT_GPL_SPARSE_OVERFLOW on t36/t9 is the current gen rule (leaf only), not a gap.

## ot-run records (lane FAM-S81-SLICE-R3)
- epyc10 otrun-civil-redfish-123316 unit oth-ubuntu-124525-1795274689 = WREG LEC rerun (lec3.sh)
- epyc10 otrun-civil-redfish-367843 unit oth-ubuntu-369050-1795275213 = t37 manifest tree publish + bind (bindtree.sh)
- epyc10 otrun-civil-redfish-3908525 unit oth-ubuntu-3910202-1795273859 = t36 route + sign-off (t36_route.sh)
- epyc8 otrun-outgoing-giraffe-3968837 unit oth-ubuntu-3969870-1795274939 = t49 internal hold ECO pass (t49_eco2.sh)
- epyc8 client PID 948431 unit oth-ubuntu-949753 = t9 WREG GRT (R2 record)
- t37 run-item on the hardlink tree: EXITED (src_manifest FAIL); no run-item is live.

## Late result (07:4x, after stand-down)
- bindtree.sh (oth-ubuntu-369050) ENDED: the tree published fine (read-only, hash f375cabd), but the bind stopped with
  "no asbuilt.json in <tree>_bind (run bind.py elab, or stage the packaged cached elaboration)". Next for R4: copy
  asbuilt.json (+asbuilt_sources.json) from the wave J6 bind epyc10 /srv/opentallas-scratch2/claude/kw45/
  src_s81_pin_3c913dbdfb23_d8j6_1117_work_bind_11210316 into /srv/opentallas-scratch2/claude/fam-s81-slice-r3/trees/
  src_s81_j6_t37reach1_bind (reach1 changes no RTL, so the elab is the same; or run bind.py elab). Then rerun bindtree.sh
  minus its publish line (already published).
