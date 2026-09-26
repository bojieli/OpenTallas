# Host interface and runtime

This is the host-interface workstream of the
[tape-out readiness plan](TOKEN_PIPELINE_OPTIMIZATION_PLAN.md) (section 6). It
covers how a host talks to each chip and how an ordinary client reaches it:

- a host command and completion interface in RTL;
- a runtime that drives the RTL simulation;
- an OpenAI-compatible HTTP endpoint that uses each model's Hugging Face
  tokenizer;
- an end-to-end test whose generated tokens must equal the decode campaigns'.

The same interface block, runtime and endpoint serve all three
architectures. Only the engine behind the interface changes.

## Per-architecture status

| Architecture | Target | Engine behind the host interface | Users | Tokens through the endpoint path | Status |
|---|---|---|---|---|---|
| Qwen3-8B ROM reticle | `qwen3-rom` | one `ot_hdc_core`; the KV SRAM has one slice per user | 16 contexts, steps interleaved | 1073, 382, 93 for three concurrent users; also through `/v1/chat/completions`, streamed and plain, and from the `openai` Python client | done |
| HBM comparator | `qwen3-hbm` | `ot_hdc_core` with `KV_HBM=1`, `ot_hdc_kv_stream` and the HBM timing model | one user at a time, engine cleared between users | 1073, 382, 93 for two users in turn | done for KV in HBM; weights-in-HBM core (`rtl/hdc/hbm`) not yet on main |
| DeepSeek-V4.1 ROM array | `v41-rom` | `ot_hdc_core_v41` (reduced V4.1 vehicle) | one user at a time, engine cleared between users | 3118, 2400, 318 | done for one package (one die) |
| ROM array (package fabric) | `qwen3-array` | package 0 (`ot_rom_pkg_ctrl`, SOURCE) of a four-package layer-per-package array over `ot_rom_pkg_link` | a batch of up to 16 users through the package controllers' user contexts | 1073, 382, 93 for four users | done for the array machinery; the only multi-package RTL array carries the reduced Qwen3 layer pipeline |

Multi-package V4.1 sessions are the gap. The host interface fronts the
package controller (`qwen3-array`), and the package controller is the same
for any model. But no RTL array carries V4.1 layers:
`tools/hdc_program_v41.py` has no `--stages` split, so the V4.1 core runs as
one package. When a staged V4.1 program exists, it runs behind the same
`MODE=1` host interface without change.

## 1. The host interface: `rtl/host/ot_host_if.sv`

The block is synthesizable. It sits between a PCIe-style host port and the
decode engine.

**Host side.** A register BAR on an AXI4-Lite slave, and an AXI4 master for
DMA to host memory. The master issues single 64-bit beats: the traffic a PCIe
endpoint's bridge presents. An interrupt is a level (`irq`, the INTx model)
and, when enabled, an MSI: a DMA write of `MSI_DATA` to `MSI_ADDR`, which is
how a PCIe function signals a message-signalled interrupt.

**Rings in host memory**, as in NVMe:

- *Submission queue.* 32-byte descriptors. The host writes a descriptor and
  rings the `SQ_TAIL` doorbell. The chip fetches the descriptor and then the
  prompt it points to, and advances `SQ_HEAD`.
- *Completion queue.* 16-byte entries, written by the chip. There is one
  entry per generated token, so the completion queue is the token stream.
  The last entry of a request carries its stop status. A phase bit flips on
  every wrap, so the host finds new entries without reading a register. The
  host returns entries through the `CQ_HEAD` doorbell. The chip never
  overwrites an entry the host has not returned; it counts the cycles it
  waits for room.

**Descriptor fields:**

- opcode;
- flags: greedy is required, and stop-at-EOS is optional;
- a 16-bit tag;
- prompt length and maximum new tokens;
- the host address of the prompt (16-bit token ids);
- the user context, which is a slot;
- two EOS ids.

**Completion fields:**

- phase and kind (token, last token, or error);
- status: `ok`, `eos`, `length`, `bad_opcode`, `unsupported_sampling`,
  `slot_unavailable`, `bad_length`, `engine_fault` or `dma_error`;
- slot, tag, position and token;
- the step's cycles and the number of tokens generated so far.

**Fail-closed checks.** A descriptor is refused with an error completion
before it touches a slot if:

