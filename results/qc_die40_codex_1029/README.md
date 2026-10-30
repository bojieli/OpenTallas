# QC native prebuild fixes 2026-10-29 18:47 takeover

Base DIE-QC-39 L4: top413, native M7 census18short/6spacing. No signoff/freeze claim.

N1 replaces clipped endpoint keepouts in L9 with net-aware complete M8/M9 join, actual VIA89 pads at both ends, and both short M8 stubs. Same-net identity passes through MetalIndex; other-net PG at a joint cannot be skipped. Small actual MetalIndex check passes a same-net joint and rejects endpoint PG (the clipped-end mutant fails this case).

N2 adds the missing0.056um along-axis VIA78 minarea cap reservation when choosing M8 tracks. Forces provider ports coincident with a vertical trunk onto a real selected M8 landing track; otherwise the join generated unreserved access at the provider pin row.

N3 additionally clips cell M7 riser windows against actual native M7 pin rectangles, including explicit reviewed PHY stub extensions. A fixed stack base overlapping other-net native metal fails closed. Targets18short/6spacing class; no moved cells, RTL, cycles or constraints.

All are geometry-only prebuild runs on intel2:/srv/opentallas-scratch2/claude/codex-qc-1847/prov_R7N{1,2,3}. Every heavy run uses ot-run64GB/4threads. No P&R/STA launched. Existing R7/L4/L9 failures remain untouched. Render is generated with each prebuild; must view and review before materializing/route.

The pinned14MB src_pc snapshot is copied from DIE-QC-39, including the leaf-load change already on main9c711d06afa. It reads immutable predecessor clock/PG/access artifacts; all output and new source is in own lane root. Current native bind obligation remains pair image32h03039da9 (TOK-KV-4 now merged4208361ea2a).

N3 FAIL retained native_N3_fail.log: clipping ran before R7 backbone substitution and found ck_b1750/Y versus ck_n1752 at the old cell pin column. This is not an actual R7-stack conclusion. N4 corrects ordering: native clipping after mapping R7 M7 backbone coordinates. No source failure hidden, no physical route.

N4 actual R7-column FAIL retained native_N4_fail.log: ck_b3046/Y M7 backbone intersects actual native ck_n3048 M7 pin metal. Upstream structural fix RUNNING: unchanged backbone planner plus explicit reserved-metal argument containing7889 actual native M7 rectangles and reviewed PHY stub extensions. Outputs backbone_native/RN1,RN1c. Existing R7 default-window pin exceptions must be revisited on the new geometry; no pass assumed.

CORRECTION 19:01: N4 first flagged ck_b3046/Y is an overconservative check, NOT a physical short: backbone x23959.136 and native left23959.184 leave exactly0.032um M7 spacing. Indexed successor now uses actual CR.SPACE[M7]=0.032, not0.048, and includes emitted M7 minarea enclosure at riser ends. Actual predecessor18short/6spacing remains unclosed. Upstream reserved-metal backbone planner already uses actual0.032 geometry; its running result is unaffected.
