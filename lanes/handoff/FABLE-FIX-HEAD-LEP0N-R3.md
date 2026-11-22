# FABLE-FIX-HEAD-LEP0N-R3 (Fable, 11-21 18:3x PST): hd_lep0N owner + HEAD e1a (successor of FABLE-FIX-HEAD-LEP0N-R2)

Predecessor: lanes/handoff/FABLE-FIX-HEAD-LEP0N-R2.md (section FINAL STATE). Hub logs intel2 ~/fable-fix-head-lep0n/.
Lane dirs: epyc10 F=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-env (R2), epyc7 /srv/opentallas-scratch2/claude/fable-fix-head-lep0n-r3/tmp.

## STATE 11-21 19:2x PST

### Kits: BOTH shelf proofs are ended. The shelf form is congestion-bound and at the cell cap.
- shelf_tg oth-ubuntu-21834-1795274496: stopped 18:30 PST by the fleet NOPROG watchdog (rc 143; 4_2_tapbal_grt, no non-iteration
  log line for 6.5 h, pre-GRT at it 13/30). Not by this lane. Record: epyc10 ~/.local/state/noprog/actions.jsonl.
- shelf_we oth-ubuntu-1587841-1795268678: CANCELLED by R3 18:42 PST (ot-run --cancel exact unit, container gone). Evidence
  (cancel class "flat GRT overflow over 2 rounds", job age 12.7 h):
  main GRT congestion-5.rpt -> congestion-10.rpt, both at the 20,000-gcell report cap, listed sum 89,584 -> 90,077
  (east band x 800-1700 y 500-750: 64,010 -> 60,221; west collector x < 200 y > 800: 18,059 -> 21,903; other 7.5k -> 8.0k).
  The watchdog labelled the same numbers GRT-CONGESTION DESIGN-FAIL. r11b (2x2 form) was cancelled at capped sum 52k -> 43k,
  so the shelf form is NOT better at GRT than the 2x2 form in the wave env (with OT_PGCAP).
  Cells: pre-GRT FF hold pass 2 ended at insts 494,506 = non-tap 395,746 (98.9 % of 400k); hold_cells 37,757; cross-tap +45.0;
  port_in 7,438 ends ws -72.2 (boundary, advisory); setup +22.0 unchanged. Reports stay in
  F/shelf_we/gen/gen/hd_lep0N/run/reports/asap7/dp_hd_lep0N/base/congestion-{5,10}.rpt.
- Both kit dirs are kept: ot-delete refuses them (guard: protected), and Codex's I/O relocation proof (unit
  oth-ubuntu-2578120-1795311923) mounts F/shelf_we/gen/gen/hd_lep0N/rtl read-only. Do not delete.
