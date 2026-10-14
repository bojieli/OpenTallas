# Actual one-PC functional provider

This new integration top composes the original `qkd_ctrl_pc_host` and
`qkd_host_static_pc` from source 94b28c9ce without changing either module.
Compile one static library and instantiate 128 C++ objects (four stacks, 32
runtime PC straps per stack). This is a functional backing model, not physical
qualification or a change to the production architecture.

`build_library.sh /absolute/output` creates
`obj/Vqwen_native_hbm_pc_provider__ALL.a` and its matching header. Link with
Verilator `verilated.cpp` and `verilated_threads.cpp`, C++17 and pthread.
Each instance must have a unique instance name. Drive clocks and input pins,
call `eval()` on each edge, and sample outputs after evaluation. Preserve clocks'
relative phase. Reset both domains low, release resets while clocks run, and
wait at least 128 HBM rising edges before any traffic; this preserves the
original per-PC strap scheduler boot contract. Runtime `pc` must be set before
reset release and remain stable.

ABI (packed bit numbering follows the actual source):

| Pin | Meaning |
|---|---|
| `ck`, `rst_n` | Core clock and active-low core reset |
| `pll_hbm`, `hrst` | HBM clock and active-low HBM reset |
| `pc[4:0]` | Actual controller scheduler strap 0..31 |
| `host_es[287:0]` | Write-only static host command; bit0 valid, bit287 write-data-valid, bit286 write, bank285:281, col280:276, row275:257, data256:1 |
| `host_cr` | Returns one of four initial host queue credits; does not certify memory visibility |
| `host_ack` | Ordered host-owned WR completion, derived from actual controller column WDONE17 through CDC |
| `land_es[287:0]` | Same command ABI; reads use bit287=0/bit286=0 |
| `land_er[260:0]` | fault260, queue-credit259, uncorrectable258, corrected257, read data256:1, read-valid0 |
| `po[327:0]` | PHY row-valid0/op3:1/bank8:4/row27:9; column-valid28/write29/bank34:30/column39:35; actual encoded 288-bit write data327:40 |
| `pi[288:0]` | Actual PHY read codeword288:1 plus valid0; ordered read responses |
| `ci[318:0]`, `co[293:0]` | Original native KV CDC-facing controller ABI, retained verbatim |
| `ki[32:0]`, `ko[32:0]` | Original controller command tap chain, valid0/data32:1 |
| `fi`, `fo` | Original controller sticky fault chain |
| `static_fault`, `completion_fault` | Static ownership/queue and completion CDC fault pins |
| `completion_v`, `completion_we` | Actual ordered static column events; RD events are ordering events, not read-data completion |

The host and landing producers each start with FOUR credits. A valid command
consumes one; replenish only on the corresponding credit pulse. An early credit
is never an ACK. Host writes must carry both write bits. Receive read payloads
only on `land_er[0]`; reads must never be supplied from a golden/output oracle.

The C++ PHY must track ACT/PRE commands and the open row of each of 32 banks.
At each column event, bind `{open_row,bank,column}`. Actual write codeword must
be captured from `po[327:40]` after the controller's five-edge column-to-data
latency (the existing actual-native test captures five HBM edges after the
column). Store all 288 bits from that signal, never re-encode expected data.
Return that stored codeword for reads after the selected PHY read latency,
in column order. Missing addresses should fault in the harness rather than
silently materializing expected operands. Original ECC decode/CDC remains RTL.
The harness owns descriptor/row-quarter metadata and memory keys separately
for every instance. The controller owns JEDEC scheduling and completion.

Build completion only proves a usable library. Full-layer payload exactness,
proper row-quarter ownership, all-return fences, fault mutants, composed timing,
and actual throughput still require the parent multi-model integration.

## Reusable actual PHY backing

`actual_phy.hpp` supplies `qwen_actual_phy::Backing`. Its memory is indexed by
`key(row, bank, col)` and stores nine 32-bit words copied from actual PHY write
pins. No expected payload or encoder is present. `sample_hbm(model)` must run
before the HBM rising `eval()`. Evaluate that edge, assign its returned ten-word
packed `pi`, and evaluate again to reproduce the reference test's nonblocking
PHY-return update. This matters: driving `pi` before that rising eval would
advance read capture by one HBM edge. The adapter retains the row sampled at
column issue, even if ACT/PRE later changes that bank before write capture.