- the greedy flag is missing;
- the slot is out of range or busy;
- the prompt is empty or larger than the prompt buffer;
- prompt plus generation would run past the user context's positions.

**User contexts.** There are 16 slots, the package controller's `MAXU`. A
slot holds:

- the request's tag and lengths;
- its next position and the fed-back token;
- its EOS ids and its generated count.

The prompt is DMA'd once into the prompt buffer, an external 1R1W SRAM
addressed by {slot, position}. Like every memory of the decode cores, that
SRAM sits outside the block.

**Engines.** `MODE` selects the engine type; `ENG_CTX` says how many user
contexts the engine holds.

- `MODE=0` (one decode core). The block schedules every decode step of every
  running slot through the core's start/done handshake, round robin.
  - Prompt positions take their token from the prompt buffer. Generated
    positions feed back the core's argmax.
  - `kv_base` (slot × KV words per user) selects the running user's KV slice.
  - With `ENG_CTX=1`, the engine keeps one user's state beyond the KV cache.
    The V4.1 core does: persistent vector-memory regions and the Engram hash
    history. So does the HBM streamer's KV tail SRAM. A slot then runs to
    completion, and before the next slot the block raises
    `eng_clr_req`/`eng_clr_ack`. The simulation tops reset the engine and
    zero its user state; in silicon, that is the memories' clear or BIST
    initialisation engine.
- `MODE=1` (the SOURCE package of a ROM array). `ot_rom_pkg_ctrl` schedules
  its users itself, with one prompt length and one generation length. So the
  host starts slots 0..n-1 together by writing n to `BATCH_GO`.
  - The block checks that those slots are loaded with equal lengths.
  - It resets the array and sets the controller's `cfg_users`,
    `cfg_prompt_len` and `cfg_gen_len`.
  - It serves the controller's prompt reads from the prompt buffer.
  - It turns the controller's reduced-token stream into completion entries.

  Using the package controller unmodified keeps its routed record current.
  Per-user lengths in the array would need a host issue port on the
  controller.

**Counters** (registers):

- cycles and engine busy cycles, 64-bit;
- tokens, steps and completed requests;
- MSIs, DMA read beats and DMA write beats;
- cycles stalled on a full completion queue;
- per slot: state, position, tag and generated count.

The register map and both formats are written out at the top of the RTL
file.

### Physical

`ot_host_if` in its reticle configuration (`MODE=0`, 16 slots) was routed on
ASAP7 with `tools/run_abi3_physical.py`: 0.9 ns target, block I/O
false-pathed, synth and place-and-route.

- Routed Fmax: **1,137.4 MHz**. <!-- figure: 1137.4 src="results/physical_abi3/asap7/host/ot_host_if/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="ot_host_if routed fmax" -->
  Setup and hold are met at 0.9 ns, with 20.8 ps of setup slack. <!-- figure: 20.8 src="results/physical_abi3/asap7/host/ot_host_if/physical.json#place_and_route.metrics.setup_wns_ns" scale="1000" name="ot_host_if routed setup slack, ps" -->
- Standard-cell area: about 4,314 µm². <!-- figure: 4314 src="results/physical_abi3/asap7/host/ot_host_if/physical.json#place_and_route.metrics.standard_cell_area_um2" name="ot_host_if standard-cell area" -->
  Of that, 5,085 cells are flip-flops. <!-- figure: 5085 src="results/physical_abi3/asap7/host/ot_host_if/physical.json#place_and_route.metrics.sequential_cell_count" name="ot_host_if flip-flops" -->
  Most of them hold the slot contexts and the completion-event queue.
- DRC: zero.
- Acceptance: `not_met`. Timing closes, but 15 max-slew violations remain. <!-- figure: 15 src="results/physical_abi3/asap7/host/ot_host_if/physical.json#place_and_route.metrics.max_slew_violations" name="ot_host_if max-slew violations" -->
  The router record cleared the same kind of violation with
  `--slew-margin-percent 40` (docs/ROM_ARRAY_FABRIC_RTL.md). That rerun was
  not made here; this workstream allowed one place-and-route run.

The routed source is the revision at commit `a8186d18`. The later fix to the
end of a ROM-array batch changes only `MODE=1` logic. At `MODE=0`, the
Yosys netlists of the two revisions are byte-identical
(`tools/host_if_routed_revision_identity.py`,
`results/physical_abi3/asap7/host/ot_host_if/routed_revision_identity.json`),
so the record still routes this circuit.

