This directory binds the VM allocation audit to the actual encoded G25 rank-0 programme, SHA-256 `43c1652f3c2348fd711c770c4769e041caa51a63209c34670c9993ccbbbe4d1d`. The generator decodes and re-encodes all 4,120 records exactly. It records 6,392 tensor dependency edges, every VM descriptor and its static address extent. Runtime-indexed operands remain unresolved. Operation order is not converted into a clock timestamp.

Regenerate with:

```sh
python3 tools/hbm_static/native_vm_allocation.py --out results/arch/hbm_vm_native_allocator_1015/frozen_g25_rank0.json
```

The current Layout tool has changed several tensor addresses by 64 words. Its literals must not be substituted into this frozen programme. In the encoded baseline, Q is word 53376, SC 53888, MB 54528, E 54592, SE 55232, EB 55296, SINK 55936, DEN 56064, PV 56128, and normalized output 57152. They are native SID0 ranges. Each word occupies one native 32-bit VM slot, including expanded BF16 values.

The actual physical request/reservation binding tool is `tools/hbm_static/native_vm_reservations.py`. Its input names an exact operation record SHA, actual producer RTL SHA, launch authority, operand, global sector, physical quadrant, logical owner and bank-input capture edge. It rejects address relocation, mismatched source profiles, nonexistent ports, simultaneous logical owners on one physical port, unbound runtime addresses and unsupported programme capacity. It emits the existing actual four programme-SRAM word ABI, including the measured two-edge-per-stage LG selector propagation. The supplied producer trace and absolute launch authority still require native hardware proof; passing this compiler is not that proof.

Concrete integration work remains:

- HC residual source correctly maps contiguous h at word0 through global sectors, with no four-SID transpose. Canonical MIXRAW is word145088, sector18136, SID2; its real three-sector reader now has a separate native P1 proof. The encoded programme supplies one position, not an inferred P8 stride. Rank0 projection rows are disabled by the actual 24-row/96-rank ownership rule. The real gathered result, rank-owned projection, P1 tail and released base/scale metadata producer must all be connected.
- ATT descriptors request H1. The existing fixed H16 controller cannot stand in for that operation. Its owner is implementing a source-compatible H1 mask and zero initialization. Actual physical NE interfaces still require implemented SID0 transport or a versioned, fully priced residency/port change.
- The SFU MAX lowering needs scaled-SC scratch before raw EXP E exists. The explicit candidate lease uses the future E region, word54592/sector6824, in an earlier epoch. It preserves raw SC. Actual source-RAM fill and MAX capture must finish before EXP overwrites E; the arithmetic owner is proving this epoch transition against native memory and a wrong-lease mutant.
- Existing HCOLL slot160 profiles failed the actual chronological endpoint sequence check. A new ordered source programme is under independent native network proof. Neither transport roundtrip nor the five-word retirement correction qualifies the whole kernel.

These are source-bound allocations and compiler checks. Whole-token native execution, global fixed timestamps, resident P6/P8 contexts, physical station reach and end-to-end throughput remain unqualified.
