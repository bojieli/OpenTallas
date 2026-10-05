# V4.1 core window KV block handoff

`ot_hdc_v41_qe` exports the QDQ8 activation quantizer's E4M3 code block and
E8M0 scale byte before BF16 dequantization. The `kvb_src_addr` is the 32-element
VM destination address for that quantized block. This sideband is valid only
for `QE_QDQ8`; a nonfinite input or a scale exponent outside the storable
E8M0 range raises `kvb_fault` and suppresses `kvb_v`.

`ot_hdc_v41x_window_kv_blocks` captures one 512-element QDQ8 row as sixteen
consecutive blocks. The following `DST_KVT` instruction supplies the matching
VM source base, 30-bit logical KVT base, and 21-bit absolute row. Its output
holds `blk_v`, base, row, block index, codes, and scale until `blk_ready`.
One handshake commits all 32 codes and their scale atomically. There is no
partial-block update; another QDQ8 row cannot enter until all sixteen blocks
have been accepted. The `cap_ready` and `issue_ready` outputs are required
dispatch conditions. The current QE has no input stall, so the controller
must prevent a new QDQ8 issue while `cap_ready` is low.

The KVT scalar address for dimension `i` of row `r` is

`base + ((r >> 4) << KVT_SH) + (i << 4) + (r & 15)`.

For block `b`, `blk_first_elem` uses `i = 32*b`. The 32 dimensions have stride
16 in logical element space. The first address is therefore generally not
32-element aligned. The die adds its user base and maps these logical values
to the packed window row's 32-byte code sector and scale slot. It must accept
the entire block as one transaction, drain it before a dependent prefetch,
and invalidate any staged copy of that row. Scalar `kv_wdata` cannot recover
the original codes or scale and must not update the packed window image.

This standalone source gate does not wire the new ports through the full core
or the die. It establishes the exact QE source and block handshake for that
integration. It does not measure a full token or write rate.
