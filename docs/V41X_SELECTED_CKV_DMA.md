# V4.1 selected compressed-KV DMA boundary

The selected compressed-KV path reads a **different HBM region** from the
window KV ring. One compressed source row is 288 bytes: 256 bytes of 512 E2M1
codes, low nibble first, followed by 32 E4M3FN scales, one per 16 elements.
It occupies exactly nine 32-byte sectors, with no padding. The row byte
contract is `runtime/prefill/v41_main_kv_row.py`.

`ot_chip_v41x_ckv_selected_dma` takes an explicit `source_id`, the attention
job's `local_row`, its `window_count`, and the number of source rows whose HBM
writes have been published by ingest. It rejects an unpublished source or a
local row in the window prefix. The caller supplies `region_base_sector` for
the current user and owner layer, so distinct users cannot alias. A selected
row's sector address is `region_base_sector + 9*source_id + sector_index`.
The HBM command/response pins match the four-stack die K-side bus; one
parameter-selected stack issues a one-sector read at a time. Only a fully
received, finite-scale row raises `kv_ok`. The staged row is tagged to its
local row and explicit source ID. A full packed row is exposed for an eventual
four-lane attention stream merger, while element reads return both the FP8
code and its exact FP32 expansion to the existing core-style KV read port.

The generated combinational decoder enumerates every finite E2M1-code and
E4M3FN-scale pair using the exact-rational reference. Its output is finite
E4M3FN with RNE saturation and canonical positive zero. A NaN scale poisons
the row. `tools/rtl_v41_ckv_selected_campaign.py` checks that the generated
decoder and fixtures are current, then runs a standalone RTL test against the
golden: two 512-element selected rows, 1,024 matching FP8 and FP32 reads, 18
valid HBM sectors, and rejection of unpublished, window-prefix, and poisoned
source reads. The source-pinned record is
`results/rtl/v41x_ckv_selected_dma.json`.

This gate establishes the selected-row DMA and decoder in isolation. Die
arbitration with window KV and the indexer, attention stream merge, ingest
publication signaling, full-shape token exactness, and physical timing remain
open. Its one-outstanding-sector schedule is not a throughput measurement.
