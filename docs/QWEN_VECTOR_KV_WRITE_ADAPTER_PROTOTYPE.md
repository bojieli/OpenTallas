# Qwen vector KV write adapter prototype

The shipped vector stream unit emits up to `SW=8` or `SW=16` KV element writes
per cycle. The scalar HBM streamer accepts one write per cycle and its K tail
has one write port per tile parity, so it cannot be connected to the vector
core without preserving all lanes. `ot_hdc_qwen_kv_write_adapter.sv` provides
the bank and sector datapath for that interface.

K addresses are dimension-major within a 16-position tile. Adjacent stream
lanes therefore address distinct K words in the **same** tile parity. The
prototype stripes each parity across `SW` one-write banks: bank `word mod SW`,
row `{layer/head, dimension / SW}`. Tile bits are deliberately omitted from
the row, so the two parities hold only the open and previous tiles. Every
accepted vector beat writes its active banks together; duplicate-bank beats
raise `fault` and are not silently serialized. The word outputs are 16 FP8
bytes with a lane mask. A production macro wrapper must provide this banked
read/write organization and BIST.

V elements and completed K tail words enter one 32-byte sector assembler.
A full sector is written to HBM directly. A partial sector is read from HBM,
merged by byte mask, then written as a full 32-byte sector. `in_ready` and
`fl_ready` stay low while a different sector is pending or a memory request
is in flight. The adapter accepts vector FP8 bytes. The synthesizable
`ot_hdc_qwen_kv_vector_bridge.sv` buffers core output and converts its FP32
encoded values with the shared E4M3 ingest quantizer. Its 128-beat FIFO holds
one full shipped Qwen KV instruction (8 KV heads × 128 dimensions) at SW8 or
SW16 even when HBM refuses every write. The core's optional
`KV_VEC_WRITE_BRIDGE` mode waits for stream-unit idle and bridge drain before
starting another stream instruction or retiring the token.

`ot_hdc_qwen_kv_tail_read_mux.sv` exposes one synchronous read port per bank.
The current KV streamer can request at most one tail word from each parity in
a cycle, so those two requests address separate banks. A registered bank
select lines up with the macro's one-cycle read result. The reduced bench
checks both parities in the same cycle and the layer/head row map. The actual
macro wrapper and read-before-write behavior are still unimplemented.

Run `python3 tools/run_qwen_kv_write_adapter_campaign.py` to regenerate the
source-pinned reduced record in
`results/rtl/qwen_kv_write_adapter_prototype.json`. The Icarus benches cover
SW8 and SW16 tail-bank dispatch/read mux, sparse masks, sector-switch backpressure,
full V and K-flush sectors, and a partial-sector read/modify/write. Python
tests compare the address equations directly against `Layout.k_elem` and
`Layout.v_elem` from the shipped program source.

`results/rtl/qwen_kv_system_bridge_boundaries.json` records focused SW8/SW16
tests holding off HBM writes for a full 1,024-element V instruction. Both
drain without overflow. A separate test checks logical 16-byte reads and
partial writes through `ot_hdc_qwen_hbm_sector_bridge.sv` into 32-byte sectors.
`results/rtl/hdc_qwen_vector_bridge_token_g4.json` records a passing G4/SW8
vector-core token: logits, vector memory and KV elements match the ISA, and
every core-emitted KV byte matches the banked K tail or assembled V sector.
Compute reads still use the direct behavioral KV array in this token gate.

`results/rtl/hdc_qwen_ingest_to_two_tokens_physical.json` records the packed
ingest image feeding a 32-byte physical-sector HBM model for two scalar tokens
across K tail tile reuse. Terminal logits, vector memory and KV are exact.
The sector shim serializes requests to preserve ordering, so this is a
functional proof and does not measure production HBM throughput.

The remaining vector-core connection is the read side: the banked tail read
mux and sector shim must feed the KV streamer with prefetch ordering. Physical
bank macros need read-before-write behavior, BIST and a flush controller. The
FIFO and drain schedule prove no write loss for one instruction under
arbitrary stalls; they serialize stream instructions and do not establish
shipped throughput or physical route. Parameters `AW`, `LOG_TW`, and
`V0_ELEMENT` must come from the selected model layout.
