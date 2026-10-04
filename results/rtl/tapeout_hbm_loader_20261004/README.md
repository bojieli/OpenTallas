# HBM accelerator: host -> HBM load engine (2026-10-04)

Gap closed: the HBM accelerator's HBM contents (weights, KV images) existed only as load-time `$readmemh` images;
there was no path for the host to put a checkpoint into HBM (inventory row hbm_accel / fsr_load).

RTL `rtl/hbm_accel/loader/ot_hbm_accel_loader.sv` (default-off ENABLE=0): AXI4-Lite register slave (BAR view),
AXI4 256-bit read master to host memory (INCR bursts of 16, never across 4 KB, 8 outstanding), payload CRC-32,
asynchronous FIFOs host -> memory clock, one MREQ client of `ot_gpu_memsys` issuing full-strobe sector writes
(96 unacknowledged), optional read-back verification (16 reads in flight, reorder buffer, second CRC-32),
completion + status + irq. CRC = `tools/mem_compiler/ecc.py` signature over 256-bit sectors.

Gate `tools/hbm_accel_loader_gate.py` + bench `rtl/test/hbm_accel/tb_hbm_accel_loader.sv` (Verilator 5.050,
ot-epyc1tb). Image: die 0 of the DeepSeek-V4.1 HBM system run (the `$readmemh` files of that bench), memory system
with NO load-time image. Verdict **PASS** (`record.json`):

| Transfer | Result |
|---|---|
| T0: densest 8 MiB window (262,144 sectors, 259,435 non-zero), verify on | status 0; payload CRC = read-back CRC = expected `84d2183a` |
| T1: second 1 MiB region, verify off | status 0; CRC `cac870b9` |
| Full memory compare, 2 partitions x 2^21 words | 294,912 loaded words equal the system image, every other word still 0: **0 mismatches** |
| misaligned size / one corrupted beat / AXI SLVERR | status 3 / 1 / 4 as specified |

Measured rate (host clock 1 ns, host read latency 400 cycles): 9.79 GB/s write-only, 5.0 GB/s with read-back.
The rate is set by the single MREQ client of the reduced memory system (NPC 2), not by the engine: it is the same
with 32 and 96 writes outstanding (`record_1mib_outw32.json`). Boot load is off the decode path; full-rate boot
needs one engine port per HBM partition (not built).

Not done: installation in `ot_hbm_accel_hbm_system` behind `ot_host_if` (the engine is a standalone block with
its own BAR window), HBM -> host direction (KV save), SS/FF timing of the engine.
