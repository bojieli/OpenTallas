# MU-QWEN-HEAD 2026-10-19: chunked LM head (R4) and the stage-start user index (R3)

This is a sub-lane of MU-QWEN: Qwen ROM 4-user static calendar, owner decision 0is. Items R3 and R4 are defined in
`results/rtl/mu_qwen_1018/README.md` section 3, on branch `claude/mu-qwen-1018`.

Both items are opt-in RTL. The default parameter (1 user) is today's behaviour, and this branch edits no existing file.
Adopting them is a one-patch change each to two closed, critical tiles (see "Adoption"). Nothing was submitted.

## R4: LM head in row chunks with a per-user running argmax

**Where today's argmax lives.** On the current compute die (DV) it is in `rtl/qwen_dv/qfd_dv_slice2.sv`, lines
199-234, in the block "LM-head running argmax".
- Station results of an STN op armed with `amax` (cmd[50]) go into a 16-leaf, 4-level compare tree.
- The tree feeds one running best, `am_run`.
- AMAX (kind 6) `[4]` clears it and `[5]` emits it as the slice candidate.
- The root (`qfd_dv_scalar2`) and the cross-die ARX gather then merge the candidates with the strictly-greater rule, so
  a tie keeps the earlier rank.

The old `ot_qfd_tt_ctlm*` fold (`run_any` / `last_row0`) belongs to the redesign-qwen vehicle and is not on the DV die.

**Why it needs per-user state.** The single `am_run` is one context. A filler's head runs as 8 row chunks interleaved
with the other users' ops, so another user's LM-head chunk would merge into the same `am_run`.

**New block: `rtl/qwen_dv/mu/qfd_dv_amax_mu.sv`**, parameter `NU`.
- **`NU = 1`** is the slice block, statement for statement.
- **`NU = 2..4`** keeps one running best per user, `run[u]`.
  - Each STN op's user (STN cmd[52:51], a spare field) travels down the compare tree beside the leaves. Every leaf of an
    edge belongs to one op.
  - A result merges into the running best of that user only.
  - AMAX clear and emit act on the AMAX command's user (cmd[9:8], also spare).
  - The merge is today's `amb` rule: the larger okey wins, and equal keys go to the lower index. The index is part of
    the rule, so the running best over any chunk sequence equals the single-shot argmax over all rows, ties included.
  - In row order this is the same as "strictly greater wins, and the earlier chunk keeps a tie".
  - A wrong chunk order therefore cannot change the result, and the bench shows it: half of the heads run in a random
    chunk order.

**Static schedule.** There are no credits and no stall. Schedule violations raise a sticky `mu_fault`, which the patch
ORs into `port_fault`. The violations are:
- a clear for a user whose head is open;
- an amax result, or an emit, for a user whose head is not open;
- a user ≥ NU.

## R3: user index on the stage start

**Constraint.** The T calendar event is {class3, arg9}. Class 0 STAGE uses all 9 arg bits: stage 6, L start, token run
and RESULT.

**Encoding: a USER prefix event** (`rtl/qwen_split/mu/qfd_sys_face_mu_user.sv`).
- It is class 7 on the T calendar, with arg[1:0] = user and arg[8:2] = 0.
- Today class 7 on T faults: it is the E-calendar FILL class, so on T it is free.
- The event latches `cur_user`. Every later T event (STAGE, MARK, RESULT, LEVEL, END) belongs to that user until the
  next USER event.
- The compiler emits USER only where the user changes. A period with u user switches costs u T entries, against NE 64.

**Why not elsewhere.**
- **A wider calendar entry** would change `ot_qwen_d2d_cal`, the Q-LINK engine shared with the closed static D2D ends.
- **STAGE's own arg** has no 2 spare bits.
- **Taking the user from the token number** needs the per-user token bank (R2) before the stage start that selects it.

**`NU = 1`.** Class 7 still faults, `ev_user` is constantly 0, and the patched class check equals today's on every
edge. The bench checks all of this.

