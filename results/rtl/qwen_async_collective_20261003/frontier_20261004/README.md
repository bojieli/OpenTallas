# Qwen async collective: registered-read scoreboard (SB_PIPE=2/3), the final attempt (2026-10-04)

**Verdict: FINAL REJECT.** The owner approved one last attempt. It removes the 256:1 `lw[rd_k]` lookup from the issue loop, but it still does not close SS setup at 1.2 GHz in context. Under the owner rule there is no further redesign. The Qwen ROM keeps the one-stream all-reduce (144,522 cycles per token, ideal memory).

## The change
Source: `3dc2234a7` on `claude/qwen-async-frontier-20261004`. `SB_PIPE` defaults to 0, and modes 0 and 1 are byte-for-byte unchanged in behaviour.

The send check now reads a registered bit, `rdy`. It is loaded every cycle from `rd_go ? lw[rd_k+1] : lw[rd_k]`, using `rd_kb`, a registered `rd_k + 1`. The loop `rd_k -> word_ok -> rd_go -> rd_k` therefore no longer contains a 256:1 mux.

The scoreboard set is also narrowed:
- The tap registers `{we & full & addr < 512, addr[8:0]}`.
- The range check is two short compares against a registered `vw + nw`.
- `SB_PIPE=2` registers the offset as two 16-way one-hots. `SB_PIPE=3` registers the 8-bit offset and decodes it inside the AND-OR.

A mark becomes visible 3 cycles after the write. It is never visible early, and a simulation `$fatal` asserts that no word is sent before `lw[rd_k]` is set.

## Exactness
The Verilator gate passes for both modes. It runs 56 cases each: the real legacy and async sequencers, the rank-order binary32 collective, and adversarial, reverse and partial write orders. The only mismatches are in the three expected overflow-fault cases. The source hashes in the gate JSON match `3dc2234a7`.

The full-token layer-parallel run (with its poison twin) and the REAL_MEM P0/P255 runs were launched but **cancelled** once GRT had decided the verdict. As a result there is no full-shape gain re-measurement for SB_PIPE=2. The last measured gain is SB_PIPE=1's +7.33% (`../sbpipe_20261004`). SB_PIPE=2 adds one more cycle of mark visibility, so its gain would be the same or slightly lower.

## Physical, in context
Both runs used the a0h/a1p recipe: `ot_qwen_tp_seq_async_ctx_w12`, 1.2 GHz, 60 ps setup uncertainty and 25 ps hold, the WC/BC corners, and `ADDER_MAP_FILE=` empty.

| | after CTS repair | after GRT repair | failing endpoints | worst endpoint |
|---|---|---|---|---|
| SB_PIPE=1 (previous attempt) | | **-87.9 ps** | 164 | `rd_k` (256:1 read loop) |
| SB_PIPE=2 | -6.4 ps | **-17.8 ps** (TNS -149.6) | 63 | `rdy` |
| SB_PIPE=3 | -41.6 ps | **-66.5 ps** (TNS -1037.7) | 101 | `rdy` |

In both modes, GRT repair ends with `RSZ-0062 Unable to repair all setup violations`.

**What limits SB_PIPE=2.** The worst path is the *select* of the registered read: `nw[7]` -> segment-end compare -> `rd_go` (about 750 ps of logic, ending at 12-fanout buffers) -> the `lw[rd_kb]`/`lw[rd_w]` select -> `rdy`. Moving the lookup off the loop recovered 70 ps. The control that decides *which* of the two lookups to take is still one cycle long. A third stage would add a cycle per mark and would be another redesign, which the owner rule does not allow.

Detailed route and FF hold were not run to completion, because the setup verdict was already decided at GRT. That matches the previous attempt.

## Files
- `async_coll_verilator_gate_sbpipe{2,3}.json`
- `physical/route_f{2,3}_repair_tail.txt`: the CTS and GRT repair tables.
- `physical/route_f{2,3}_grt_worst_setup_path.txt`
- `jobs/`: the phase scripts and `chain.log`.
