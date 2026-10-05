# V4.1 packed window KV address contract

This is the address/layout proof for a full-shape **window** KV row. It does not
validate a full token, the die prefetch scheduler, the quantizer, or timing.
Compressed CKV main rows use a separate 288-byte FP4 format; index keys use a
68-byte format. Neither may be interpreted with the 528-byte window mapping.

For each layer die, the core sees two aliases of the same 128-position window
ring: `KT` transposes groups of 16 rows so one 512-bit read contains one
dimension from 16 rows; `KR` is row major so a read contains 16 dimensions
from one row. For `slot = absolute_position % 128`, `dimension = 0..511` and
16 lanes, the persistent ring offsets are:

```
KT scalar offset = (slot // 16) * (512 * 16) + dimension * 16 + slot % 16
KR scalar offset = slot * 512 + dimension
core word offset = scalar offset // 16; core lane = scalar offset % 16
```

The die must map either core alias to **one** packed row: 512 FP8 code bytes
followed by 16 E8M0 scale bytes. The row occupies 17 consecutive 32-byte
sectors, or a 544-byte HBM pitch. For user `u`, reserve at least `u_count *
2176` sectors per window layer per die. Given an external region base sector:

```
row_first_sector = region_base + u * (128 * 17) + slot * 17
code_sector = row_first_sector + dimension // 32
code_byte = dimension % 32
scale_sector = row_first_sector + 16
scale_byte = dimension // 32
```

The scale sector uses only bytes 0..15; its upper 16 bytes are padding. The
existing one-user `Placement.window` region reserves only 2,176 sectors. A
second user requires a newly reserved, disjoint second region before enabling
that address. The 30-bit sector arithmetic must be checked before truncation.
The low seven position bits select a ring slot, while an **absolute-position
tag** rejects reads after that slot has been evicted and reused at `p+128`.

An update is atomic at the **32-code block plus its one scale byte** boundary.
Those bytes occupy two HBM sectors. A reader cannot see a new code sector with
an old scale, or the inverse. The die must hold the block unavailable until
both sector writes drain, invalidate a prefetched copy, then refetch before
asserting `kv_ok`. It also needs the prequantized 32 inputs to compute the
golden scale and codes; the existing scalar BF16 writes cannot reconstruct
them. The standalone row codec already makes this limitation explicit in
`docs/V41X_PACKED_WINDOW_KV_INTERFACE.md`.

The maximum all-window attention op is 640 rows: 337,920 packed payload bytes,
348,160 HBM bytes including 16 padding bytes per row, and 20,480 possible
512-bit *unpacked* core words. Storing those words would consume 1,310,720
bytes per slot and violate the 338 KB packed staging budget. The staging SRAM
therefore holds packed payload rows; the core-facing 512-bit word is decoded
and scattered on demand. These figures are exact layout arithmetic, not a
throughput prediction. Each user/layer/die window ring reserves 69,632 HBM
bytes, independent of the 1M absolute-position limit.

The *attention job* needs a second, local row space. At absolute position
`p`, let `W = min(p+1, 128)` and let `NSEL <= 512` be the number of selected
compressed rows. The core's attention adapter can consume only `W+NSEL <=
640` rows. Its local row `r < W` resolves to window absolute row
`p+1-W+r` and then to the ring slot above. Local row `r >= W` resolves to
the explicitly selected CKV source row `SEL[r-W]`, which is stored as a
**288-byte FP4** compressed row in a different region. The last KT group
has masked padding lanes when `W+NSEL` is not a multiple of 16. The die
needs the local-to-source map or equivalent descriptor metadata; a KVT
address alone does not distinguish the row formats.

The existing reduced emitter uses absolute `POS`, `POS1`, `ROW` and `ROW1`
selectors. It cannot send a 1M-position row number directly to a 640-row
attention adapter or a 128-row ring. The full-shape emitter must use local
`WIN-1`, `WIN` and their dimension-scaled selectors and carry selected CKV
IDs. This is an **open integration requirement**, not a passing gate in this
address checker. The actual 128-window-plus-512-compressed payload is at
most 215,040 bytes and transfers 217,088 B at 32-byte sector granularity;
the 337,920-byte all-window figure above is a conservative envelope.

`python -m tools.v41x_packed_kv_mapping` regenerates the source-pinned
`results/rtl/v41x_packed_kv_mapping.json`. The checker enumerates all 131,072
KT/KR scalar aliases and the tests exercise second-user separation, the 1M
boundary, ring eviction, address overflow, both atomic-drain orders, and
read-after-write. The standalone RTL row-codec evidence is
`results/rtl/chip_v41x_window_row_codec.json`.
