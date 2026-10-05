# V4.1 selected compressed-KV DMA boundary

The selected compressed-KV path reads a **different HBM region** from the
window KV ring. One compressed source row is 288 bytes: 256 bytes of 512 E2M1
codes, low nibble first, followed by 32 E4M3FN scales, one per 16 elements.
It occupies exactly nine 32-byte sectors, with no padding. The row byte
contract is `runtime/prefill/v41_main_kv_row.py`.

`ot_chip_v41x_ckv_selected_dma` takes an explicit `source_id`, the attention
job's `local_row`, its `window_count`, and the number of source rows whose HBM
writes have been published by ingest. It rejects an unpublished source or a
local row in the window prefix. The caller supplies four per-stack region
bases and sizes for the current user and owner layer, so distinct users cannot
alias. The global source ID follows the published placement: for `group =
source_id // 16`, `die = group % 4`, `stack = (group // 4) % 4`, and
`local_source = (group // 16)*16 + source_id % 16`. The sector address on the
owner stack is `region_base_sector[stack] + 9*local_source + sector_index`.
If that die differs from this one, the module raises `remote_needed` with
`remote_die` and issues no local HBM command; the array fabric must supply
the row. The HBM command/response pins match the four-stack die K-side bus;
the selected local stack issues one-sector reads. Only a fully
received, finite-scale row raises `kv_ok`. The staged row is tagged to its
local row and explicit source ID. A full packed row is exposed for an eventual
four-lane attention stream merger, while element reads return both the FP8
code and its exact FP32 expansion to the existing core-style KV read port.

The factored combinational decoder multiplies two short integer significands,
then performs exact E4M3FN RNE and finite saturation. It canonicalizes signed
zero. A NaN scale poisons the row. The exact-rational reference generates an
exhaustive truth fixture for all 4,096 code/scale pairs; the RTL matches every
FP8 result and FP32 expansion. Generic Yosys 0.68 synthesis reports 339 cells
for one decoder (no placed area or timing claim).
The source-pinned generic synthesis record is
`results/rtl/v41x_ckv_decode_synth.json`.
`tools/rtl_v41_ckv_selected_campaign.py` checks that fixtures are current and
runs a standalone DMA test against the golden: two 512-element selected rows on
different stacks, 1,024 matching FP8 and FP32 reads, 18 valid HBM sectors,
rejection of unpublished, window-prefix, and poisoned source reads, plus a
remote-die request without a local HBM read.
The source-pinned record is
`results/rtl/v41x_ckv_selected_dma.json`.

This gate establishes the selected-row DMA and decoder in isolation. Die
arbitration with window KV and the indexer, attention stream merge, ingest
publication signaling, full-shape token exactness, and physical timing remain
open. Its one-outstanding-sector schedule is not a throughput measurement.
