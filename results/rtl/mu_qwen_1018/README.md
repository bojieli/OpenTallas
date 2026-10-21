# MU-QWEN 2026-10-18: Qwen ROM 4-user static calendar (owner MU.DECIDE option A)

The owner decided (10-18 ~23:30, MU.DECIDE option A) that Qwen ROM multi-user goes into this release. The target was
4 users: 1 latency user at 4,769 tok/s plus 3 users at about 4,549 tok/s each, with no die change.

The design sources are `results/arch/rom_multiuser_1018/README.md` sections 1, 3 and 4, and
`results/arch/s81_balance_1018/README.md` section 2.

The rules are static schedule only:
- no credits and no backpressure;
- a collision is a compile error in the compiler and a sticky fault in the RTL, never a stall.

## 1. The finding that changes the decision basis

**The study's 4-slot pure-shift calendar (18.4k tok/s) does not exist for the real Qwen layer programme.**

The shift lemma (study section 3) assumes that every shared resource is used once in each layer period. The production
layer programme does not meet that assumption:
- the compute-die ROM tile field is used 4 times (qkv, o_proj, gate_up, down);
- the SU/VM is used 5 times;
- the TP8 collective runs 2 all-reduces;
- the single shared UCIe link carries P and R frames for both all-reduces, which is 4 runs.

Two users collide on a resource if some shift difference between them equals a difference between two of that
resource's windows. With several windows per layer, those differences cover almost every shift.

**Frame check** (`frame_feasible_shifts`). Layer period 6,886. Windows come from the 10-13 production layer of record.

| occupancy model | tile-field forbidden shifts | feasible 2-user shifts | 4-user pure shift |
|---|---|---|---|
| measured unit-busy windows (tile field 1,283 a layer) | 5,781 / 6,886 | 82 (3,283-3,323, 3,563-3,603) | **none** |
| priced windows (tile field 1,643) | 6,319 / 6,886 | 0 | **none** |

**Best static calendar found** (`compile_calendar`).
- Each user's work is the single-user programme. Only start cycles are compiled.
- The latency user is fixed at its single-user timeline, and the compiler asserts that it stays bit-for-bit identical.
- All windows are checked pairwise disjoint over the whole emitted schedule.

| sequencer granularity | LM head | users | aggregate tok/s | per user |
|---|---|---|---|---|
| layer (today: one stage start a layer, layer rigid) | 1 window 3,048 | 2-4 | 4,769 | fillers never finish a token |
| layer | 8 chunks | 2 | 9,291 | 4,769 / 4,522 |
| op (the sequencer interleaves users at programme-op level) | 1 window | 2-4 | 4,769 | fillers never finish a token |
| **op** | **8 chunks** | **4** | **14,054** (measured occupancy) / 12,568 (priced) | 4,769 / 4,642 / 2,321 / 2,321 |
| op | 8 chunks | 3 | 11,732 | 4,769 / 4,642 / 2,321 |
| op | 8 chunks | 2 | 9,411 | 4,769 / 4,642 |

Grade: **modelled**. The windows are measured-old-RTL (the 10-13 TP4 vehicle) plus priced production adders; the collective
uses the current-RTL word timeline at LU 53 / LS 378.

**Why the LM head must be chunked.** The latency user's tile-field gaps are all shorter than the 3,048-cycle head. A
filler's head therefore never fits in one piece and has to run as row chunks. A per-die running argmax merged in row
order with the strict-greater rule gives the single-shot result.

**What blocks the fillers.** No single resource does it. Ignoring one resource at a time:
- the tile field gives 14.4k;
- the KV service gives 14.0k;
- the collective / shared UCIe gives 15.3k;
- ignoring the tile field, the SU and the collective together gives 18.9k, the study's number.

So the 18.4k figure assumes that a user's 12 chained layer ops can slide freely past each other. They cannot: a filler
must wait for the gaps in all four resources at once.

**The collective is not the limit.** The engine is 18% busy and the shared UCIe 37% busy in the 4-user schedule.

## 2. The collective sequencer (item 1)

**Engine.** `rtl/rom/ot_coll_tp8_static.sv` is already a fixed-offset pipeline.
- Its only sequential state is the slot sequencer, which is busy for `words` cycles a command (256 for an all-reduce).
- Every later stage is a delay ring or delay line indexed by the free-running counter: the P / S / R rings and the
  linkcal / CDC / codec slots.
- So it accepts a new all-reduce every 256 cycles while older epochs are still in flight.
- The constraints are the static engine-resource sets: issue, B, W, O, hold and the shared UCIe P/R.
  `mu_calendar.coll_sets` checks them, and the bench re-checks them.
- **No engine RTL change is needed, and no CLOSED collective tile re-closes.**

