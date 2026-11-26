# SYS_C west abort R2 plan review

**Scoped plan accepted for source gating. Actual detailed placement and timing remain pending.**

I opened the new G4 plan and the focused overlay. The proposed mismatch register fence lies above the PHY body and between its SRAM banks. It preserves the existing macro outlines, boundary sites, straps and lane geometry. The upper routing band remains visibly busy, so the changed implementation needs actual detailed placement and a fresh visual verdict before routing.

- E12 exact changed plan picture at /srv/opentallas-scratch2/claude/KV-NOROW/sysc_abort_local_1126/plan_review_r2/kv3_sys_c.png
- E12 focused overlay at /srv/opentallas-scratch2/claude/KV-NOROW/sysc_abort_local_1126/plan_review_r2/abort_west_plan_overlay.png
- Prepared plan 67959e5dd2ce, RTL b7999b752ef7 and anchored row 4d67d512f191

The added register captures the checksum mismatch on the existing receive edge. Its result feeds the eight west abort copies. The old CRC registers, the east copy, four local quarter copies, receive acceptance, TX, epoch control and reset behavior are retained. No interface or cycle changes. The exact native full-width bench compares 528 edges and detects the deliberately omitted CRC check on 47 edges.

Old placement timing reports −226.424 ps ideal at the west abort endpoint and +241.606 ps ideal at the worst existing CRC input register. The new capture uses part of that budget. This candidate is isolated from G5, KVN fences, straps and the forwarded-clock fixes. Subsequent placement should measure the added capture margin and the same eight endpoints before any route recommendation.
