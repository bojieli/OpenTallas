# V4.1 packed window die hookup

The full-shape die connects the core/tile's QDQ8 window block sideband to
`ot_chip_v41x_window_kv_prefetch`. Each accepted block writes 32 E4M3 codes
and its E8M0 scale to the 17-sector, 544-byte-pitch ring. The module waits
for both HBM write completions before publishing that block. A 10-bit user
tag comes from the host in host mode or from the package controller's
registered `core_user`; the region reserves `KV_USERS * 2,176` sectors, after
the configured index-key region. `WIN_STACK` chooses the one stack carrying
this small window ring. The full mode uses 30-bit K-port sector addresses;
the reduced mode retains its existing scalar KV prefetch and 28-bit default.

The die checks the KVT transposed address attached to each block before
forwarding it. A bad address sets sticky KV fault. The window DMA separately
checks user capacity, context range, block order, HBM responses and stale
ring tags. Unreserved users cannot alias user zero.

This is a **write-path and port-boundary milestone**. Full-shape scalar KVD
reads fault and `kv_ok` stays low. The adopted attention job also needs up to
512 selected compressed-KV rows, each 288 B of FP4 data, in addition to up
to 128 FP8 window rows. Source IDs must come from SEL memory, and compressed
rows are sharded across four dies; remote rows require the priced row
all-gather before the engine can consume them in exact local-row order.
The selected-row DMA and K request mux exist, but the die does not yet drive
that DMA or a mixed FP8/FP4 attention stream. No full-shape token, rate,
capacity or route result follows from this hookup alone.

`python -m tools.rtl_chip_v41x_packed_die_boundary` checks the reduced and
full die port headers with the exact tile and HBM PHY interfaces blackboxed.
Its source-pinned record is
`results/rtl/chip_v41x_packed_die_boundary.json`. The standalone packed
window RTL gate remains `results/rtl/chip_v41x_window_kv_prefetch.json`.
