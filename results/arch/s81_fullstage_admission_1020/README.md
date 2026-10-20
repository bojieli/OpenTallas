# S81 full-stage admission handback — 2026-10-20 04:51 PDT

STOP received: CLAUDE IS BACK. Evidence preservation only; no jobs remain live for this agent. No full-stage admission PASS, topology fix, eight-frame producer/RET/CAP vehicle, or new rate adoption.

## Preserved source and metadata

Parent component head b82da5c37 on codex/s81-calendar-capacity-1020 remains frozen. Continuation head 6eefead19 contains only the four-line opt-in OT_XS_COMPACT_TAILS candidate in xs_place.py. It is UNTESTED and UNQUALIFIED; default behavior unchanged. The census is metadata-only: no tensor payload read or rehash.

Unit oth-ubuntu-2934880-1792496684 on ot-epyc9 exited 0. verify_output PASS_AT_HEADER_METADATA_SCOPE covers all 15,360 expert identities, 46,080 weight/scale pairs, 48 immutable raw headers and 96,085 indexed tensors. all_expert_metadata.json contains tensor/scale names, shapes, shard and byte offsets. input_sources.json pins exact inputs. The first attempt failed on an incorrect U8 assertion; corrected source accepts actual I8/U8 and both logs are retained. Checkpoint revision dba1be0a40aa45a94ad051997016db3960a90277; index SHA256 74b0686a3d2891980d5e303251b075a3bccae2c2ff650747db2620a649b98fa8.

## Release blockers discovered

1. Actual p4l has 122 physical frames (12 slices with eight frames, two with seven, two with six). xs_place.op_groups deals rows to eight owners on every slice, while compile_frame enumerates actual owners. This omits 384 wq_b rank rows, 54 merged-GU rank rows per expert and 60 down rank rows per expert, summed over affected slices. Exact groups/counts are in summary.json. No topology-aware fix exists in this branch. A six-frame head needs at least ceil(512/(6*8)) = 11 phases, so the eight-phase first-slice component vehicle cannot establish whole-die rate.

2. Actual allocation pads partially SENT tail superrows into ROM. Preserved real GU six-expert field at /srv/opentallas-scratch/codex/s81-rom12-1020/out/fseq12/experts_gu.pickle, compiled by rootseg5 source, has per-qpair fill [240]*12 across physical pairs [0,1,2,3,5,6,7,9,10,11,12,14]. Reconstruction sums 16 words for every assign_slots entry in each ffn.experts_gu phase. This is 40 words/qpair/expert. The same source allocation rule gives down 20 words/qpair/expert (analytic, not independently measured here). Thus 60 words/qpair/expert × 15360/110 = 8378 > 8192 before dense weights. The raw-byte average capacity PASS does not qualify the actual allocator. OT_XS_COMPACT_TAILS limits npair to ceil(rows/2)*nseg to remove wholly SENT padding, but has no simulation or allocation qualification yet.

3. No current detailed p4l production stage/expert map was found. Current MU cal1 is 520 dies; ROMCAP's 110-stage/440-die scalar average does not select a map. The only located detailed canonical map is legacy NP2417/BF519, guarded as 81 stages, incompatible with p4l 122 frames/1464 q pairs. It covers all expert identities but is not a current admission vehicle. A real selected map, per-pair ROM and cfg admission, corrected ownership, consumer shape and transport proof remain required.

4. Parent/ROOT reports no current qualified CAP parent: capc5-land167af3006 has core/rt 134/178 FAIL; five-region C is unproven; old CAPC2 native/PG is not current landed parent. No full current CAP claim is made.

## Existing qualified component contract

b82da5c37 contains contents-only calendar reuse and ROM12/GU component evidence. GU same-origin span 2810 is measured. New eight-phase, 64-row, full-12-pair wq_b spine-GO to last frame RET is 1189, priced with opt-in tail307; default old223 preserved. It is not interchangeable with the legacy 1987 first-element-capture denominator. Existing 965.0 AR / 2998.8 MTP eight-frame scenario remains explicitly a projection, not adopted. Calendar packing L0 1868 and L2 2006 fit existing 4096-row calendar ROM and passed real reader tests; that component proof does not establish whole-stage ROM/cfg capacity or missing row ownership.

## Resume locations

Continuation worktree /home/ubuntu/wt/codex-s81-stage-admission-1020; frozen component worktree /home/ubuntu/wt/codex-s81-calendar-capacity-1020. Remote census /srv/opentallas-scratch/codex/s81-stage-admission-1020/root/out/census_r2/. All prior component jobs and census jobs are terminal. All fleet jobs belonging to other owners were left untouched. No further autonomy after handback.

## Resumed takeover: immutable compact-tail mechanism qualification (05:06 PDT)

Claude's active `/home/ubuntu/wt/s81-rate3-1020` topology work and its two existing field-calendar jobs were observed read-only and preserved. No changes from that evolving worktree were imported. The following independent measurements use immutable c347cea9b source, `OT_XS_QPAIRS=12 OT_XS_GU_MERGE=1 OT_XS_COMPACT_TAILS=1`, the same release h9/LK5 frame and existing Verilator5.050 sequence binary as b82 component evidence. All eleven imported Python files match c347cea9b SHA256 exactly (`compact_source_verification.json`); binary SHA is recorded in `compact_fseq/summary_down.json` and equals the component binary. Production RTL is unchanged. This qualifies the tail mechanism only on the first eight-frame slice, not topology or stage admission.

