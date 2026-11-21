# KV D26 hroot net2446 guide review

I inspected the retained hroot global-route congestion image. The main routing fabric is open, with localized sites of high utilization. The failed transition lies in an interior column near the east edge and the problem is local to the metal access there. It does not require moving a macro or resetting the clock topology.

The retained guide drops from M8 to M6 through M7 in the 0.57 µm cell with lower-left coordinate (1870.170, 562.020). Two full-height M7 special wires occupy x = 1870.224 to 1870.512 and 1870.608 to 1870.896 µm. Half wire width plus width-dependent spacing covers the entire set of M7 tracks in the transition cell. The surrounding metal also limits the cells directly above and below. The existing kit reported PG track truth and regional PG capacity cuts, so a local check will inspect which constraint actually reaches the transition before any broader route.

Reviewed image: epyc8, /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D26/items/kv3_hroot/gen/kv3_hroot/run/layout_review/grt/congestion.png. Retained guide: epyc8, /srv/opentallas-scratch2/claude/fable-fix-kv-hub/r4/net2446/guide.tsv.

Verdict: PASS-COND for read-only local global-route diagnostics on the inherited checkpoint. The retained production route still fails detail routing at this transition.
