# SU.VOP N512/M128/LQ8 production chain on the reset-relay RTL (claude/hbm-suvop-rstrelay-1014), collected 2026-10-14

- Qwen q512: HGI_SU_PROD PASS, 101,800 sink-sector words; CASE0 service 1,831 / price 1,548 = 1.183 (FAIL vs 1.10; identical to the pre-relay 1,831).
- DS d512: HGI_SU_PROD PASS; CASE0 service 2,718 / price 2,912 = 0.933 (identical to pre-relay).
- N64/M64/LQ8 n64 PASS CASE0 4,105 = pre-relay; n64m6 MUTV6 FAIL 66,568 (observed mutant). Leaf benches in leaf.log.
- The relay changes no service cycle. Qwen 1.183 remains open (head allocator / drain); not qualified.
