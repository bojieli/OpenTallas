# ISA rows: N-row records (MINIMAL DRAFT by HBM-NEXT-UNITS, 2026-10-19)

**Flag: this is a placeholder draft.** The lane that owns this spec is HBM-NEXT-CMTP, which had not launched when HBM-NEXT-UNITS needed a decode rule. CMTP replaces this file (and adds `tools/hbm_next/isa_rows.py`). Until it does, the units implement only the rule below. The rule adds no new header bits.

## Rule (HGI-1 fields as they are, `tools/hbm_generic_iface.py`)

1. **The row count N is the row operand's `m`.** For an N-row record, every per-row operand (inputs A/B/C/D and outputs O/R) carries `m = N`, with 1 <= N <= 8 on the P = 4 die: 4 users, or 6 verify positions. HGI-1 already reads `m > 1` as rows in FUSED.ROW_NORM ("with m > 1 rows") and in IDX.TOPK ("per outer row of A (m rows)"). The draft extends that meaning to every unit in the HBM-NEXT-UNITS scope.
2. **The per-row stride is the same descriptor's `stride`.** Row r of an operand starts at `base + r * stride`, in the space's native unit. VM is addressed in 256-b sectors, and an HC residual row must be 32-sector aligned. `stride = 0` means dense rows, which is the d4g form and bit-identical to the current hardware.
3. **Operands shared by all rows** (the stationary HC mix weights, the norm weights, the IDX key stream, routed-expert weights) carry `m = 1`, or the `m` of their own matrix shape. They are read once per record.
4. **SM.MATVEC is unchanged.** Its `param[4:2] = positions - 1` (G18) stays, and it must equal `A.m - 1`. A mismatch is E_RANGE.
5. **Static schedule.** The compiler emits one record per layer-op for all N rows. The unit's row counter steps the rows on fixed edges. A unit pays its fixed span (descriptor, first access, tail, publish) once per record, and each further row costs that unit's measured row II. There is no per-row relaunch, no credit and no ready.

## Decode per unit (what the hnx RTL takes from the record)

| unit | record | rows field -> RTL | stride -> RTL | state |
|---|---|---|---|---|
| HC | HC.HC_MIX | A.m -> core `cmd_npos` (PMAX 8) and hc_q `residual_npos` | A.stride -> hc_q `residual_row_stride` [94:79]; O.stride -> `result_row_stride` [110:95] | RTL `rtl/hbm_next/hc/ot_hnx_hc_q.sv` (benched) |
| FUSED | HC_PRE_NORM / HC_POST / ROW_NORM | A.m -> row field | A/O.stride | HBM-NEXT-UNITS item 2 |
| COLL | ROW_GATHER / TOPK_MERGE / ARGMAX_MERGE / ALL_GATHER / GROUP_REDUCE_MCAST | A.m -> message-train length (one endpoint/crossing/tail) | A/O.stride | item 3 |
| IDX | IDX.INDEX (N queries), IDX.TOPK (heap reset per row) | A.m -> query slots (<= 4 x 4,096-word query store) | A.stride | item 4 |
| SU / SFU / DMA / ARGMAX | SU.VOP, SFU chains, DMA.KVWB_DS, DMA.LOAD, FUSED.QDQ, ARGMAX.LOCAL | A.m -> row counter (programme word 4-b N field = m - 1) | stride field (programme word) | item 5 |

## Open for CMTP

- Whether an explicit header field (for example the UOP `slot` bits [91:89]) should carry N for units whose row operand is not in VM (STREAM space).
- The union record for verify expert groups (IDX: 384-b bitmap + per-expert lane lists) is a new operand layout, not a rows field.
- CTL.TOKX (Q-MTP-1) is unchanged by this draft.
