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
