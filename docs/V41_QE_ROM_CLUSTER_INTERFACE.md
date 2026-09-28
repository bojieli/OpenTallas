# V4.1 QE ROM-to-cluster interface gate

The shipped-shape layer-0 rank-0 checkpoint has a source-pinned logical QE image
in `results/rtl/hdc_v41x_fullshape_qe_stream_200k_l0_rank0.json`. It is an
address/readback gate, not a full-die bank map or throughput measurement.

## Two distinct QE ports

The executable core's `ot_hdc_v41_qe` consumes one 16-lane × 272-bit word per
cycle. Each lane holds 32 one-byte E4M3 codes or zero-extended E2M1 nibble
codes, then a signed 16-bit exponent. The logical address is
`base + (round * nb + block) * 8 + slot`; a routed expert adds its absolute ID
times its family stride. The checkpoint packer checks all 25 token-selected
matrices, including six absolute routed IDs and all final-tile padding. Its
FP8 physical word is 17 × 32-byte sectors; an FP4 word is 9 sectors and must
be expanded locally to the 544-byte port. `ot_hdc_v41x_qe_sector_expand`
implements that bounded, combinational one-word conversion, with a missing-
sector fault. The real-checkpoint RTL test covers both formats. The macro-Q
to QE path through the converter has no routed timing result.

The proposed physical partition `ot_chip_v41x_ptile` instead instantiates
`ot_hdc_v41x_wgt_qtile`: eight separate 264-bit weight lanes per group, each
fed by one `ot_rom_8192x266_m8` macro. The module passes only `rq_a[12:0]`
to each macro, although the engine generates 20-bit addresses; its source
comment says the 8192-depth macro covers one bank, not the tile's full weight
share. All groups receive the same descriptor but can hold different bank
contents. There is no committed compiler transform from the core's 16 × 272
stream words to those lane-bank contents, no table assigning every matrix
and absolute expert slot to physical banks, and no connected 48-tile schedule.
The stream expansion gate cannot validate this physical partition.
The current 266-bit qtile macro also allocates a full-width lane for FP4; the
2.127 GB packed-image figure cannot be credited to that macro implementation
without a narrow FP4 bank or a proved two-packed-lanes-per-macro mapping.

## Port and capacity accounting

`docs/ARCH_SPEC_V41.md` states 264,960 quantized and 41,664 BF16 MACs per
cycle, with 349 KB/cycle of ROM read. The 348,288 B/cycle value is useful
weight bytes: one FP8 byte per quantized MAC plus two BF16 bytes per other
MAC. At the physical partition's port widths, matching those lane counts
requires 1,035 quantized groups (264,960 / 256) and 651 BF16 groups
(41,664 / 64). Their macro outputs total **453,684 B/cycle**:

| Port | Groups | Bytes per group per cycle | Physical bytes/cycle |
| --- | ---: | ---: | ---: |
| QE: 8 × 266-bit macro | 1,035 | 266 | 275,310 |
| ME: 8 × 274-bit macro | 651 | 274 | 178,374 |
| Total | | | 453,684 |

The currently described 48 physical tiles at their default `NQ=2, NM=0`
contain just 96 QE groups, or 24,576 quantized MACs/cycle. Scaling the fixed
8192-word macro count to the modeled groups allocates 8,280 QE and 5,208 ME
macros, 3.717 GB of *raw macro bits*. That exceeds the model's 2.714 GB of
useful checkpoint payload, but does not alone prove an area failure: the
ASAP7 macro views are denser than the model's N5 ROM assumption, and the raw
macro bodies sum to about 199 mm² before placement, ports and wires. It does
show that depth waste, bank ownership and area need an explicit joint ledger.

The source-pinned stream layout reserves 3.912 GB if every FP4 word is stored
expanded. Its packed FP4 image plus the older ME/HE/CROM region ledger
reserves 2.127 GB, within the 2.714 GB payload budget, but requires the
local expansion converter. These are byte-image facts, not proof that enough
simultaneous local ROM reads or a macro floorplan exists.

## Acceptance needed before using the 349 KB/cycle model point

1. Emit one immutable checkpoint-to-program-to-bank manifest: each logical
   QE/ME word, matrix and expert ID has a die, cluster, macro, row, lane and
   port owner. The map must reject unmapped, duplicate and aliased addresses.
2. Run the exact emitted layer-0 program against those bank images, including
   dense/shared/routed expert switches and back-to-back descriptors. Check
   per-port conflicts, physical and useful read bytes, converter cycles,
   activation SRAM ports, queues, credit stalls and exact output bits.
3. Route a complete cluster with the real macro port widths, expansion path,
   activation broadcast and result return. Then compose the finite number
   of characterized clusters, charge their registered links and measure the
   attainable total service. Reprice the token model from that schedule and
   achieved frequency if service differs from the assumed point.

Until those gates pass, the pooled QE/ME width and 349 KB/cycle read rate are
design-point assumptions. The local converter establishes only packed-word
functional correctness at the executable core's QE port.