## 2. The simulation: tops and the host bridge

Each architecture has a top that puts `ot_host_if` in front of its engine,
with behavioural memories loaded from the program/ROM images:

| Top | Engine |
|---|---|
| `rtl/test/tb_host_qwen.sv` | `ot_hdc_core`; the KV SRAM has 16 slices |
| `rtl/test/tb_host_hbm.sv` | `ot_hdc_core` with `KV_HBM=1`, `ot_hdc_kv_stream`, window and tail SRAMs, and `ot_hdc_hbm_model` |
| `rtl/test/tb_host_v41.sv` | `ot_hdc_core_v41` |
| `rtl/test/tb_host_array.sv` | four packages, each one `ot_hdc_core` and one `ot_rom_pkg_ctrl`, in a point-to-point `ot_rom_pkg_link` ring |

All four expose the same host ports (`rtl/test/tb_host_ports.svh`).

`rtl/test/host_bridge_harness.cpp` is the host side of the chip. It plays
four roles:

- *Host memory.* A file mapped into both the simulator and the runtime, so
  the runtime builds rings and prompts in it and reads completions from it,
  as a driver does in pinned DMA memory.
- *The DMA target.* Each access completes a fixed number of chip cycles after
  it is accepted: 64 by default, standing in for the PCIe round trip.
- *The interrupt controller.* A write at or above `0xFEE00000` is an MSI.
- *The CPU.* It performs the register accesses.

The runtime sends it line commands on a pipe: a register write, a register
read, and "clock until an MSI or n cycles". Time advances only while the
runtime waits on the device, so every simulated cycle is a chip cycle.

## 3. The runtime: `runtime/hdc`

| Module | Role |
|---|---|
| `targets.py` | The four targets: top, sources, image generator, tokenizer, context length, and the physical records that bound the modelled clock |
| `build.py` | Verilates the chip and generates the model's program/ROM images (`tools/hdc_program.py`, `tools/hdc_program_v41.py`, `--stages` for the array). Both are cached under `build/hdc_host/`, keyed by the hash of their inputs |
| `device.py` | Starts the simulated chip, maps host memory, and gives register access and interrupt waits |
| `driver.py` | What a kernel driver owns: ring layout, descriptor encoding, doorbells, MSI programming, phase-bit completion polling |
| `runtime.py` | `HdcRuntime`: sessions and slots, one pump thread that owns the device, per-request token streams, counters |
| `tokenizer.py` | The model's Hugging Face tokenizer and chat template |
| `server.py` | The OpenAI-compatible endpoint |
| `__main__.py` | The command line |

**Scheduling** follows the engine:

- *Step engines.* A request takes any free slot and is submitted at once. The
  chip either interleaves the running slots or, for one-context engines, runs
  them in turn.
- *The array.* The runtime groups waiting requests of equal lengths into
  slots 0..n-1 and starts them with `BATCH_GO`.

**Tokenizers.** Only `tokenizer.json` is read from `~/.cache/huggingface`;
no weights. The reduced vehicles fold the shipped tokenizer's ids into their
vocabulary by `id % vocab`, the rule that derived the reduced workloads from
the governed ones. A generated reduced id is decoded as the shipped token
with that id.

- Qwen3 uses the Qwen3-8B tokenizer (vocabulary 4096).
- V4.1 uses the DeepSeek-V4.1-Flash tokenizer (vocabulary 4040).

The chat templates render with thinking disabled, as the governed workloads
do. "Reply with OK." then encodes to exactly the governed prompts:
`TA-QW-REDUCED-EOS-1` (16 ids) and `TA-DS41-REDUCED-EOS-1` (8 ids).

**Modelled clock.** Seconds and tokens/s are chip cycles at the modelled
clock. The cores are not routed as whole blocks, so the modelled clock is
the slowest routed block among each core's records:

- the Qwen3 cores: the matrix engine, `ot_hdc_matvec`, at 1,098.6 MHz;
- the V4.1 core: `ot_hdc_softplus`, at 1,033.9 MHz.

The Sinkhorn unit (151.9 MHz) is excluded: it is clocked once every seven
core cycles as a multicycle path (`ot_hdc_sinkhorn_mc`).

## 4. The endpoint and the CLI

