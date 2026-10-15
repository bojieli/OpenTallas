# HBM Engram: eight-home structural partition candidate

The actual released tables contain 384,006,168 and 384,016,682 rows. Each HBM row is 288 bytes, preserving 256 code bytes, eight scale bytes and 24 padding bytes. Four contiguous homes per layer require up to 27,649,201,248 bytes per stack, exceeding the hardware's 22,500,000,000-byte stack capacity and overlapping the reserved data window beginning at 20 GiB. This is a capacity defect; routing another instance of the four-home organization cannot fix it.

The new source contract partitions each table across eight contiguous homes: layer 1 on ranks 0–7 and layer 14 on ranks 8–15. No rows or table bits are dropped or recompressed. The exact sixteen half-open intervals in `allocation_manifest.json` cover the released rows once each. Maximum home extent is 13,824,600,768 bytes on stack 3, below the reserved 20 GiB data window. This proves these intervals fit; all other live allocations still require H-DIE's allocator-book collision audit.

`tools/hbm_engram_partition.py` owns homes, interval mapping and bounded metadata. The actual `hgi_sim.ds_native` compiler/image producer now uses that shared eight-home mapping and a 232-word host table (24 gather IDs, counts at words 32–39, eight arrays of at most 24 local row IDs beginning at word 40). Its historical checkpoint-backed simulator reader is updated consistently and checks non-home reads and out-of-extent row IDs. That callback remains a diagnostic, not an on-chip implementation.

The new actual RTL `ot_hbm_engram_home_dispatch` takes a statically reserved stream of 24 global row IDs, maps each through constant interval comparisons, and emits registered destination rank, stack-3 address, local row, staging slot and gather list ID. It has no ready, arbitration, demand issue or credit mechanism. A missing input in any reserved slot or an out-of-range row faults immediately without extending execution. The 24 rows may all belong to one home; the per-home slot counters support that full bound. `ot_hbm_engram_hash_home_native` instantiates the existing released 12-stage hash RTL and two dispatchers. It computes both layers from the same actual hash history and emits two simultaneous descriptor streams; it does not hash the token twice or substitute precomputed rows.

Evidence:

- `partition_receipt.json`: actual encoded/compiler contracts across all 96 ranks and both layers; 6,576 actual RTL descriptors across 274 tokens, including every home boundary and 24 rows on each single home. Missing-slot and invalid-row faults are checked. A rank-offset DUT mutant fails on the first descriptor. Terminal unit `oth-ubuntu-1376580-1792053830`, 2 GiB/one thread, EPYC4.
- `hash_home_receipt.json`: actual released hash to both eight-home descriptor streams, 64 tokens/3,072 descriptors, repeated sequence resets and vocabulary endpoints. Every descriptor and exact age is checked: first request at age 13 after the compressed-token input edge, last request and done at age 36. Rank-offset DUT mutant fails. Terminal unit `oth-ubuntu-1380983-1792053892`, 4 GiB/one thread, EPYC4. These are functional common-clock ages; physical insertion and registered seam delivery remain unproved.
- Initial units 1375112 and 1375944 exposed a testbench scheduling error: the stimulus left an empty reserved row edge after `start`. The DUT correctly faulted and advanced the fixed calendar. Corrected stimulus begins row 0 on the immediate next edge; both failed logs remain on the remote proof directory. No DUT calendar or fault threshold was relaxed.

Concrete costs and remaining work:

- Metadata grows 144 → 232 U32 words, or 18 → 29 32-byte sectors. That is +352 bytes/rank and +11 metadata sectors/layer when the host-table interface is used. Existing VM addresses after EGID move through the compiler's allocation; stale images/descriptors must be regenerated.
- Each home retains a worst-case 24-row staging requirement (6,912 bytes). Doubling the home count adds active home endpoints, not more Engram data: total released tables remain 221,190,580,800 bytes. The collectives still gather exactly 24 selected rows/layer and return them in the original hash-column order.
- The actual hash/native serializer needs 1,392 held row bits plus fixed counters/control and two descriptor-register sets. No physical area is inferred from this declared-storage count. The shipped hash itself is existing hardware; its placement/root partition still needs a real view and clock proof.
- **Open:** raw-token mapped/context producer hookup; actual dispatcher → DMA request/return → staging visibility → ROW_GATHER → code/scale decode → native consumer composition; full compiler static reservations and end-to-end performance measurement; physical slots/pins, all incident wiring, clock insertion, TT/FF/DRC.
- The candidate changes no immutable throughput target and claims no full-layer/full-token or physical qualification. H-DIE owns allocator-book validation/adoption. Geometry owns coherent system placement. A capacity fit cannot establish transport/calendar/physical closure.

Reproduce from a source snapshot through the fleet admission tool:

```sh
PYTHONPATH=tools python3 tools/hbm_engram_partition_gate.py --out proof
PYTHONPATH=tools python3 tools/hbm_engram_hash_home_gate.py --out hash_proof
```

Actual Yosys 0.52 `proc; opt; memory_map; opt` census (`dispatch_census_receipt.json`, terminal unit `oth-ubuntu-1389084-1792053962`) retains 150 register bits per dispatcher. This is an optimized logical-storage count, excluding the hash and serializer, and does not establish physical area or clock delivery. Both native streams use two such dispatchers.

## Actual SRAM staging and eight-scale decode

`ot_hbm_engram_row_store_decode` implements 24 complete 288-byte rows with two real 128×256 ASAP7 SRAM macros. Input address/data are registered before the macro, macro outputs are captured, and the outgoing raw/decode face is registered. A read reserved at edge t returns at t+3, accepting one request each edge. Home staging uses DECODE_ENABLE=0 and may read sectors in any order; consumer DECODE_ENABLE=1 reads scale sector8 first and then code sectors0–7, using each block's matching scale. No ready/credit mechanism is present. Explicit epoch_begin invalidates row-visibility metadata without resetting SRAM or upstream hash history. Duplicate writes, reads of unwritten words and invalid row/sector addresses fault.

`external_rows/` contains 48 actual released-checkpoint rows selected by the real hash contract from compressed CID history [17,999,5543,99091]. Each original code/scale region is pinned by file/header/absolute offset/SHA; only these original bytes may supply the external HBM model. BF16 expectations are comparison-only. This is a valid component input sequence, not a claim of replaying the canonical 1M-token programme.

Terminal unit `oth-ubuntu-1500123-1792055383`: both SRAM epochs, all432 raw sectors,384 decoded blocks/12,288 BF16 elements, exact read age3, epoch reuse without global reset and unwritten retained-old-epoch fault all pass. Actual DUT mutant reusing scale0 for every block fails. No DMA/collective/hash composition or physical qualification is inferred. Initial simulator elaboration rejected a generated macro-output connection; two explicit fixed bank instances preserve the actual two-macro architecture and pass. The controller and full operation join are tracked separately.
