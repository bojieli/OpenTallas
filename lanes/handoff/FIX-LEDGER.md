# FIX-LEDGER handoff (Opus, started 11-23 01:5x by COORD)

Job: lanes/DIE-FIX-LEDGER.tsv = one row per Fable gap item (FABLE-RC-REVIEW PARTIAL/MISSED/WRONG-CAUSE; later HOTSPOT-GAPS/HOP-GAPS).
Owner rule 6079af4: one comprehensive event per die, no partial apply. Cuts: HEAD r18 12:00, KV D29 14:00, QC V4 14:00, S81 J9 18:00.
Owner deadline = cut - 1 h (HEAD 11:00, KV/QC 13:00, S81 17:00).

Status rules I apply:
- GATED = row passed its own gate (PRE/bind/LATCHECK) and is in this event.
- ROW-DRAFT = named row with a form, targeted at this event (J9/D29(+D30)/V4(+V5)/r18), not yet gated.
- OPEN = no row, partial row, row targeted at J10 (not allowed: S81 has one event), or a reason not yet accepted by Fable.
- REASONED = reason accepted by the die Fable reviewer (FABLE-RC-S81 / -QC / -KVHEAD).

Build script: local scratchpad fl/bin/build.py (mapping per FABLE-RC-REVIEW line number).
v1 02:0x: 98 items. S81 43 OPEN/18 DRAFT/1 REASONED; KV 11/4; QC 3/9; HEAD 4/5. 0 GATED.
Dead-owner candidates: FAM-S81-LEPE-4 (last post 23:36), FAM-S81-DSDV-R1 (19:16). Unknown ids: RANKSEAT-R2, VIS-HEAD.
HOTSPOT-GAPS.tsv / HOP-GAPS.tsv: not landed at 02:0x.

## 02:5x state
- v3 ledger: 100 items (98 FABLE-RC + x1 SVC-HI4-SPLIT-F65F + x2 PHY-T1-NECORNER-1).
- Helper lanes I started (agent ids): FIX-S81-XG-STN a7a9aaee779b55334 (rc30 inner xg legs), FIX-S81-SVC-BCAST a8c9603916048346b (rc16), FIX-S81-SVC-LOSTART aa73a799dcaa5cd85 (rc25), FIX-S81-SVC-WESTRIP a3b5045d81be1bf87 (rc17/21/24), FIX-KV-PV-MESOFIFO ae1b569fcc8e401ce (rc128 ot_meso_fifo).
- COORD Fable co-owners: FABLE-UNC-S81-SVC ad36422a39196fd09, -S81-LEAF a123f45b0c046602a, -S81-DIE aa0cf9d7ecf0a898a, -KV a9b9c65e6b5f2d104, -HEAD a2c5304dd88cb994b.
- DEADLINES (revised): S81 ASSEMBLY intake Wave A 10:30, Wave B hard 12:30 (17:00 NOT usable). KV/QC 13:00. HEAD 11:00. QC V4-R2 c2 intake 08:00, c3 last call 09:30.
- Rulings: rc66 SPARSE-TAP-1 = serdes 11 types; eng/seqhost/gunit/bk_sel/iqf keep VIS-MISC J9 tap rows.
- Risks: SVC hi4 split bind 6-8 h vs Wave B 12:30; rc72 +43.2 does not fit die X (VIS-DIE options a/b); rc97 reason pending FABLE-RC-QC.
- Update script: fl/bin/upd.py <json> <ts> (scratchpad), then cat to hub + coord-commit.

## 03:2x
- HOTSPOT-GAPS e4a2ac3 ingested as 26 [hg-<die>-<cause>] class rows (S81 14, KV 6, QC 6). Owners: flow classes FLOW-OPS-R2; RESET-ASYNC/HOLD-SKEW/IO-BOUNDARY/HOLD-SHORT-PATH -> CLASS-FIX (agent id PENDING from COORD; fill owner_agent_id); demand/reach -> VIS lanes; CLOCK-* also TAP-GRID-R5.
- HOP-GAPS.tsv not landed yet (PRECHECK-R2; VIS-DIE-S81 routes it).
- Sweep every 30 min: read new posts in lanes/posts since last sweep, update via bin/upd.py, publish, chase OPEN owners. Report to COORD every 2 h (next ~04:5x) and at each cut.

