# V4.1 full-shape L0 execution connections

This inventory is checked by `python3 tools/v41x_l0_connection_contract.py` and pinned in
`results/rtl/v41x_l0_connection_contract.json` against the packed-adapter bypass at
`c235f4a3`. It is an integration contract for review, not an RTL token verdict.

## First executable layer

At position 199,999, layer 0 has `RATIO[0] = 0` and `T0 = 128`: its attention
reads 128 chronological FP8 window rows and no selected compressed-KV rows.
This makes L0 a useful first exact arithmetic gate. Its packed rows must still
come from the die's window HBM prefetch and row merger for an HBM-serving claim.
Feeding preloaded rows through the new adapter proves only the arithmetic
boundary. Layers with `RATIO > 0` additionally need RTL-selected source IDs,
selected FP4 CKV DMA, and cross-die delivery.

| Boundary | Current source evidence | Required connection | Owner proposal |
| --- | --- | --- | --- |
| Attention descriptor | `ot_hdc_core_v41x.sv:763` asserts `kvd_v` in every `S_DEC` cycle; `ot_chip_v41x_die.sv:345` accepts `att_packed_desc_ready` even without an outstanding descriptor | Latch one descriptor generation, check repeated fields, and qualify `kv_ok` with that generation. Clear on completed attention job. | Attention owner, with root approval of lifecycle |
| Window rows | `ot_chip_v41x_die.sv:504` ties packed window read low. The row merger and packed service exist separately. | Drive the 128-row refill from timed HBM through the window stage and ordered four-row merger into `att_packed_kv_*`; preserve valid/ready and final prefix mask. | Die packed-KV owner |
| Selected CKV | `ot_chip_v41x_die.sv:560` ties CKV client requests low; `ot_chip_v41x_attn_row_merge.sv:41` requires an explicit source-ID stream. `ot_hdc_v41x_xu_adapt.sv:368` writes local scan indices, whereas the CKV DMA decodes global owner bits. The TP4 final select is still marked estimated in `hdc_replay_v41.py:456`. | Implement real cross-die final selection and a local-index to global CKV-ID transform. Then read `SEL[0..NSEL-1]` from RTL-written VM and drive local CKV DMA or remote die request. | Root selector/fabric design; emitter and die packed-KV owners |
| Remote rows | `ot_chip_v41x_ckv_selected_dma.sv:71` derives owner die from source-ID bits `[5:4]`; the merger has tagged remote request/response ports, but the die does not connect them. | Transport packed 288-byte rows with user, layer, generation, source ID and local-row tags through the actual fabric, including credit and fault handling. | Root fabric design; die packed-KV owner |
| VM size | Shipped TP4 layout places `SEL` at element 365,024 and the next allocated region at 446,688. Die and tile now default to `VM_AW=19` in full shape and retain `16` in reduced mode. | Run the actual L0 program against the 19-bit VM and matching collective port widths. Later layers require VM region reuse because the uncompressed 40-layer layout reaches 1,342,632,160 elements. | Root allocation design; full-shape harness |
| QE weight HBM address | Selected checkpoint layout reserves 65,242,240 sectors, requiring 26 address bits. `ot_hdc_qstream.sv:50`, die `wq_addr:333`, and HBM PHY `w_addr:59` are 24-bit. Die now propagates `W_HBM` to tile, defaulting to the prior HBM mode. | Propagate at least 26-bit W-sector addresses through streamer, tile, die, PHY and model. Bind a placed region and capacity; use a sparse simulation backing for a full-shape gate. | QE HBM owner; root HBM placement |
| Pooled index layout | Die now propagates its `IDX_SHARDED` parameter to the tile, which passes it to both pooled reader and key writer. It stays opt-in (`0`) until the matching full-shape key image is bound. | Enable one configuration with a source-pinned sharded key image for layers that use the pooled indexer. | Index owner; die integration |
| Region placement | The RoPE guard checks `reserved_end` and 0.9 capacity, while the die can prove only keys and window as a lower bound. | Verify actual key, window, selected CKV, RoPE and weight allocations per stack, including nonoverlap and user capacity; fail closed on missing placement. | Root region verifier |

## Proposed descriptor lifecycle

The proposed die-to-service descriptor has `valid/accept` and a distinct
`staged` response. `user[9:0]`, `pos[20:0]`, `T[10:0]`,
`window_start[20:0]`, `window_count[7:0]`, `selected_count[9:0]`,
`sel_vm_base[29:0]` (VM *element* address), and
`published_source_count[20:0]` describe the rows. The die mints a 16-bit
generation when it captures a new descriptor; `staged`, packed beats, remote
replies and `done` echo it. A generation may wrap only with no outstanding
job. L0 has `selected_count=0`, so its selector base is checked for width but
never read. These widths are proposals for root review, not frozen RTL ports.

For later layers, the selected VM reader requests `sel_vm_base+i` and returns
one zero-extended 21-bit source ID with the matching generation. It must
arbitrate a real VM read port against collective/controller traffic; a
testbench-only hierarchical peek cannot qualify the result. Remote CKV
requests carry `{user[9:0],layer[5:0],generation[15:0],local_row[9:0],
source_id[20:0]}` and the response echoes the tag before presenting 288
packed bytes to the merger.

1. **IDLE:** Capture one new descriptor with user, position, row count, selected
   count, selector VM base, published source count and a generation. Repeated
   `S_DEC` assertions describe the same job; changed fields fault.
2. **STAGE:** Derive `W=min(pos+1,128)` and `NSEL=T-W`. Refill the window from
   HBM. For selected layers, finish the TP-wide selection, convert each local
   scan index to a global CKV source ID, fetch the `NSEL` IDs from RTL VM in
   order, and validate each against the published source count and owner map.
3. **READY:** Assert `kv_ok` only for the matching descriptor when the service
   can begin. A late readiness pulse with no outstanding generation must fault
   or be ignored. The core's `kv_ok && !kvd_v` issue rule remains intact.
4. **STREAM:** Supply exactly `ceil(T/4)` chronological beats. The mask is
   `1111` except for a prefix tail. Count accepted beats only when both valid
   and ready are high; hold data and mask during backpressure.
5. **DRAIN:** Wait for merger completion and attention-engine idle, then clear
   the generation before accepting another job. Errors in source ID, region,
   remote tag or beat count enter a sticky fault state.

The packed bypass record proves full-width port elaboration with an engine stub
and a two-beat forwarding test. Its real full engine still exceeds the bounded
local elaboration budget. A hierarchy or shard strategy is needed for the
numeric full-shape gate; that gate must never be reported as a chip rate or
physical timing result.