| Shape | Positive | Causal shorter-period control | Measured spine-GO to last RET |
|---|---|---|---|
| GU: 18 phases, 54 fixture rows | P145, golden/cycle exact, fault0 | P144 FAIL4 | **2812** (+2 vs existing2810) |
| Down: 21 phases, 70 fixture rows, per-phase real x | P130, golden/cycle exact, fault0 | P125 FAIL4 plus data timing errors | **2896** (+7 vs existing2889) |

The changed pair subset/return merges alter the tails. Existing2810/2889 prices must not transfer unchanged to compact mode. No compiler rate price or projection was changed here. GU tail slots shrink10->5; down tail slots shrink10->5. The six-expert GU-only address increments are `[176,176,160,192,240,224,208,208,176,192,240,208]` (total2400, mean200 versus old240 per pair). Actual down increments include one shared FP8 expert plus six FP4 experts; the exact vector and phase counts are retained in `capacity_bounds.json`. First attempt's down sequence generator refused differing x at phase4, after GU completed; this is preserved in compact_fseq.otrun.log. The corrected adapter enables the bench's existing PHASE_VM feature, with no DUT change. Its terminal result is PASS for the positive and expected FAIL for the negative. Units3015861-1792497664 (first, terminal1),3026382-1792497872 (down corrected, terminal0),3029434-1792497922 (capacity audit, terminal0). The accidental local deadline wrapper was suspended to prevent a deadline and retired only after its child terminated; no progressing fleet job was killed.

### Stronger capacity impossibility bound under existing slice ownership

The actual image writer's segment order yields80 paired-address increments per GU superrow (FP4 K5120, five segments),40 per down superrow (FP4 K2304, five segments). Existing semantic ownership gives every slice72 GU rows and80 down rows per expert. Even perfect packing therefore needs `ceil(72/2)*80 + ceil(80/2)*40 = 4480` paired addresses/expert/slice. Each six-frame slice has only`6*12*8192 = 589824` paired addresses: **at most131 experts/stage**, before any dense weights, per-pair imbalance, odd-row waste, idle-phase padding or cfg limits. At110stages that bounds the full catalogue at14,410 identities, below15,360;97stages at12,707. Consequently **tail compaction plus physical-frame-count fixes alone cannot admit a110-stage layout** while preserving the existing per-slice FFN shares. At least118stages is a necessary expert-only bound, not an admitted design. The current130-stage/520-die MU calendar is not ruled out by that necessary bound, but still has no selected map or per-pair/cfg/consumer admission. `capacity_bounds.py` and source-pinned JSON show the exact derivation; no average is a PASS.

### Additional producer and consumer audit gaps

- `lower_xs.placement` handles phase0 independently: ROWS_PER_SLICE28, ROWS_PER_FRAME4, one programme phase. Six-frame slices cl3S/cl4S place24of28 rows each, omitting **8 additional a_proj rank rows**. Physical nfr in xs_place/xs_bf does not repair this path. A correct new ownership/phase contract must cover phase0 too.
- Compact-tail condition `and mat.rows` leaves zero-row idle phases allocating full npair SENT segments. Global slowest-slice phase counts create idle phases on other slices. Actual EMPTY cfg/no ROM allocation must retain stream/phase identity and be qualified separately.
- Production `xs_place.write_images` still uses phase-local row tags. `xs_calendar.remap_tags` changes bench vector images only. Production consumers need real rank-local tags plus correct per-op output identity.
- Existing `xs_calendar.cmd_cap` assumes contiguous slice rows and loops `range(XP.NFRAME)`. GU_MERGE slice ownership has two disjoint gate/up ranges; physical6/7-frame groups also invalidate its fixed8 indexing. No new cfg_d emitter was implemented here.
- Current CAPC5c source is an evolving, physically unqualified successor. Old CAP/EDLY24/WL3DLY16 source and old fullsix private consumer cannot establish the new physical-owner shape or current landing ages. No current source-consumer claim is made.

## Final STOP handback (05:09 PDT)

CLAUDE IS BACK received again. No new launches/source work after STOP. The already-running consumer audit unit3060723-1792498180 completed terminal0 and was collected as evidence only: baseline GU_MERGE0 CAP emitter succeeds; identical source with GU_MERGE1 refuses with `slice share not contiguous`, produces no descriptor file. Actual compact GU RTL RET trace contains all four row-flag domains0/1/2/3; first observed RET edge387 has tag08000025, row16384, flags1. Rank-tag remapping preserves these flags, so real cfg_d updates must follow actual FIN lifetime and registered cfg path. This is an observational/source-emitter refusal witness, never consumer or full-stage qualification. Full logs and JSON are in consumer_contract/.

All own jobs terminal. Active Claude RATE3 worktree and its fleet jobs remain untouched and unimported. At05:09 local clients3297082/3297083 topo_s0/topo_s3 and3415702/3415703 prop_s0/prop_s3 remained present under /srv/opentallas-scratch/claude/s81-rate3 on ep9; these are Claude-owned, not this agents jobs. Existing component b82da5c37 remains frozen; measured compact/capacity evidence7ddede063 pushed before STOP. This final in-hand packet is preservation only. No further autonomy.