**Bench.** The 8-die TP8 bench `tools/qwen_coll_tp8_static_links_bench.py --mu-cal` runs on the production wrapper:
dv2f14bi real lanes, calendar LS 378, six_five UCIe, 50%-duty clocks, Verilator 5.050. It has four cases:
- **positive:** 30 all-reduces of all 4 users at their compiled cycles from the of-record calendar, including 8 pairs of
  epochs in flight at the same time. Each word must be exact at its compiled cycle, with zero faults.
- **identity:** the same window with only the latency user's 11 commands. Its outputs must land on the same compiled
  cycles.
- **negative control:** one filler command moved into the previous command's 256-word issue window. It must fail with an
  engine calendar fault.
- **mutants:** RLAT and RANK on the multi-user window must fail.

Results are in `coll/runs/` (record.json and logs per case).

**The real one-in-flight limit is the die sequencer, not the engine.**
- `ot_qwen_tp_seq_w12_vrl` (inside `ot_qfd_seq_su_bi`, die master `qfd_seq_su_static`) stays in S_COLL until the last
  result word arrives.
- It has one context {tok, pos, seg}.
- The collective calendar face `qfd_seq_su_collective_calendar` captures one token/position per stage start. It has
  DEPTH 8 rows and admits tags 0..2 only.
- Lane MU-QWEN-SEQ owns the opt-in multi-epoch sequencer: NU contexts, an in-order epoch FIFO, a per-user VM base, and a
  user in the tag. Its branch and results are listed in the lane file.

## 3. What 4-user operation needs on the dies (die-bound RTL, for the die lanes)

**Compute die (Q-DIE15).** None of these items changes die area; all of them change RTL in RTL-only clusters.
- **R1. Op-level user interleave.** Without it the calendar fits at most 2 users: 9.3k with a chunked head.
  - The core (`ot_qwen_rom_core_ctrl_x_bi`) holds its program counter through the in-segment waits: the KV attention
    result (`kok`) and the collective (S_COLL).
  - Fix: either a merged per-period programme with a per-instruction user field, or NU user contexts with compiled
    per-op starts.
- **R2. Per-user DYN offset bank** (token row, RoPE row, KV write slot, context length, VM base), selected by that user
  field. Per-user residual + staging is 24 KB a user in VM.
- **R3. User index on the stage start.** `dh` / `sys_face` T calendar events need +2 bits: the event arg is 9 bits and
  all 9 are in use today.
- **R4. LM head in row chunks** with a running argmax across chunk segments.
- **R5. Collective calendar face:** per-user issue contexts (or DEPTH ≥ 9 period programmes) and a user field in the
  collective tag.

**KV die (KV-PLAN / KV-HROOT).**
- **R6.** Per-user KV row (coordinator 0jc, 10-19: the RTL row is the reference). Row of user u, layer l =
  64 + l + 256*u: `qkd_kv_mu_wrow` / `qkd_kv_mu_rrow` put the stage user into row[9:8] of today's row 64 + l (bit
  insertion, no job-word field). The compiler (`kv_user_rows` / `kv_user_bases` / `kv_user_dimension`) emits the same map,
  test `test_kv_user_rows_match_rtl_rowoff` (the earlier compiler map (u*36 + l) << 10 did not match the RTL and is gone):
  - 144 user-layer rows (64..99, 320..355, 576..611, 832..867), all below the embedding table (row 24,427);
  - the per-PC stream is 514 HBM edges, which fits the 1,265-edge service window;
  - the service windows never overlap across users.
- **R6 (host).** NSLOT 4 on the host plane (`qkd_host_if_pins` `$fatal`). Lane MU-QWEN-HOST covers it.

**Not to be wired: `ot_qwen_activation_handoff`.**
- It is an elastic ready/valid FIFO, and no die instantiates it.
- Wiring it would add backpressure, which the static schedule forbids.
- Under the static calendar the user of every D2D record is a compiled fact. A user tag on the static D2D records
  (`qfd_d2d_static` / `qkd_d2d_static`) is only a check field.

## Files

- `tools/qwen_static_schedule/mu_calendar.py` is the compiler. It covers the calendar, the frame lemma check, the
  whole-schedule verifier, the collective word sets, the kv_calendar user dimension and the bench-case emitter.
  `test_mu_calendar.py` holds its tests (10 PASS).
- `calendar/summary.json` holds every number above: `python3 -m qwen_static_schedule.mu_calendar --out ...` from `tools/`.
- `coll/mu_cal.json` holds the bench cases. `coll/runs/` holds the fleet results; the launcher is
  `tools/xdie_qtp8/launch.sh`, run with cases mu_bi, mu_bi_neg_overlap, mu_bi_mut_rlat and mu_bi_mut_rank.
