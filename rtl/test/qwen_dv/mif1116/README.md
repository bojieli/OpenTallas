# Current native QC MIF calibration

The pinned capsule contains the current H/J SUVM, eight heads, native relays and SFUs. It compares MIF0/CROM3 with coupled MIF1/CROM3 and a mismatched MIF1/reply0 negative control. The test-only adapter drives landed `su_cmd`, bypassing command delivery and collective transport. Exact source hashes and boundary receipts are in `results/rtl/qc_mif_native_1116`.

Use `single`, `two_row`, or `silu_sigm` fixtures. `three_row_timing_only` preserves an oversized scalar-scoreboard experiment: its timing/counts are valid, but the third scalar row is not payload-qualified. Use `two_row` for bounded payload evidence. Outputs named scalar are streamed head values before the reducer, not completed partial sums. No absolute full-slice compiler profile is claimed by this bench alone.

Admit the runner with `ot-run`; provide a fresh scratch path. The same executable can replay any fixture by replacing `programme.hex` in a new runtime directory. The source capsule retains the exact behavioral memory models used by the native component, including collision assertions.


The compiler can consume the composed native profile directly. From the repository root:

```bash
env -u DV_SU_TRANSPORT DV2_S8DIE1=1 \
  DV_LOWER_VFLAGS='-DOT_QC_SRAM_MIF -DOT_S8_CROM_ALIGN' \
  DV_SU_AGES=results/rtl/qc_mif_native_1116/composed_base_3_1/slice_ages.json \
  DV_VEC_AGES=results/rtl/qc_mif_native_1116/composed_base_3_1/vec_ages.json \
  python3 tools/qwen_layerbench/dv_layer.py --out /tmp/qc-native-base-layer.json
```

`DV_SU_AGES` and `DV_VEC_AGES` affect default intake only; an explicit `load_ages(path)` wins. Unset variables retain the legacy defaults. The existing memory-profile mismatch check remains active. This command is for native zero-parent-transport analytical compilation. It does not qualify the current bound READ_EXTRA9 vehicle. Do not set `DV_SU_TRANSPORT` until QC resolves and measures its relative control/data and VM-loop contract.
