RoPE source candidate, execution unqualified

Selected DS L0 kv_rope.tail n64 uses A64 and B/D32 coefficients each, c_pair1, b_half1, alternating QM3, final BF16 rounding. Reference-only fixture check matches all64 output words. Existing exact FP32 intermediate rounding and final record rounding are retained.

Opt-in PAIR_C_READS defaults0 in canonical and actual scoped pgslice. A C request for physical bank L^1 is read through that adjacent bank's existing C reader; row address stays unchanged. A three-edge request selector follows existing RF/bank return selection. Conflicting simultaneous normal/pair reads of different rows fail closed. No new reader, macro, port, or calendar edge. MUT16 breaks the actual return source. Physical fanout/SS/FF remains unqualified; old physical views cannot alias this source.

B/D are not routed through the adjacent C exchange. The helper performs128 real scalar moves on original64 coefficient words, through VM/SU BYP/reducer/stree32/RF, then16 full RF-sector VM drains to a caller-allocated128-word scratch run. It reloads those actual VM words into identity-bank B/D rows. Scratch never enters cycle0 preload. The final q0 rows are serialized64-lane rows; all four pgslices own16 of those lanes. Reused coefficient tables support up to32 index_q rows.

API tools/hbm_layer_vehicle/su_rope_bank_1340.py lower(raw,q=0,data,place,tag,timing=NativeTiming(18,15),scratch_base=<allocated physical VM WORD base aligned128>,pair_c_reads=1,pair_source_path=<actual scoped file>). The caller owns scratch liveness; a scratch source is never a reference-data drive. Return includes canonical ql/lines, original-input preload/data, comparison-only scratch and output checks, exact runtime scratch writes/reads, RF moves and schedule. Scratch may be reused only after scratch_reuse_after_serial. Missing source/scratch fails closed.

Measured compiler schedule for selectedkv_rope:2088serial /2784stream edges. This replaces the original price; no cost mask. Model estimate was2300serial for staging. The private compiler fixture uses65024 as an explicitly allocated test run; production must use the common VM ledger allocation, never assume this address is free.

Actual selected RTL proof with real VM, pinned SRAM readers and stree remains pending. No connected functional, native, route or adoption claim follows from the compiler fixture check.
