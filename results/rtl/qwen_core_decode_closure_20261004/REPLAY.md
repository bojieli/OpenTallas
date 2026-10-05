# Qwen ROM decode core at 1.2 GHz SS: zero-latency decode restructure DEC_LA

The AR decode core (`ot_qwen_rom_core`, emitted by tools/qwen_rom_rt_core_emit_w12.py + the VPOS emitter) failed
1.2 GHz at SS by 1,257 ps (VPOS=0) / 1,693 ps (VPOS=1) on the repaired screen
(results/rtl/qwen_dspark_closure_20261004/core). Every Qwen ROM rate assumes 1.2 GHz, so this is a mandatory
baseline blocker. DEC_LA (tools/qwen_rom_core_dec_emit_w12.py, parameter default 0, VPRM die `DEC_LA`, driver
`--dec-la`) restructures it with zero-latency techniques only. **No cycle is added**: the core is cycle-for-cycle
the AR/VPOS core, so the 8K AR and DSpark rates are unchanged (AR 2,274 tok/s, DSpark 3,447 tok/s, 1.516x).

## What DEC_LA does
- **Predecode at FIFO entry.** A program word is decoded as it enters the 4-word fetch FIFO, not as it leaves.
  Control fields (unit, barrier, chase, waits, wsrc, a_src) are predecoded from prog_q at pend1. Data fields
  (bases and counts with their DYN adds) are predecoded from a one-cycle staged copy (pq_r) through kept prefix adders.
  They are written one edge after the push, which is no later than the entry's LOAD edge, and read only after it.
- **NEXT data fields come from the FIFO.** The decoded FIFO has 8 entries and NEXT is a pointer (la_nx), so LOAD
  moves only the control registers and pointers. Each data field is the NEXT entry, unchanged until the next LOAD.
  At most 4 entries are held or in flight behind NEXT, so the NEXT entry is never overwritten. The fetch throttle
  still counts fq_n.
- **Registered tables.** The DYN tables, VPOS per-position tables and every DYN_TTILES round count
  ((pos+o) >> (WT+GT-split) / 3 + 1, folded into (x+ODD)/ODD) come from a three-stage pipeline off pos_r/tok_r with
  kept adders. It is settled at E3; the first program word is registered at E4.
- **Registered lookups.** Each word's split rounds and DYN values are looked up when the word is staged (pend1).
- **One-hot write strobes.** The FIFO slot writes use registered one-hot strobes.
- **Kept comparators and counter.** The chase test uses kept log-depth comparators, the lm_head chunk argmax uses a
  kept key comparator, the update has its own kept copy of `issue`, the cycle counter uses a kept incrementer, and the
  FIFO count candidates are precomputed.

## Screens (tools/risk_clock_loops_screen.py repaired phase without I/O constraints; SS RVT, 60 ps; ~150 ps pessimistic vs routes)
| version | VPOS=0 reg-to-reg | VPOS=1 reg-to-reg | worst path |
|---|---|---|---|
| baseline core (no DEC_LA) | -1,257 ps | -1,693 ps | fq_rd -> ir mux -> DYN/ /3 rounds -> me_tiles |
| DEC_LA first cut (86a06603b) | -386 | — | predecode / tables |
| DEC_LA ea08ba78f | -108 | -294 | me_tiles 128:1 rounds lookup |
| **DEC_LA final bc6f91862** | **-45.6** | **-66.6** | d_chase_n -> chase compare -> issue -> LOAD (la_rd, fq_n, run_val) |
Final VPOS=1 focus: fsm +222, issue -67, FIFO writes -28, tables -43 ps. Final VPOS=0: fsm +2, issue -29, FIFO -0.8,
tables -26 ps (`screens/core_d1v0h`, `screens/core_d1v1h`).

The remaining path is the core's single-cycle issue loop: unit progress vs the chase count, then issue, then LOAD.
It is within the screen's calibrated pessimism. The authority is an in-context route (see CODEX_HANDOFF.md):
the core alone exposes 1.87 M black-box unit ports and cannot be routed standalone.

## Exactness (8K benches, same plans/goldens as results/rtl/qwen_dspark_system_20261004)
| job | committed | proof/b (86a06603b, EPYC) | proof/h (final bc6f91862, ot-agidock128) |
|---|---|---|---|
| k_L0: verify L0, P8187 np4, commit 1, rollback, then P8188 np4 | 49,582 cyc | pass 49,582, 40 checks 0 mismatches | pass 49,582, 40 checks 0 mismatches |
| k_AR0: AR L0 at P8187 | 14,581 | pass 14,581, 8 checks 0 | pass 14,581, 8 checks 0 |
| c_H1: head p=4 + accept | 12,000, a=0 bonus 98951 | pass, same | pass 12,000, a=0 bonus 98951 |
| c_H2: head p=4 + accept | 12,000, a=3 bonus 1958 | pass, same | pass 12,000, a=3 bonus 1958 |
| k_D0r: drafter L0 at 8188 | 30,618 | pass 30,618, 16 checks 0 | pass 30,618, 16 checks 0 |

All runs use SEQ_LA=1 and DEC_LA=1. They are bit- and cycle-identical to the adopted records, so the driver
default is now `--dec-la 1`.

## Replay
jobs/core_screen.sh LABEL VPOS DEC_LA (EPYC; the Yosys 0.68 screen-copy workarounds of the VPOS block are in the
script, logic identical); jobs/proof.sh (EPYC) / jobs/proof_pve1.sh (PVE1 / ot-agidock128, bench inputs mirrored at the same /srv paths).