## Benches (fleet, Verilator 5.050, ot-epyc5, `run_head.sh`)

Logs are in `runs/`, and `runs/summary.txt` is the verdict table (overall rc=0).

| case | expects | result |
|---|---|---|
| `amax_pass_s1/s2/s3` | PASS | PASS on 3 seeds. Phase A: NU=1 equals the verbatim slice2 block (`amax_today_ref.sv` from `mk_ref.sh`) on 60,000 random edges, 0 mismatches. Phase B: 4 users × 150 heads × 8 chunks × 512 rows = 600 emits, 0 mismatches. Seed 1 has 448 cross-chunk-tie heads, 147 chunk-boundary-tie heads, 275 permuted-order heads and 2,414 back-to-back other-user ops. mu_fault 0. |
| `amax_neg_clear` | FAIL | FAIL: a clear of an open head (schedule violation) gives mu_fault 1. |
| `amax_mut1_ge` | FAIL | FAIL: a tie goes to the later chunk (`>=`), 338 / 480 mismatches. |
| `amax_mut2_xtalk` | FAIL | FAIL: a result merges into the current STN user rather than the user carried down the tree, 416 mismatches. |
| `amax_mut3_clrall` | FAIL | FAIL: a clear clears every user, 370 mismatches. |
| `amax_mut4_emitu` | FAIL | FAIL: emit selects the wrong user, 388 mismatches, mu_fault 1. |
| `user_pass_s1/s2` | PASS | PASS: 200k edges, 38k USER events (7.6k with reserved bits set), 88k user-carrying events (26k on the edge right after a USER event). NU=1 identity and NU=4 both show 0 mismatches. |
| `user_mut1_late` / `user_mut2_nochk` / `user_mut3_nu1` | FAIL | FAIL: the user lands one edge late / the reserved-bit check is dropped / class 7 is accepted at NU=1 (breaks the default identity). |

## Adoption (not applied; closed tiles)

`git apply --check` passes for both patches on origin/main.

- **`adopt_dv_slice2.patch`** changes `qfd_dv_slice2`:
  - it adds the parameter `MU_NU = 1`;
  - it replaces the in-line block with `qfd_dv_amax_mu #(.NU(MU_NU))`;
  - it ORs `am_emit_empty | am_mu_fault` into `port_fault`.
- **`adopt_sys_face.patch`** changes `qfd_sys_face`:
  - it adds the parameter `MU_NU = 1`;
  - it instantiates `qfd_sys_face_mu_user`;
  - it exempts USER events from t_bad's class check;
  - it adds two outputs, `seq_dh_user` (the user of the dh stage start) and `result_user`.

**Closed or critical tiles that adoption touches:**
- **`qfd_dv_slice2`.** This means both hardened face masters, `qfd_dv_slice2_w` and `qfd_dv_slice2_e`, generated by
  `tools/qwen_dv/gen_slice_faces.py`, which must thread `MU_NU` through. At `MU_NU = 1` the logic is unchanged, but the
  source changes, so the tile re-gates.
- **`qfd_sys_face`.** At `MU_NU = 1` the logic is unchanged apart from the two constant-0 output ports, and the die
  port-bind must accept them.

**Consumers that must follow** (other MU-QWEN items, not this lane):
- `qfd_dv_cmd_cal`: its command image carries the STN and AMAX user fields. It should forward cmd verbatim; check this
  at adoption.
- `qfd_tt_ctlm_dv`: its `dh` takes `seq_dh_user` for R1 / R2.
- The face's single `tok` / `pos` registers become a per-user bank indexed by `ev_user` (R2).
- The root merge (`qfd_dv_scalar2`) and the ARX gather stay single-context and run once per user token. The calendar
  must keep two users' gathers from overlapping: make the gather a calendar resource window (add it to `mu_calendar` if it is not one yet).

**Not run.** The die-level lint, gate and port-bind of the patched masters are left to the die lane at adoption.
