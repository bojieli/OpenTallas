> **Coordinator decision 2026-10-19 (MU-S81b): the S81 multi-user AR target is 46 users** (the proven calendar), not 47. No third copy of the four full-scan groups (~+40 dies) is added for one user. 47 is recorded only if the twelve non-duplicated FFN-pair stages (S005..S027) measure >= 1.4% faster in RTL (20,754 -> <= 20,468 cycles; `target47_bound.json` keeps that bound). Composition of record: **46 x 1,224.1 = 56,309 tok/s** AR, MTP 10 x 3,711.7 + 1 filler = 38,009 (token_path_1018 `multi_user`).
>
> (Superseded) Codex recovery 10-18: the owner target remained 47 AR users on 520 dies; the 46-user calendar was called diagnostic. Current main's S81-SCAND pricing corrections remain authoritative.

# MU-S81 2026-10-18: the S81 multi-user static calendar, chain plan and pricing

Owner decision MU.DECIDE option A (HANDOFF 0is). The coordinator's S81 configuration is:
- B3 index sharding with MTP read sharing;
- the 8 index-attention stage groups duplicated: S029 (L20), S020 (L14), S011 (L8), S002 (L2), S034 (L24), S040 (L28),
  S046 (L32) and S052 (L36);
- 520 dies and 520 HBM3E stacks in total.

Grade: **modelled**. The calendar is exact integer arithmetic on the S81-BALANCE stage model of record
(`results/arch/s81_balance_1018/compute.py`, imported as is). MU.TOK measures it on RTL.

## Files

| file | producer | what |
|---|---|---|
| `calendar_ar.json`, `calendar_mtp.json` | `tools/s81_dv/dv_mu_calendar.py` | N-slot calendar: slots, copy A/B per user, per-group per-slot `{user, kind, copy, local, start, wb[, sb, ikb]}`, the shift-lemma result |
| `chain_plan.json` | `tools/s81_dv/dv_mu_chain.py` | placement of copy B, extra links, latency and occupancy checks |
| `../token_path_1018/ds_rom.json` `multi_user` | `tools/token_compose_xdie.py` | aggregate priced on this composition's per-user rate times the calendar's users |

Tests: `python3 tools/s81_dv/test_dv_mu_calendar.py`. It covers positive cases, 4 negative controls and the `--check`
reproduction. Regenerate the records with `dv_mu_calendar.py`, then `dv_mu_chain.py`, then `token_compose_xdie.py`.

## Result

| mode | users | per-user | aggregate | slot (cycles) | period (cycles) | lemma |
|---|---|---|---|---|---|---|
| AR | **46** (model said 47) | 1,224.0 (calendar model) / 1,224.1 (composition) | **56.3k** / **56.3k** | 21,313.7 (P/46 on the 4-edge issuer grid) | 980,428 | PASS, 5,474 windows, 0 collisions |
| MTP | 10 + 1 AR filler | 3,829.1 / 3,711.7; filler | 39.2k / 38.0k | 124,524 | 1,303,400 | PASS, 1,309 windows, 0 collisions |

**Finding: existing model windows and fixed-copy assignments do not fit 47 AR users at the target period. Target = 46 (coordinator 10-19).**
- The study's `floor(T / II)` treats a duplicated group as one stage with half the occupancy. A real copy holds one
  position for its full window: S029 38,900, S020 35,325, S011 34,394, S002 31,144 cycles.
- Users must alternate copies, so that on each copy the gap between consecutive users is at least the window. With an
  odd N the alternation breaks once around the circle (an odd cycle cannot be 2-coloured). That puts two users on the
  same copy one slot apart.
- At N = 47 that gap is at most 25,652 cycles on the four-edge issuer grid (980,428 minus 46 x 20,756). That is below all four full-scan windows.
- The 4 reindex groups (23,190) would tolerate it; the full-scan groups would not.
- 47 users would need a 3rd copy of S002/S011/S020/S029: about +40 dies for +1 user (+1,224 tok/s). **That is not
  recommended.**
- At N = 46 the slot is P/46 = 21,313.6, which is at least the largest non-replicated window (20,754). Every duplicated
  group runs 23/23 users per copy, with a per-copy gap of 42,627, which is at least 38,900.

**The latency user (user 0)** has shift 0 and is on copy A of every group. Its windows are the single-user windows,
and the brute-force check finds no other user touching them. Its rate and cycle trace are therefore the single-user
ones.

## The shift-lemma assertion (compile fault, never a stall)

1. **Premise.** Every non-replicated window is at most the slot spacing, and every duplicated window is at most its
   per-copy spacing.
