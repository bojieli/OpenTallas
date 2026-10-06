# S81-PH gather -> capture exact lockstep bench (CLAUDE S81-PH, 2026-10-06)

Bench `rtl/dsrom_sys/s81_ph/test/tb_s81ph_gather_capture.sv`, stimulus `gen_stim.py <case> <seed>`, Verilator 5.032 on
ot-epyc2 (`/srv/opentallas-scratch2/scratch/claude/s81-ph/benchA`, `build.sh <tag> [defines]`).

Reference = 128 `ot_v41_ret_root` (D = QD = 128) + `ot_dsrom_rd64_vm_capture` (ENABLE, CAPACITY 1, VM_AW 19,
ALWAYS_ACCEPT) + S81 profile quota, wired as the spine.  DUT = `dsfd_sp_gather` -> `dsfd_sp_capture`, VM writes taken at
the serial-domain pins (ck : ckv = 4 : 3).  Compared: every root's ordered (addr, data) sequence, totals, final drained
and fault.  `run_base_*` = flat roots (ROOT_BLK 0), `run_blk_*` = hardened root sub-blocks (ROOT_BLK 1, the routed
configuration), `run_m1/m2` = negative controls.

| case | content |
|---|---|
| mix (seeds 7, 11, 12, 13) | 9 phases: fmt 0/1/2 x np 0/3/7, rows 64..1000, random tree cuts (nseg <= 8), random and burst arrival |
| trace | the retained I66 shape: every root's rows complete in one burst (576 rows / 6 edges), and 7,168 rows = 56 back-to-back rows per root |
| err / over / range / rreq | error partial, over-quota row, address out of range, reset request: both fault |
| m1 (S81PH_MUTANT_BF16_TRUNC) | bf16 by truncation instead of the root RNE: FAIL (128 roots mismatch) |
| m2 (S81PH_MUTANT_LANE_SWAP) | lanes of roots 0/1 swapped: FAIL (2 roots mismatch) |

Result: every base/blk case PASS, both mutants FAIL (`summary.txt`).

Cycle cost (phase completion, VM sees `drained`, vs the core's in-clock 128-port writer): +7..9 stream cycles (flat),
+9..10 (hardened root sub-blocks), independent of the phase size: back-to-back 56-row bursts per root drain at the
2-row serial words without backlog (no hold overflow).  Per dependent weight phase this is the fixed latency of pin
registers, the stream->serial crossing and the status crossing.
