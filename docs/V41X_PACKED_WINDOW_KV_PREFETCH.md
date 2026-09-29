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
The sector responder withholds request readiness on a deterministic subset
of cycles; all commands hold their address and payload until accepted.

The current component issues one HBM transaction at a time. It does not yet
wire the full die's mixed attention descriptor, which contains up to 128
window rows and 512 selected **compressed** KV rows. Those compressed rows
have a distinct 288-byte format and require a separate fetch/decoder. The
`ot_chip_v41x_kv_reqmux` lets the two fetchers share the die's K-side HBM
arbiter with a response-owner tag bit. Its focused gate checks same-stack
priority, parallel grants to different stacks, response demultiplexing, and
suppression of writes from the read-only compressed fetcher. The
full-mode K arbiter gate checks that addresses with bits 28 and 29 set pass
through its 30-bit port without truncation. The HBM PHY K address port is
parameterized to 30 bits in full mode and remains 28 bits by default. The
640-row stage and four-row-per-cycle attention feed need a banked packed-row
SRAM boundary and measured scheduling before the modeled V4.1 throughput can
be attributed to RTL. This gate establishes the window block write, packed
HBM layout, validity barrier, and read result without making that rate claim.

The optional `BANKED_STAGE=1` mode replaces the large combinational packed
read with four local row banks indexed by absolute position modulo four.
Each bank stores 32 tagged 528-byte rows. A registered bank read followed by
a registered lane rotation returns four consecutive rows in absolute order,
including across positions 127/128, with user and position checks per lane.
Requests accept one four-row beat per clock after the rows have been staged;
single-row requests use the low lane and the same synchronous path. Preloaded
HBM sectors are checked for poisoned FP8 codes and E8M0 scales before a bank
row becomes valid. `python -m tools.rtl_chip_v41x_window_stage4` records the
preloaded read gate and an integrated HBM refill gate in
`results/rtl/chip_v41x_window_stage4.json`. The integrated gate fetches four
rows through the serialized 17-sector HBM port, checks all packed code and
scale bytes, rejects a cross-user read and a poisoned scale. The reported
four-row-per-clock rate is the staged read rate only; the HBM refill schedule
and mixed window/compressed attention rate remain unmeasured.
