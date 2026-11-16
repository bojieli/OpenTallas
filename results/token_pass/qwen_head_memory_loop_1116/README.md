# Native head memory-loop witness

The actual routed loops cannot execute against current READ_EXTRA9: E0 adds43edges and W0 adds42, but EXTRA9 only budgets8 above the nativeMIF1 base. Each current loop writes128 wrong values while retiring all128 operations. A short4+4loop is exact.

The opt-in segmented successor from7f5ea966cdd passes E0 with EXTRA44 and W0 with EXTRA43, SEGMENTED_MEMORY_DELAY1, ALIGN3, KV_WR_PIPE1. S1 retains two bounded8bit rings; S2 uses exact native32x64 SRAM segments. Generic ring limits are unchanged. This qualifies the native memory COPY mechanism only; it does not adopt a plan, imply physical closure, or qualify other operand classes.

Source origin: epyc2 actual treeJ and bound bind_s29q103S4Q9JBQL. Critical native VM8q/VMR/LRLY file hashes match treeJ byte for byte. All source dependencies, actual SRAM models, exact case benches and commands are committed under source_packet. Replay one case by copying source_packet/common contents to a scratch directory, overlaying source_packet/actual9 (or E0/W0), then running bash run.sh through the host admission guard. Source hashes are in source_packet/sha256.json. Build measured below0.5GB and20seconds at1thread; original admission8GB1T.

Dates are from delivered head input fields, not global CALR. The operand observer is first registered S1valid-visible edge; native S2data capture occurred one edge earlier. The raw aligned_va diagnostic prints the next raw word at that edge and is not a first S2data payload assertion. Receiver-sampled VM writes prove payload/address identity for all128 finite requests. The case stream preloads128 distinct finite FP32 values and writes a disjoint128word output region.

Failed initial fixture is retained in failure_r1. It omitted grouped SV input declarations and issued no VM writes. The corrected fixture control and all expected-negative evidence are separate.
