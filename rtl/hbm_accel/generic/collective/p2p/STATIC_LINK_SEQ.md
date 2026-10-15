# Static full-sequence native HBM link

`ot_hgi_coll_static_link_seq` is distinct from the frozen596-bit link. Its
compiler API uses `wr_seq`, `rd_seq`, and `rx_expect_seq` as16-bit monotonically
increasing reservations from0 through65535 in one8-bit epoch. Physical SRAM
addresses are the low6bits. Every read consumes its written publication; the
native ownership guard rejects reuse until the old read pipeline clears.
No acknowledgement, credit or received frame chooses an issue edge.

The protected stored word is `{sequence16,payload545}`. The native19-bit
header andCRC32 produce612wire bits. Both full TX identity and captured RX
identity are checked before publication. TX read at n reaches pins at n+3;
RX pin capture at n publishes at n+1. All17-bit reservation counters saturate
after65536frames, refusing16-bit wrap; an explicit drained epoch restart is
required. Epoch abort/retry_requested only signal exceptional failure.
Actual recovery, retransmission and the physical package are unimplemented.

`tools/uarch_model_hcoll_static_seq.py` sizes this composition before build.
The native top hardcodes137-bit storage leaves, too narrow for561bits;
therefore this wrapper composes the unchanged source-pinned native controller
atFW561 with four unchanged native SRAM leaves atW141. Each leaf still
instantiates the real64x512 macro; padded storage is564bits. The controller,
parallelCRC and SRAM leaf source blobs are pinned by`static_link_sources.json`.
There is no Qwen source change and no local behavioral replacement SRAM.
W141/controller physical timing and channel capacity are unqualified.
Wire width increases16/596=2.685%; codec latency and SRAM macro count stay fixed.

Run`bash run_static_link_seq_bench.sh`. The fullwidth bidirectional bench
streams1024frames per direction at one per cycle, same epoch, with96 fixed
physical-flight edges. This crosses16physical-slot laps while flight exceeds
the64-slot count. Its independent word and serialCRC scoreboards check2048
payloads, exact TX3/RX1 publication edges, and no faults. Mutants cover dataCRC,
wrong expected full sequence, native store corruption, late/missing arrival,
missing publication, overwrite of unconsumed slots, missing observed write,
CRC-valid previous-lap replay with the same low6slot, unpublished read, and
CRC-valid stale full sequence in SRAM. Overflow is a separately labelled
boundary test that seeds reservation counters near65536, then uses real RTL
edges to check legal65534/65535 and refused wrap; it does not claim a65536-frame
endurance simulation. No PHY/replay or physical closure claim follows.
