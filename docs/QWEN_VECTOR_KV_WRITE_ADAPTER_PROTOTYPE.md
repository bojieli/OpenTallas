# Qwen vector KV write adapter prototype

The shipped vector stream unit emits up to `SW=8` or `SW=16` KV element writes
per cycle. The scalar HBM streamer accepts one write per cycle and its K tail
has one write port per tile parity, so it cannot be connected to the vector
core without preserving all lanes. `ot_hdc_qwen_kv_write_adapter.sv` is an
isolated write-side prototype for that interface.

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
is in flight. The adapter accepts vector FP8 bytes; conversion from the
core's BF16-valued stream port must follow the scalar numeric contract.

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

This is not yet an integrated token path. The remaining gates are the
BF16-to-FP8 numeric contract, SRAM macro/BIST and read-before-write implementation,
bounded-buffer throughput under arbitrary HBM stalls, tail flush scheduling,
HBM read/write ordering, full-context token campaign, and physical route.
The RTL parameters `AW`, `LOG_TW`, and `V0_ELEMENT` must be set from the
selected model layout; the bench uses a reduced layout.