## CLOCK CORRECTION (real 02:10 PST)
- My earlier "02:5x/03:xx/04:xx" stamps in this file, the ledger and reports were GUESSED and ~2 h ahead. Real time at ledger v8 (bb6386a) = 02:10 PST. Always run `date` first. upd.py now stamps real time itself (2nd arg ignored).
- So deadlines are further away than I implied: S81 intake 10:30/12:30, KV/QC 13:00, HEAD 11:00.
- Ledger 136 rows: 98 FABLE-RC + x1 svc-hi4 + x2 phy-ne + x3 qc-fefw + 26 hg classes + 8 hop classes. GATED: rc71, rc73, rc45, rc129.
- Extra helper lane: FIX-S81-UCF-VIEW af4f23223665e2940 (rc72 u_cf view pin access).
- FABLE-UNC-S81-SVC now BUILDS rc14/15/19/20 + SVC-SMS-ORDER; SVC-R9 keeps x1 split rebase. adv_hop_gap.py over-counts hcore->h4 ~8x.
- CLASS-FIX agent id still not received from COORD (10 hg rows).
- Sweep timer: background sleep 1500 (re-arm each sweep). 2-h report due ~04:00 real time.

## 02:54 (intel2 clock)
- Recounted the hg rows against HOTSPOT-GAPS v2.4 (05b3ebe0ae0). All 313 NONE items (S81 204, KV 74, QC 20, HEAD 15) sit in owned class rows. Ledger hub beed724.
- Counts were posted to COORD (072cd94). The next per-die OPEN post is due 05:00, then every 2 h. Stamp times from `ssh intel2 date`; it matched local time at 02:54.
- Slice C row re-issued as plan_f65f_xga2_xf_tl.json 6c1f82db89ab on epyc8/9 (tap halo fix by R6). Its gate is on epyc9.

## 03:4x
- New helper lanes: FIX-QC-STA-BTW a35deea6aa47630a5 (rc96) and FIX-QC-DPL-RERUN a9784a10c9cb5fea6 (x5).
- x8 is new: the KV hroot D28-geometry kits are at -76 ps post-GRT (HROOT-R1, path report generating).
- x9..x12 are new: the stale tap_offset class on S81, KV, HEAD and QC (FABLE-UNC-QC census tool lanes/handoff/FABLE-UNC-QC-tapoff_census.py).
- GATED: rc117 (TGR5-D29-SYSC-1), and rc17/21/24 (SVC-WE-STRIP, J9 row 3f; it has no row-level bind, so the composed bind covers it).
- rc66: tap-only is not reachable; FAM-S81-SERDES-R7 (aa41bc468fa649413) owns the keepout tap-site row.
- rc96: rc96 has a scope conflict (FABLE-UNC-QC withdrew STA-BTW-1, while the STA-1 probe measures 840 um). The helper answers by 05:00 and the row is due by 07:00.
- rc97: rc97 is ROW-DRAFT (btab_s4r swap). FABLE-RC-QC conditionally accepts a V4 cut with the 11 st_a types held; COORD's ruling is pending.
- S81 leaf row 3d is still in PRE, with its 4 h bind not started. The Wave A 10:30 warning is posted (ea4cdce).
- rc67 gate: the hop re-run on the composed J9 (~10:30) via PRECHECK-R2. Its watch (FABLE-UNC-S81-DIE) is short-lived, so check it myself.
- Next count post is due 05:00.

## 16:1x STAND-DOWN (replaced by PRECHECK-LEDGER-R3 05:52)
- Session paused about 04:18-16:10. On resume, u93 overwrote the hub ledger with a stale copy; reverted at 16:13 (edd7703 = R3 15192edde99). Post dc170d36.
- This lane makes no more ledger writes. PRECHECK-LEDGER-R3 owns lanes/DIE-FIX-LEDGER.tsv.
- The items handed to R3 are in the post.
- Lesson: always re-pull the hub ledger before any push. Never push a local master after a gap.
