# Qwen production reset clock-input correction

Source fix: `ed5b5c2148d63214e916ff4d7bf0e4ed6d64ae1c`.

The reset planner counted every clock-trunk endpoint as a receiving clock. A forwarded station receives `ck` and drives `ck_o`; its output was therefore mistaken for a second sampling clock. The single-clock safety guard skipped the required synchronizer. `clock_inputs()` excludes each clock trunk's driver endpoint. The mixed-clock leaf guard remains in place.

Actual full-shape GEN comparison, using the pinned g5r2b recipe:

| Source | Actual emitted-netlist audit | Repeater count | Synchronizer endpoints |
|---|---|---:|---:|
| Original g5r2b | FAIL, 2 untreated foreign reset releases | 13,761 | 3 |
| Original plus `8cd522a2f` | FAIL, same 2 untreated releases | 13,761 | 3 |
| Plus receiving-clock correction `ed5b5c214` | PASS, 0 untreated releases | 13,761 | 5 |

The corrected output drives both `rstt_rst_d2d__fo1__r4_21/clk` and `rstt_rst_d2d__fo2__r4_6/clk` from `n_pll_fwd`. Their `q0` outputs drive the two forwarded epoch hop-0 enable inputs on that same clock. Their `d` pins are explicit two-stage `qfd_rst_rep` synchronizer endpoints. See `production_comparison.json` for actual instance lines, endpoint metadata, all three run paths and SHA-256 hashes of source files, scripts, input plans and emitted netlists.

The corrected production run was `oth-ubuntu-77259-1792560557` on ep6, `/srv/opentallas-scratch/claude/codex-qw-reset-inputs2230`. It completed GEN with exit 0 and the emitted-netlist reset auditor with exit 0. The reset planner's production-shaped test includes the causal old-map negative; existing reset contract and forwarded-root tests also pass.

The complete production recipe includes pinned g5r2b geometry patches and the facts exporter, so this is not a claim that an otherwise narrow main checkout completed GEN. The actual `reset_sync_contract.py` is byte-identical to the narrow source correction. The actual `_reset_tree` function, preserved as `input_clocks/reset_tree.function.py`, is canonically identical (`ast.unparse`, SHA-256 `21161c983530097c3038563773b99048eb4a3cfa46fd4135c66f435bb8e5b0bd`) to the narrow main-plus-`ed5` function. See `reset_function_binding.json`. The full emitted netlists remain preserved at the source-bound run paths in `production_comparison.json`.

This establishes the production source correction and actual reset connectivity. It does not establish clock-phase timing, reset release calendar qualification, strict binding of a successor die, or physical closure. The independent final GEN-safety report still failed; `input_clocks/RESULT.txt` records `GEN_SAFETY=1`. Exporter diagnosis and remaining die crossings remain open. No GRT/STA result or waiver is claimed here.
