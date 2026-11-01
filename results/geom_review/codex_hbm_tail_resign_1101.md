# HBM tail-native release-receipt review

2026-11-01 05:5x PST, Codex independent visual review before re-sign STA.

Pictures viewed: `/home/ubuntu/coord/tmp/codex-signoff-1101/review/tail_f56.png` and `tail_949.png`, copied unchanged from intel2 `kit-wave/hbm/d44o/items/ot_hbm_idx_tail_native__v{f56d1f72f3f3,9496b22d4b49}/attempt_2/geom/auto_geom.png`.

Verdict: PASS-COND under the standing fill/empty exception, concurring with GEOM-96. Both outlines are 218.6 x 187.5 um. The dominant signal pin bank is at the N face, and the dense compute band follows that face; the W pin column stays accessible. No macro walls or blocked streets exist. The lower half is sparse because this is a pin-bound plan slot. A central clock entry reaches the opposite corner within 194.4 um. Existing GRT overflow is zero; previous register reach census gives no >405 um signal pair. No placement or PDN changes are proposed. The existing routed DBs already have DRC/antenna zero and SIGNED+equivalent routed LEC receipts.

Action: re-sign only those same routed DBs with released `flow-20261101-m-hbm` tools in a separate Codex output directory. Original PASS receipts and routed DBs are unchanged; no new route.

## KV pv-join sample

2026-11-01 05:5x PST: `ot_qwen_tp8_pv_join_t__v9d707d929550` attempt_2 independent geometry review CONCUR PASS. Viewed `/home/ubuntu/coord/tmp/codex-signoff-1101/review/pvj_9d7.png`, copied from intel1 kit-wave qwen_kvsys/event28w_c. Compact clusters fill the 172.8 um square inside a perimeter register ring; no macros or blocked channels. JSON: GRT 0, r2r 233.5 um with zero captures >405, pin-register p90 9.16/max 15.1 um, unregistered pins 0, clock entry reach 163.4 um pre-CTS. E-face density 9.4/um and column demand .701 are warnings with measured GRT0. Existing route decision stands.
