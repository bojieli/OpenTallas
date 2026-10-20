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