Read latency defaults to **14 HBM edges**, as in the authoritative controller
bench `rtl/test/qwen_host/tb_qkd_ctrl_pc_host.sv`; write-data sampling is exactly
five HBM edges after the WR column. Neither callback fabricates ACKs. Parent
samples actual `host_ack` on core edges and binds its ordered ownership queue.
`written_keys`, `written_at`, `writes`, `reads`, `returns`, `acts`, and `pres`
provide counters for independent identity/visibility checks. Each PC instance
requires its own backing object. Unwritten reads and columns on closed banks
raise observable integration errors.

`run_functional_gate.sh LIBRARY_ROOT OUTPUT` links the actual library and tests
12 distinct 32-byte quarters over three rows, changing bank/column ownership,
then reads through real ECC and CDC. The core has an 833334-fs period with
137000-fs initial phase; HBM has a 1024000-fs period. It starts at PC31 after
160 HBM edges and requires actual WDONE17-or-later host ACKs, independent of
early credits. Actual two-bit read-codeword corruption and a wrong ACK ownership
consumer must cause observed payload and identity assertion failures. This is
one-PC functional proof, not full-layer qualification or timing signoff.

## Actual 128-PC row backend

`row_backend.hpp` defines `RowBackend(context, current_token_position)`. It
instantiates the same compiled PC class 128 times, each with independent backing
and actual controller state. Its group-zero native map follows source94b28c9ce
and sector adapter99e529864: stack=position[8:7], PC=8*quarter+position[2:0],
row=64+layer, with the original native sector-derived bank and column.
`QuarterIdentity` holds epoch/layer/position/kind and dimension-quarter0..3.

- `enqueue_mapped_quarter(identity, data32, observed_physical)` validates the
  actual sector-adapter output coordinates against the identity, then queues a
  host write. `enqueue_quarter` computes the same coordinates directly.
- `pop_write_ack` returns the original quarter identity only after actual
  `host_ack`, the recorded physical write identity and WDONE17 visibility check.
  Feed this event to the sector adapter's ACK inputs. Four internal early host
  credits govern command posting separately; early credits never produce this
  completion event.
- `request_row(identity)` creates four real landing reads. `pop_row` exposes the
  128-byte row only after all four actual `land_er` returns. Current-token reads
  are refused until all four matching epoch/identity writes were acknowledged.
- `declare_prior_quarter(identity, supplied_ECC288)` explicitly seeds a declared
  prior DRAM image. It refuses current/future positions. There is no automatic
  cache oracle. `begin_token` advances position after outstanding operations
  drain; newly written same-identity quarters invalidate prior ACK state.
- `core_edge(high)` and `hbm_edge(high)` implement independent pre-edge sampling,
  actual model evaluation and post-edge updates. Set the shared context's time
  before each call; calls must alternate rising/falling edges. A parent can join
  these hooks with other RTL models. Alternatively `next_event_fs` and
  `advance_one_event` provide the reference 833334-fs core, 1024000-fs HBM
  scheduler. All controllers receive reset release at HBM edge8 and traffic
  starts no earlier than edge160.

The targeted gate uses 24 actual current-token writes/ACKs for K and V at
layers0/17/35, position8191. A separately declared 128-quarter prior image
exercises actual read traffic through every one of the 128 controllers. In
all it reads152 quarters and assembles38 rows, with4096 independent mapping
checks. Prior preload uses the gate's explicit ECC image initializer; current
payloads always take the real RTL host-write path. Physical codeword corruption
and incorrect sector-adapter coordinates produce observed failures. This tests
backend integration and addresses, not production kernel execution or cost.

For immutable raw FP8 prior-cache inputs, use
`enqueue_prior_quarter_via_actual_controller(identity, raw_data32)`. It requires
position less than the current token and uses the identical real
host_es→controller ECC→PHY write→WDONE ACK path as current writes. No C++ encoder
is involved. `row_is_committed` now requires all four matching actual write ACKs,
or (for prior rows only) all four explicitly declared ECC preload quarters.
Uninitialized, partially preloaded and pending prior rows cannot be read.
The full-layer parent should initialize raw prior payloads through this method;
the targeted gate also retains separately declared prior DRAM image coverage.
