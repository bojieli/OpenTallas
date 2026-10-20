KV-CTL3 S32b native-safe successor

Exact gate-map native census PASS: maximum32, zero violations, zero role errors; 44725 roots. Source4541c6582, ep5 qkd_kvs_ctl_s32b-20261020-041935. Committed report: results/arch/kv_ctl3_1020/native36/rev3/mapped_native_census_s32b_PASS.json.gz.

Safe-design checklist before CTS (unchanged geometry from KV-CTL3 lane):
1. PASS: registered data pins and two-stage reset landing retained.
2. PLANNED: inherited345.6x475.2 CTL slot; placed reach audit remains a gate obligation.
3. PASS: exact mandatory mapped census max32, resets included; kept priority decode, staged /6 remainder cones, 14-bit kept writer hold muxes.
4. Unchanged own.cycle depth warning ~635ps/17levels from baseline; physical timing measured by gate.
5. PASS: control tables remain real SRAM macros, no added storage.
6. Inherited 43.2 lattice, one standard-cell band, aspect1.38, full-face pins; actual placement/pin density audit remains gate obligation.
7. Inherited single spine and clock budgets/hold margin; TT/FF spread remains CTS gate obligation.
8. PASS: zero added edges, same ports/macros/boot schedule; V5.050 module + real-boot-first-use + causal negatives committed.

No route/closure claim before physical gates, review and submit_exact.
