# QC native prebuild fixes 2026-10-29 18:47 takeover

Base DIE-QC-39 L4: top413, native M7 census18short/6spacing. No signoff/freeze claim.

N1 replaces clipped endpoint keepouts in L9 with net-aware complete M8/M9 join, actual VIA89 pads at both ends, and both short M8 stubs. Same-net identity passes through MetalIndex; other-net PG at a joint cannot be skipped. Small actual MetalIndex check passes a same-net joint and rejects endpoint PG (the clipped-end mutant fails this case).

N2 adds the missing0.056um along-axis VIA78 minarea cap reservation when choosing M8 tracks. Forces provider ports coincident with a vertical trunk onto a real selected M8 landing track; otherwise the join generated unreserved access at the provider pin row.

N3 additionally clips cell M7 riser windows against actual native M7 pin rectangles, including explicit reviewed PHY stub extensions. A fixed stack base overlapping other-net native metal fails closed. Targets18short/6spacing class; no moved cells, RTL, cycles or constraints.

All are geometry-only prebuild runs on intel2:/srv/opentallas-scratch2/claude/codex-qc-1847/prov_R7N{1,2,3}. Every heavy run uses ot-run64GB/4threads. No P&R/STA launched. Existing R7/L4/L9 failures remain untouched. Render is generated with each prebuild; must view and review before materializing/route.

The pinned14MB src_pc snapshot is copied from DIE-QC-39, including the leaf-load change already on main9c711d06afa. It reads immutable predecessor clock/PG/access artifacts; all output and new source is in own lane root. Current native bind obligation remains pair image32h03039da9 (TOK-KV-4 now merged4208361ea2a).
