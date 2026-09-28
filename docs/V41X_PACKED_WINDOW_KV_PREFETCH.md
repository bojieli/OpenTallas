# V4.1 packed window KV die boundary

`ot_chip_v41x_window_kv_prefetch` is a window-only die component. It consumes
the core's 32-code/E8M0-scale block handoff and writes each block's 32 code
bytes and one scale byte to the 17-sector, 544-byte-pitch HBM row. The code
sector and the scale-byte write must both report completion before the next
block is accepted. A row becomes readable after all 16 blocks commit. The
128-slot ring holds an absolute-position and user tag, so position `r + 128`
evicts position `r` within a user and a stale read faults. User `u` has its
own 2,176-sector window region beginning at `region_base + u * 2176`.
For a prefilled HBM image, the host primes each already installed row's
absolute user and position tag through `prime_v`; a row cannot be prefetched
before its tag is published.

The fetched stage stores 528 packed bytes per row. It exposes the full packed
row and one 32-code/scale block for the attention engine, as well as an exact
FP32 element read through `ot_chip_v41x_window_row_codec`. The latter is a
compatibility path for the current element-wise core port. A read of an
incomplete, stale, or invalidated row faults. A block write invalidates any
staged copy of the same ring slot; a dependent read must prefetch again.

`python -m tools.rtl_chip_v41x_window_kv_prefetch` runs a focused HBM-sector
bench and writes `results/rtl/chip_v41x_window_kv_prefetch.json`. It checks
48 atomic block commits across three written rows and two users, one preloaded
row restored by priming, 17 sectors per fetched row, exact FP32 values at a
scale boundary, user-region separation,
the HBM code and scale bytes, the largest valid 1M-context position, rejection
of position 1,048,576, and eviction at the 128-row ring wrap. The
standalone row codec gate separately checks
the exact deployed golden quantization and thousands of packed decode
vectors.

The current component issues one HBM transaction at a time. It does not yet
wire the full die's mixed attention descriptor, which contains up to 128
window rows and 512 selected **compressed** KV rows. Those compressed rows
have a distinct 288-byte format and require a separate fetch/decoder. The
640-row stage and four-row-per-cycle attention feed need a banked packed-row
SRAM boundary and measured scheduling before the modeled V4.1 throughput can
be attributed to RTL. This gate establishes the window block write, packed
HBM layout, validity barrier, and read result without making that rate claim.