```
python3 -m runtime.hdc targets
python3 -m runtime.hdc generate --target qwen3-rom --chat "Reply with OK."
python3 -m runtime.hdc serve --target qwen3-rom --target v41-rom --port 8000
```

Routes:

- `GET /v1/models`
- `POST /v1/completions` (prompt as text or token ids)
- `POST /v1/chat/completions`
- `GET /v1/counters`

`stream: true` answers as server-sent events and ends with `data: [DONE]`.
Each event carries one token the chip wrote to its completion queue. The
model id is `<model>@<target>`, for example `qwen3-reduced-v1@qwen3-rom`.

The chips decode greedily and bit-exactly. A request asking for sampling
(`temperature` > 0, `top_p` < 1, `n` > 1) is refused with HTTP 400 rather
than served greedily without saying so.

Every response carries an `opentallas` object:

- target and token ids;
- chip cycles and per-step cycles;
- the modelled clock, seconds and tokens/s.

A standard client works unchanged:

```
curl -N http://127.0.0.1:8000/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-reduced-v1@qwen3-rom","messages":[{"role":"user","content":"Reply with OK."}],"stream":true}'
```

```python
import openai
c = openai.OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="unused")
for ev in c.chat.completions.create(model="qwen3-reduced-v1@qwen3-rom", stream=True,
                                     messages=[{"role": "user", "content": "Reply with OK."}]):
    print(ev.choices[0].delta.content or "", end="")
```

### Demo

This is a streamed request through the endpoint into the Verilated Qwen3
reticle. The server was started with `python3 -m runtime.hdc serve --target qwen3-rom --port 8765`.
Chunks are abridged:

```
$ curl -sN http://127.0.0.1:8765/v1/chat/completions -H 'Content-Type: application/json' \
    -d '{"model":"qwen3-reduced-v1@qwen3-rom","messages":[{"role":"user","content":"Reply with OK."}],"stream":true}'
data: {... "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": null}]}
data: {... "choices": [{"index": 0, "delta": {"content": "ask"}, ...}], "opentallas": {"token_id": 1073}}
data: {... "choices": [{"index": 0, "delta": {"content": ".\n\n"}, ...}], "opentallas": {"token_id": 382}}
data: {... "choices": [{"index": 0, "delta": {}, ...}], "opentallas": {"token_id": 93}}
data: {... "finish_reason": "stop"}], "usage": {"prompt_tokens": 16, "completion_tokens": 3, "total_tokens": 19},
       "opentallas": {"token_ids": [1073, 382, 93], "status": "eos", "chip_cycles": 566244,
                      "step_cycles": [32246, 32374, 32502], "clock_hz": 1098640000.0, ...}}
data: [DONE]
```

Token 93 is the reduced vocabulary's EOS. It ends the stream with
`finish_reason: "stop"` and adds no text. The text is the shipped tokenizer's
reading of the reduced ids; the reduced vehicle is a numerical test article,
not a language model. The same request with `"temperature": 0.8` returns HTTP
400: "the chip decodes greedily (bit-exact argmax)".

## 5. Evidence

`python3 tools/rtl_host_if_campaign.py` builds all four chips and runs:

- **`qwen3-rom`.** Three users at once. Then the endpoint: one streamed and
  one plain `/v1/chat/completions` request, and one from the `openai`
  client. Then the three fail-closed descriptors.
- **`qwen3-hbm`.** Two users in turn.
- **`qwen3-array`.** A batch of four users.
- **`v41-rom`.** One user.

It writes `results/rtl/host_if_campaign.json`, with the input hashes of
every RTL, harness and runtime file.

All four targets pass. Every request's generated ids equal the decode
campaigns':

