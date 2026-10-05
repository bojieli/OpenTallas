# Candidate full-shape QE HBM fetch descriptor

This is the root-approved standalone candidate ABI. The tile, die, their list
ROMs and full-shape image emission have **not** migrated. Do not enable it in a
production comparator by widening a port alone.

`ot_hdc_qstream.FULL_SHAPE=1` explicitly selects a 160-bit fetch-list word;
153 bits are used. Software uses `encode_list(entries, profile="full_shape")`.
Reduced mode remains the default, with the existing 128-bit bit positions.

| Field | Reduced | Full-shape | Units |
|---|---|---|---|
| hbm | 23:0 | 29:0 | 32-byte sectors relative to cfg_base |
| rom | 47:24 | 59:30 | QE logical words |
| n | 63:48 | 80:60 | logical word count; zero terminates |
| fp4 | 64 | 81 | format |
| pred | 66:65 | 83:82 | predicate |
| ind | 67 | 84 | indexed flag |
| ibase | 91:68 | 114:85 | vector-memory element address |
| istride | 115:92 | 144:115 | logical words per expert |
| grp | 123:116 | 152:145 | release group |
| reserved | 127:124 | 159:153 | zero |

Full mode defaults AW=30, HAW=30, NW=21. Entry count, walker index, operation
FIFO count, and consumer index are 21 bits; the rate product widens to 48 bits.
All software fields reject negative and overflowing values. Full RTL rejects
nonzero reserved bits, overflowing cfg_base + sector offset, and direct or
indexed ROM/HBM spans before a request can issue. Intermediate indirect
arithmetic is 96 bits so even a malformed 32-bit expert ID cannot wrap before
the check. The fault reuses fault_why[3] (descriptor/uncoverable); no new port.

The full profile is an addressability envelope, not an approved full-die
allocation. The selected L0 layout needs fewer bits in several fields, but
multi-layer/state placement is unresolved. 30 sector bits represent 32 GiB;
if the root-owned region map needs more, this ABI requires explicit revision.
The region allocator must verify extent, expert count and packed stride; the
walker checks representability, not ownership or tensor semantics.

## Acceptance

`tests/test_hdc_qstream_full_descriptor.py` checks the real program generator's
encoder, every field overflow, reduced legacy bit packing, and actual RTL
walker dispatch with count65,536 and high ROM/HBM/VM addresses. Direct and
indirect requests agree with software; reserved bits, direct base/span overflow
and expert stride overflow fault before requests. This bounded test checks
walker/FIFO count retention; it does not consume65,536 QE words or verify the
full matrix arithmetic or shared service.

## Migration gates

1. Root approves complete physical region map and address units.
2. Tile/die list ROM width, qstream parameters and request widths migrate together.
3. Full emitter writes40 hex digits/entry with profile metadata and matching
   source hashes; old128-bit images must not silently load into full mode.
4. Execute real full-shape QE operations under bounded HBM and backpressure,
   preserving golden arithmetic and checking every supplied weight word.

The existing reduced writer continues to emit32 hex digits and the reduced
profile. No full comparator throughput claim follows from this ABI test.
