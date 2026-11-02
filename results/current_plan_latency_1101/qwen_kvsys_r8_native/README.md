# Selected native KV R8 compiler candidate

This is a separate compiler candidate with the selected native R8 pads folded into the current canonical base table. It does not change a plan, binding, RTL, calendar, programme or model default.

The base plan is d4710b2e4571100a (2404 lanes). The selected native receipt is `intel1:/srv/opentallas-scratch2/claude/die-kv-60/geom2/bind_merged`. All 2404 base lane costs and exact endpoints/widths match that receipt.

The production recipe uses its `geom2/r8/qwen_kvsys_r8_landing_bind.json` (replica=type, bus=leaf, exempt `^kreq$` / `^krsp$`) plus three authoritative member overrides. Those original recipe-base files had been pruned, but byte-identical committed copies survive at `results/die_kv_15_1028/vport_w_pads_b2.json`, `results/die_kv_37_rc_1029/pv_col_pads_28b.json` and `results/die_kv_16_1028/pv_v_pads_b4.json`. Their SHA prefixes de521f7fc7d92a9a / 27cc9f955acdbab2 / de92b34e91c72526 match the actual native bind report. The exact native base-table SHA prefix is 4336871c5b9c74a0. Full hashes and the merged members are retained in the compressed input artifact.

The binder's existing authoritative-ID rule replaces 24 / 1178 / 2022 members, with zero added or INNER members. A direct join against CURRENT native `bind_merged/bus_groups.json` matches every one of the resulting 6167 member IDs, lane IDs, bound depths and landed depths, with zero missing or differing values. See `member_native_join.json`. The fold then uses the existing `r8.lane_fold(members, Plan.lanes)` and `gen.write_latency(..., r8_fold=fold)` functions; it does not solve R8 again or change production policy.

There are 2047 lanes with native members and 393 lanes with a nonzero folded pad. Base costs 2–106 become folded costs 2–121; maximum pad is 116. The sum of per-lane maximum pads is 12844, which is a compiler summary and is neither a physical flop count nor a token latency sum. The native report's separately deduplicated applied pad-flop count is 866689. A base-table-only fold would miss the authoritative overrides (its maximum pad is only 17).

The first private caller mistakenly passed raw JSON `lanes` (a list) to `lane_fold` instead of `Plan.lanes` (a mapping), yielding an invalid empty fold. That trial remains in scratch at `candidate_latency/qwen_kvsys_r8_native_BAD_RAW_LIST` and was never published or adopted. The corrected caller uses `Plan.lanes` and an explicit nonempty-fold guard. These artifacts contain only the corrected candidate.

KV/TOK still owns programme, calendar, lease and model-path pricing/activation. Generic bus-group misalignment metadata is preserved by the native receipt; this table publication does not waive any functional invariant or qualify token throughput.
