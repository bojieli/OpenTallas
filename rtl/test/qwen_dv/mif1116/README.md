# Current native QC MIF calibration

The pinned capsule contains the current H/J SUVM, eight heads, native relays and SFUs. It compares MIF0/CROM3 with coupled MIF1/CROM3 and a mismatched MIF1/reply0 negative control. The test-only adapter drives landed `su_cmd`, bypassing command delivery and collective transport. Exact source hashes and boundary receipts are in `results/rtl/qc_mif_native_1116`.

Use `single`, `two_row`, or `silu_sigm` fixtures. `three_row_timing_only` preserves an oversized scalar-scoreboard experiment: its timing/counts are valid, but the third scalar row is not payload-qualified. Use `two_row` for bounded payload evidence. Outputs named scalar are streamed head values before the reducer, not completed partial sums. No absolute full-slice compiler profile is claimed by this bench alone.

Admit the runner with `ot-run`; provide a fresh scratch path. The same executable can replay any fixture by replacing `programme.hex` in a new runtime directory. The source capsule retains the exact behavioral memory models used by the native component, including collision assertions.


The compiler can consume the composed native profile directly. From the repository root:

```bash
env -u DV_SU_TRANSPORT DV2_S8DIE=1 \
  DV_LOWER_VFLAGS='-DOT_QC_SRAM_MIF -DOT_S8_CROM_ALIGN' \
  DV_SU_AGES=results/rtl/qc_mif_native_1116/composed_base_3_1/slice_ages.json \
  DV_VEC_AGES=results/rtl/qc_mif_native_1116/composed_base_3_1/vec_ages.json \
  python3 tools/qwen_layerbench/dv_layer.py --out /tmp/qc-native-base-layer.json
```

`DV_SU_AGES` and `DV_VEC_AGES` affect default intake only; an explicit `load_ages(path)` wins. Unset variables retain the legacy defaults. The existing memory-profile mismatch check remains active. This command is for native zero-parent-transport analytical compilation. It does not qualify the current bound READ_EXTRA9 vehicle. Do not set `DV_SU_TRANSPORT` until QC resolves and measures its relative control/data and VM-loop contract.


A fresh paired MIF0/CROM3 baseline can be emitted with the composer option `--native-mif 0`; it uses the baseline measured in the same current component, not a historic age file. `composed_base_align3_mif0` and `composed_base_3_1` were both analytically compiled with the actual S8 selector. The native tagged path now charges its freshly compiled attention-return span, rather than applying the old 98-edge whole-family record. The resulting conditional chained difference is +27 cycles. Both compiler vehicles still report unresolved coverage/capacity; the MIF1 calendar additionally exposes a historical absolute SEG-date clash with a shifted residual command. See `native_pair_price/price.json`; this diagnostic is not a qualified release price or final bound calendar.


The native calendar follow-through in `native_calendar_fix` places SEG22 at the earliest free pulse inside its source-derived controller interval, keeps all fixed ME/END rows byte-identical, and validates the selected native AR framer. Both paired fragments now retain406 entries with zero clashes. Native capacity is a separate CALR/LOCAL4 count check; real installed masks, full boot/event image, per-instance slice selection, and stage37 remain unqualified. `remaining_blockers.json` identifies the four concrete consumer/data joins and next actions. The earlier failing calendar and shared-PW diagnostic remain preserved under `native_pair_price`.
