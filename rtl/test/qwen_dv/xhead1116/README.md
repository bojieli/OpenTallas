# Current native S8 consumer timing coupon

`bash run.sh /fresh/scratch/path` under the fleet resource guard builds the selected current J tap, one of 48 identical column-head straps and eight actual fo32 XS leaves. It injects finite BF16 leaf-boundary packets from the fresh native MIF1/CROM3 producer schedules. No MAC array or whole slice is simulated. The producer packet fixtures establish routing and timing; they do not establish tile arithmetic.

All four measured paired GO/XPF boundaries pass on every column. Moving GO one edge early or XPF one edge late catches a real native sticky fault. GO and XPF timing are coupled; the failed independent-minima assumption is retained. Existing `dv_lower_xhead.lower_layer` consumes the fresh source-composed ages, emits zero analytical errors, and its actual dates pass all 240 consumer coupons (five matvec invocations times 48 columns).

The coupon samples `hr_q` after FDN. The compiler's slice HR input precedes FDN by one edge: first corridor GO receiver is 20+1=21 edges (first X tag is one edge earlier); compiler XPF lead adds one and GO lag subtracts one. The last corridor receiver is GO+read_span-6. These are native zero-parent-transport component ages; current physical corridor pads and plan transport remain separate. Tile-delivery constants are not supplied.

Fresh ages are `results/rtl/qc_xhead_native_1116/xhead_ages.json`. Existing lowerer accepts them through `--ages`, with `DV2_S8DIE=1`, `DV_LOWER_VFLAGS='-DOT_QC_SRAM_MIF -DOT_S8_CROM_ALIGN'`, `DV_SU_AGES` and `DV_VEC_AGES` pointing at the committed native3/1 profiles. The native layer input is the committed r6 candidate in `qc_mif_native_1116/native_calendar_fix/mif1.json`.

The lowered Down GO moves from5081 to5093. The committed dependency follow-through below shifts the full downstream schedule; this component receipt does not claim a final bound programme. The old missing default cohort and historical literal receipts remain unchanged.

Dependency follow-through is executable through `tools/qwen_layerbench/compose_native_consumer_1116.py --ages results/rtl/qc_xhead_native_1116/xhead_ages.json --out /tmp/native-consumer-layer.json` under the same explicit native3/1 environment. It uses existing `pre_down` hooks and converges with12 cycles: layer6332→6344, chained6299→6311, cold6813→6825. Down/AR2/residual2 dates shift together; earlier stages stay fixed;406 entries and zero command/occupancy clashes. The paired memory-only+27 comparison is not silently amended into a new paired rate claim.