| Target | Users | Generated ids | Chip cycles of the request | Engine cycles per decode step | Modelled clock |
|---|---|---|---|---|---|
| `qwen3-rom` | 3 at once | 1073, 382, 93 each | 1,632,348 for the first of three interleaved users <!-- figure: 1632348 src="results/rtl/host_if_campaign.json#targets.qwen3-rom.requests[0].chip_cycles" name="qwen3-rom interleaved request cycles" --> | 32,246 at the first generated position <!-- figure: 32246 src="results/rtl/host_if_campaign.json#targets.qwen3-rom.requests[0].step_cycles[0]" name="qwen3-rom decode step cycles" --> | 1,098.6 MHz |
| `qwen3-hbm` | 2 in turn | 1073, 382, 93 each | 571,738 for the first user <!-- figure: 571738 src="results/rtl/host_if_campaign.json#targets.qwen3-hbm.requests[0].chip_cycles" name="qwen3-hbm request cycles" --> | 32,271 <!-- figure: 32271 src="results/rtl/host_if_campaign.json#targets.qwen3-hbm.requests[0].step_cycles[0]" name="qwen3-hbm decode step cycles" --> | 1,098.6 MHz |
| `qwen3-array` | a batch of 4, then 1 more in a reused slot | 1073, 382, 93 each | 1,047,222 for the last of the four <!-- figure: 1047222 src="results/rtl/host_if_campaign.json#targets.qwen3-array.requests[3].chip_cycles" name="qwen3-array batch cycles, last user" --> | about 58,000 between one user's tokens, four users in flight <!-- figure: 58044 src="results/rtl/host_if_campaign.json#targets.qwen3-array.requests[3].step_cycles[1]" tol="1%" name="qwen3-array cycles between a user's tokens" --> | 1,098.6 MHz |
| `v41-rom` | 1 | 3118, 2400, 318 | 10,476,045 <!-- figure: 10476045 src="results/rtl/host_if_campaign.json#targets.v41-rom.requests[0].chip_cycles" name="v41-rom request cycles" --> | 1,088,554 <!-- figure: 1088554 src="results/rtl/host_if_campaign.json#targets.v41-rom.requests[0].step_cycles[0]" name="v41-rom decode step cycles" --> | 1,033.9 MHz |

Read the rates at the modelled clocks:

- A Qwen3 decode step is about 34,000 tokens/s for one user. <!-- figure: 33936 src="results/rtl/host_if_campaign.json#targets.qwen3-rom.requests[0].modelled_decode_tokens_per_second" tol="1%" name="qwen3-rom modelled decode tokens/s" -->
  A whole request, 16 prompt steps plus 3 generated, is about 0.5 ms.
- The V4.1 core generates about 940 tokens/s. <!-- figure: 939 src="results/rtl/host_if_campaign.json#targets.v41-rom.requests[0].modelled_decode_tokens_per_second" tol="1%" name="v41-rom modelled decode tokens/s" -->
- The four-package array retires one token step every ~14,500 cycles across
  its four users, about 2.2 times the single core. That matches the array
  campaign (`results/rtl/hdc_array_campaign.json`).

The 3118 at V4.1's first generated position is the oracle's token. The next
two ids are the golden model's and the RTL decode campaign's. The torch
oracle is bit-exact only over its first positions, as the decode campaign
records.

The host interface's own cost is small:

- The first completion follows the core's `done` by a few hundred cycles:
  two 64-cycle DMA writes and the MSI.
- Descriptor and prompt fetch take a handful of 64-cycle reads, paid once per
  request.
- Engine busy cycles are within 0.3% of chip cycles on every target.

The endpoint checks on `qwen3-rom` all pass:

- the streamed and plain requests;
- the `openai` 2.24 client, streamed;
- the refusal of a sampling request;
- the three fail-closed descriptors, each an error completion with the
  expected status.

`tests/test_hdc_host_runtime.py` checks four things:

- the record passes, and its expected ids are the decode campaigns' own;
- the record is current against its sources;
- the ASAP7 record routes the same `ot_host_if.sv`;
- a live streamed `/v1/chat/completions` request through the endpoint into
  the Verilated Qwen3 reticle returns 1073, 382, 93.

Set `OT_SKIP_LIVE_RTL=1` to skip the live request.

## Limits

- The memories behind the engines are behavioural, as in every decode-core
  campaign. So are the clears of `ENG_CTX=1` engines: the vector memory and
  KV SRAM are zeroed in one cycle.
- The host bridge models host memory, a fixed DMA latency and an interrupt
  controller. It models no PCIe link layer, credits or ordering beyond
  AXI's.
- The array runs one batch at a time with one prompt and generation length,
  as the package controller does. EOS stops a user's stream, but the array
  still runs that user to the batch's generation length.
- Simulation speed, not the chip, sets the endpoint's wall-clock latency.
  The Qwen3 reticle simulates about 10,000 chip cycles a second on this
  machine, so one reduced request takes about a minute of wall time for
  about half a millisecond of modelled chip time.
