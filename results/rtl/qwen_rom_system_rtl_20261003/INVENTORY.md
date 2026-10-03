# Qwen3-8B ROM: full-system RTL inventory (2026-10-03)

Status key:
- **RTL+tested**: RTL that is exercised by a bench, or by the system end-to-end run, and passes.
- **RTL untested**: RTL that exists but has never been run on the token path.
- **TB-only**: the function exists only in a testbench or the C++ host.
- **model-only**: an analytical or behavioural model, with no RTL.
- **missing**: nothing exists.

"System top" means `rtl/qwen_sys/ot_qwen_rom_sys_top.sv` on branch `claude/qwen-rom-system-rtl-20261003`. It runs at the REDUCED vehicle shape (TP-4, `tools/hdc_program.py --tp 4`) and its evidence is `campaign.json` in this directory.

The full-shape column refers to the W12/REAL_MEM TP4 runtime (`rtl/test/qwen_rom_runtime`). That runtime is C++-composed and is not this top.

## Data loading

| Block | System top (reduced) | Full shape | Owner branch |
|---|---|---|---|
| ROM weight read (core ↔ weight ROM) | RTL+tested: `ot_qwen_sys_rom` macro model with an address-bound fault (DA1). With ME_CDC, a second read port runs on fclk. | RTL+tested at the host-served scope (W12 TP4 terminal token). REAL_MEM ROM macro services (`ot_qwen_rt_rom_bank`) | this branch; real-memory-runtime @ fa3e4b320 |
| Embedding | RTL+tested: token-row DYN offset into the weight ROM | REAL_MEM `ot_qwen_rt_embed_rom` | real-memory-runtime |
| KV write path (core → HBM) | RTL+tested: `ot_qwen_sys_kv_svc`. Write-back from the staging SRAM; each write completes only on the tagged HBM write-done; `drained` gates the host completion | REAL_MEM `ot_qwen_rt_kv_fill_service` (kv_write_drained from real write-dones) | this branch; real-memory-runtime |
| KV read path (HBM → core) | RTL+tested: the staging SRAM is invalidated at every token. Per-layer block fills use tagged 2-sector reads, and `kv_ok` is issued only after the block is complete. A read of an unfilled word is a fault. Optional KV_PREFETCH notice at token start | REAL_MEM fill service | this branch; real-memory-runtime |
| HBM request identity | RTL+tested: {generation, entry} tags, checked beat by beat (DA2). Corrupted-tag injection is caught | `ot_hdc_qwen_hbm_sector_bridge` still uses tag 0 (pinned) | this branch |
| HBM controller + DRAM | model-only: `ot_qwen_hbm_model_ack` (timing-faithful behavioural model; WR_ACK, refresh, FR-FCFS) | Streaming HBM3E read controller `ot_hbm_r14_stream_pc/stack` is RTL+tested: 0.958 TB/s/stack with REFpb, a 32-sector landing buffer, and a ≥261-cycle notice; it closes at SS at CK/2 (976.6 MHz) | real-memory-runtime (model); qwen-hbm-sustained-bw @ 52ce3e9c1 |
| Near-HBM attention (stack + hub) | not on the reduced token path: its partition and reduction order are the full shape's | RTL+tested by its own exact gates (R=6, R=8), not composed into a token | qwen-nearhbm-attn |

## Communication

| Block | System top (reduced) | Full shape | Owner branch |
|---|---|---|---|
| Die↔die link layer (UCIe in package, board link across packages) | RTL+tested: `ot_qwen_d2d_link`. Provides sequence numbers, CRC-32, cumulative ACK, NAK, go-back-N replay, a replay timer, training, and engine credits carried in sequenced flits. Bit errors at periods 3–101 are recovered with tokens still exact, and a broken channel raises link_fault | `ot_rom_ucie_link` lossless fixed-latency model (W12); W15 `ot_link_tx/rx` detect CRC errors but do not replay | this branch |
| PHY / channel | model-only: `ot_qwen_d2d_chan` (latency + error injection, sim only; hard IP) | model-only | this branch |
| One-shot collective engine | RTL+tested: `ot_rom_oneshot_die` (per die, over the link layer) | RTL+tested; one-stream AR256 gate | main; qwen-allreduce-oneseg @ 7d736e8e6 |
| Collective tag identity | RTL+tested: `ot_qwen_tp_seq_sys` TAG_FULL carries {gen, full position, token, segment} (DA4). The ctrl bench checks positions 5 and 261 | W12 sequencer aliases at 256 (pinned) | this branch |
| Hub↔stack links (near-HBM) | not applicable on the reduced path | missing: direct wires in the near-HBM die bench, with no link layer | qwen-nearhbm-attn (open) |
| HBM service clock ↔ near-HBM engine crossing | not applicable | missing: needs an async FIFO at the service rate unless the clocks share the PLL (stream controller record) | open |

## Control plane

| Block | System top (reduced) | Full shape | Owner branch |
|---|---|---|---|
| Host command queue / doorbell / completion / MSI | RTL+tested: `ot_host_if` MODE 0, driven by a register-level host (SQ descriptors, SQ_TAIL doorbell, CQ phase, CQ_HEAD doorbell, IRQ W1C, MSI) | TB-only (the C++ host drives the sequencer start) | main + this branch (binding) |
| Package controller (host step → N dies) | RTL+tested: `ot_qwen_sys_pkg_ctl`. Start fan-out; done = all dies done AND all KV drained; cross-die token/logit agreement; fail-closed abort | TB-only (C++ host barrier) | this branch |
| Per-die sequencer | RTL+tested: `ot_qwen_tp_seq_sys` (stray-record fault DA3, watchdog) | RTL+tested: `ot_qwen_tp_seq_w12` | this branch; main |
| Reset / power-up sequencing | RTL+tested: `ot_qwen_sys_rst_seq`. Order: host → links trained → HBM scrub + round-trip check → dies → ready. Includes soft reset and boot faults | TB-only (reset at bench cycle 5) | this branch |
| Error / fault reporting | RTL+tested: `ot_qwen_sys_csr`. 24 sticky sources, FAULT_FIRST, mask, IRQ, W1C. Injected HBM-tag and link faults reach the host as an error completion plus a named source | missing | this branch |
| Serial 0.9 GHz / streaming 1.2 GHz split inside a die | RTL+tested: ME_CDC = 1 (matrix engine, its weight, KV and x read ports on fclk; the rest on sclk) via `ot_hdc_core_2clk` emitted from the pinned core. Exact at every fclk phase; 0 dual-clock collisions | TP1 gate exact (two-clock branch); W12 full-shape core swap open | two-clock @ 27d86cfe + this branch |
| Full-shape die parent replacing the C++ host (A10) | — | missing (the REAL_MEM runtime replaces host-served memories; the tile fabric is still host-composed) | open |
