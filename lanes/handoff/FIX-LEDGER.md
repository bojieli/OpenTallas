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