- Conclusion: the placed shelf form shows BOTH triggers OPUS-R3 set for the type split (cap + east density). Next lever =
  TYPE SPLIT (no more repair, no column form). Assets: epyc10 /srv/opentallas-scratch2/claude/opus-fix-head-lep0n-r2/split1121
  (Codex): TX split full LEC 356,004/356,004 (equiv_reset_residual_depth.log); io_stage_split native census hub 135,330
  (139,782 with allowance) + r0..r3 28.7-31.0k + io_stages 34,280, 49 macros (hub 25, 6 per lane); I/O relocation formal
  proof unit 2578120 still running (Codex's unit, leave it).

### e1a (HEAD event head_rp21z20NF15f_r17a)
- Adopted Codex contained r17a v2: tree /srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r17a_contained_v2_s0,
  manifest 561a1f11cf153c6c..., plan 00b2abf6e7a6 (sha256 62edabc647ac... of the snapshot copy), sidecar 6fcd1d3dfc43.
- Live tree check: shared live_s81_head on epyc10 + epyc9 is at 81ac28d407e8 (= snapshot s81_head_r17a_portable_s0, R2's e1a
  apply + Codex's portable pack). v2 (and its parent contained_s0 b523069d) were cut from a PRIVATE live copy
  (F/event1/containment_v2_1633/private_live, named in the snapshot .snap-group), so the shared live tree was not written
  again. epyc7's live_s81_head is still the 11-18 seed (81aad766). Consequence: the shared live tree is NOT r16 and NOT v2.
  A later live_tree.py apply (e.g. e1b) on the shared live tree would build on 81ac, not on v2: e1b must either apply its
  pack on a private live copy of v2, or first bring the shared live tree to v2 (delta 81ac -> b523 -> 561a = 10 sink bins +
  EPC Liberty made repo-relative, plan, wave_prepare, receipt). I did no live_tree apply.
- v2 replicated epyc7 -> intel2 (src_manifest replicate --link-from s81_head_r16_s0, "intel2: OK"). v2 now on
  epyc7, epyc9, epyc10, intel2.
- Candidate: intel2 ~/fable-fix-head-lep0n/cand_r17a_contained_v2_r3.json (= Codex normal_1633 with hosts/gen_hosts
  [intel2, epyc7, epyc9], gen_host intel2).
- GEN gate: publish_gate.py run --gen-host intel2 --item hd_lep0N --commit, pid in pgate_r17a_v2_r3.pid, log pgate_r17a_v2_r3.log.
- Marker (after the gate JSON line; advisory under --optimistic):
    RT=/srv/opentallas-scratch2/claude/rt/current/tools/autopilot
    python3 -I $RT/apply_reviewed_tree_marker.py --candidate ~/fable-fix-head-lep0n/cand_r17a_contained_v2_r3.json \
      --expect-source /srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r16_s0 --expect-event head_rp21z20NF15f_r16 --optimistic --no-pilot
  epyc10 is a current gen host holding a verified copy, so the marker keeps it as an extra; epyc9 is under its 250 GB admit
  cap and may come out APPLY-KEPT (not added).
- e1b stays out (HEAD-START-R17 tr12 219/329).

## FINAL STATE 11-21 19:5x PST (R3 stands down -> FABLE-FIX-HEAD-LEP0N-R4; read this section first; it supersedes "e1a" above)

### COORD rulings 19:2x-19:4x (dispatch of lanes/FABLE-PD-HEAD-2000.md)
- STOP relaunching the hd_lep0N shelf form unchanged. Representative = the TYPE SPLIT, and it must carry three rows besides the cut:
  (1) break the RX bank row (g_rx[0] + g_rx[3]: ten 51.4 x 20.8 SRAMs at y 637.7, x 1,008-1,620; no SRAM row over ~250 um without a
      >= 40 um gap, or two columns beside the consumers). Measure: V overflow x 1,000-1,625 y 635-662 at GRT it 5 (shelf_we: 12,045).
  (2) re-seat u_cland_coll_i1 (and twin coll_i2, y 120-326) with its ring logic out of the 65-um west channel that ends at the pair
      macro corner. Measure: listed overflow at x < 200 (shelf_we: 18.1k -> 21.9k).
  (3) a MEASURED pre-GRT hold margin (OT_PREGRT_HOLD_R2R_MARGIN), not 40: the 5 ps pass had 0 violating ends, the 40 ps pass cost 29.8k cells.
  Macro sites move, shapes do not.
- Do NOT apply r17a v2 as it is. Fold the split rows + the HEAD-CTL-R1 WRCAP row (plan 28819946547a, wave env) into ONE reseal of
  r17a (event head_rp21z20NF15f_r17a), then gate + marker. The marker was NOT run by R3. Wave is still r16 / s81_head_r16_s0.
- Launch the split representative on epyc7 or epyc9 (they admit), wave env via kit_wave.py private-spec, one A/B, post unit IDs.

### What R3 did not get to: the split has NO plan rows yet, so no unit was launched (0 units in flight for this lane)
Work order for R4:
1. RTL: Codex's private TX-lane extraction, epyc10 /srv/opentallas-scratch2/claude/opus-fix-head-lep0n-r2/split1121
   (derive_r16_split.py -> split_tx.sv: ot_s81hd_lep_core_nr_txext hub + 4 x ot_s81hd_lep_txlane; io_stage_split/split_tx_io_stages.sv adds
   ot_s81hd_lep0N_io_stages; native_wrapper.sv). Full LEC 356,004/356,004 (equiv_reset_residual_depth.log). I/O relocation formal proof
   unit oth-ubuntu-2578120-1795311923 (Codex's) was still in induction 18:5x with failing $equiv lines visible in
   io_stage_split/io_relocation_transitive_equiv.log (e.g. \w.u.pkrx[1]): READ its final equiv_status before using the io relocation;
   the TX extraction alone is the proven part.
   Census (native_split_bound_census.json): hub 135,330 (139,782 with allowance), r0..r3 28.7-31.0k, io_stages 34,280; macros hub 25, 6 per lane.
2. The type has ONE content (u_core), and tools/die_plan/type_split.py moves whole contents: the wrapper must expose hub / lanes / io as
   separate contents first (lane clone via ot-lane-clone on a build host; generator tools/s81_head/head_lep_split_sources.py already exists
   on main and is what derive_r16_split.py patches).
3. type_split.py split SPEC (family [hd_lep0N], cuts on the 8.64 lattice, keep = hub piece) -> plan rows; add the three PD rows above as
   macro site moves; strict bind + LATCHECK + G0 on the r17a v2 plan 00b2abf6e7a6 as base.
4. Private proof: kit_wave.py private-spec s81_head <piece> --plan ... --tree <v2 snapshot> --lane $OT_LANE on intel2, hosts epyc7/epyc9;
   A/B = hold margin (measured value vs 5).
5. Reseal r17a with split rows + WRCAP row: use a PRIVATE live copy of v2 (as Codex did: F/event1/containment_v2_1633/private_live), not the
   shared live_s81_head (it is at 81ac28d4, neither r16 nor v2).

### Publish gate on v2 (for the record; moot once resealed)
- R3 run on intel2 --gen-host intel2: verdict FAIL in 163 s, NOT a design result: every check failed with
  "ssh: Could not resolve hostname intel2" (the hub cannot resolve its own short name; static_s 0.0, dry gen stage mkdir).
  Record committed (coord 71b433d567e8, autopilot/publish_gate/s81_head/561a1f11cf15...json), log ~/fable-fix-head-lep0n/pgate_r17a_v2_r3.log.
  For the resealed package: run the gate with --gen-host epyc7 (as R2's run 3), or pass --hub so intel2 is treated as local.
  ot-run REQUEUE lines on intel2 showed the same name-resolution failure at 18:43 PST (other lanes' jobs): told FLEET in the post.
- v2 copies: epyc7, epyc9, epyc10, intel2 (intel2 replica by R3, link-base s81_head_r16_s0, verified OK).