2. **Brute force.** For every resource, every pair of users is checked with windows taken modulo the period. A
   resource is a stage-group copy, a stage-hop link copy (h message 652 cycles, or 6 x 652 a MTP step) or the host
   plane (134 cycles a token). Any overlap is a FAULT and the compile fails (exit 2).
3. **Latency user.** It has shift 0 and is on copy A everywhere.

Negative controls in the test:
- 47 users is refused, with the reason.
- Forced 47 with plain alternation shows a collision on S029.A.
- User 1 moved onto user 0's copy of S029 shows a collision between users 0 and 1.
- An 11th MTP user collides.

## Per-slot tables (compiler hook)

`dv_layer_compile.py --layer L20 --mu-cal results/arch/mu_s81_1018/calendar_ar.json --out DIR` writes
`DIR/prog/mu_slots.json`.

**One programme for all users.** The calendar rows are the single-user ones. Per slot, only the data changes:
- the dsdv_seq_host V context body: context 1 = body[159:108] = {user 10, pos 21, tok 21};
- the per-user HBM bases on the user's copy: `wb` (window ring, dsdv_svc_att `WB + 68 u`, built), and `sb` / `ikb`
  (compressed rows, index keys).

**Bases.** `local` is the user's index among the users of its copy, so each copy's HBM holds only its own users. The
`sb` / `ikb` region sizes come from `svc_bases.json` (lane MU-S81/SVC); until that file exists only `wb` is emitted.

**Positions.** pos = pos0 + p x stride, with stride 1 in AR and 6 in MTP (the verify positions of a step).

## Chain plan (520 dies)

- **Copy B.** Each duplicated group gets 10 more dies (`round(388/40)`, the study's basis) and 10 more stacks, in 2
  trays, in copy A's rack row on the same switch plane set. That is 80 dies, 80 stacks and 16 trays in total.
- **ROM content.** Copy B dies carry copy A's ROM content: the same masks are fabricated twice, so there is no new mask
  set. Copy B's HBM holds only copy-B users' state.
- **Extra links per group:**
  - stage hop in: upstream rank dies to copy B, 4 circuits;
  - stage hop out: copy B to downstream, 4 circuits;
  - copy B's own TP4 and intra-group lanes, the same as copy A.
- **Physical form (MU-S81/LINK, claude/mu-s81-link-1018 258c9894b): a second lane pair, i.e. a second static
  circuit.** A destination field is not possible: the frozen lane tile's link layer is end-to-end per peer pair, so two
  peers on one lane would mix two sequence spaces.
  - The 4 rank dies of each pre-group and post-group stage (64 dies) need a p4l variant: +1 SerDes lane pair (2 PHY
    lanes) and `ot_s81sl_lep_mu` (lane face ~4.4k pins, needs a taller outline or a second face). **This is a die
    variant, not die-unchanged.**
  - 64 extra circuits in all; added switch ports: 480 SerDes lanes on copy B + 128 on the variant dies.
- **Latency.** Every crossing is the same fixed-delay switched channel (377.6 ns budget), so copy B's hop latency
  equals copy A's (delta 0) and the lemma holds unchanged.
- **Occupancy.** The added links carry 652 of 21,314 cycles a slot, which is 3.1%.
- **Reuse layers.** In the token DAG of record every layer writes and reads its own rows on its own stage
  (`own_row_write` / `window_load` / `pv`). What later layers reuse from the owner layers is the top-k selection, which
  rides the user-tagged h message. Copy B therefore needs no reuse link. MU-S81/SVC confirms this on the RTL.

## Composition

The `multi_user` block of `token_path_1018/ds_rom.json` is priced as follows:
- **per-user rate:** this composition's single-user rate, which the lemma keeps;
- **aggregate:** users x per-user, plus the MTP-calendar fillers at f / step.

On main (10-19, after S81-SCAND B3) this gives AR 46 x 1,224.1 = 56,309 and MTP 10 x 3,711.7 + 1 filler = 38,009 (was
46 x 1,243.0 = 57,178 before S81-SCANCHK / S81-SCAND re-priced the single-user rate).

## Issuer grid (MU-S81/TOK, 10-19)

`ot_dsdv_fixed_issue` accepts a job start only on its 4-edge start phase (otherwise it raises fault 5). Every shift
and the period are therefore multiples of 4. That is now the default (`--phase-q 4`): AR period 980,428 (+3 cycles),
MTP 1,303,400. The rate is unchanged at the shown precision.

The TOK bench (`results/rtl/s81_mu_1018`) passes on this calendar on the real `dsdv_seq_host` + `ot_dsdv_fixed_issue`:
- 46 users on S000, and S002 copy A / copy B 23 + 23;
- user 0's log is line-identical to the single-user run;
- 4 mutants fail.

The 1-cycle grid (`--phase-q 1`) is kept only as a diagnostic; it is not issuer-feasible.
