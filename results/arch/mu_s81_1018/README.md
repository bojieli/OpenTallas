> **Coordinator decision 2026-10-19 (MU-S81b): the S81 multi-user AR target is 46 users** (the proven calendar), not 47. No third copy of the four full-scan groups (~+40 dies) is added for one user. 47 is recorded only if the twelve non-duplicated FFN-pair stages (S005..S027) measure >= 1.4% faster in RTL (20,754 -> <= 20,468 cycles; `target47_bound.json` keeps that bound). Composition of record: **46 x 1,224.1 = 56,309 tok/s** AR, MTP 10 x 3,711.7 + 1 filler = 38,009 (token_path_1018 `multi_user`).
>
> (Superseded) Codex recovery 10-18: the owner target remained 47 AR users on 520 dies; the 46-user calendar was called diagnostic. Current main's S81-SCAND pricing corrections remain authoritative.

> **Direct cabling (OWNER 10-21, supersedes the switched leg below): AR -74,484 cycles a token, MTP -74,344 cycles a step (net of the 5,280 TX hold).**
> The S81 release has no switch. The TP4 mesh is board trace inside one tray. Stage hops use passive DAC inside a rack and AEC between racks, in serpentine order.
> Each crossing's off-chip leg is now its circuit class's `D_cycles_max` from `results/arch/release_rack_1021/hop_latency.json` (claude/rack-1021 @5a1c6dcea), replacing the 453-cycle switched leg:
> - tp_mesh 251, stage_hop 265 (includes the longest turnaround AEC circuits), head_hop 257, token_return 251;
> - copyb_in 258, copyb_hop 265, copyb_out 257.
>
> `dv_mu_calendar.offchip_saving()` re-prices every term of the composition of record (`results/rtl/xdie_s81_1019/record.json` token_compose) as exposed = max(0, E - O). The stage offsets use hop = 1006 - 453 + 265 = 818. The period = the model period minus the saving.
>
> | | switched (453) | direct | delta |
> |---|---|---|---|
> | AR period (cycles a token) | 980,428 | 905,944 | **-74,484** (tp_mesh 257 crossings -51,914; stage_hop 119 -22,372; head_hop 1 -196) |
> | AR per user | 1,224.0 | 1,324.6 tok/s | +8.2% |
> | AR users / aggregate | 46 / 56,302 | **42** / 55,633 | -1.2% |
> | MTP step period | 1,303,400 | 1,229,056 (1,223,776 + 5,280 TX hold) | **-74,344** |
> | MTP per user | 3,829.1 | 4,060.7 tok/s | +6.0% |
> | MTP users / aggregate | 10 + 1 filler / 39,211 | 9 + 3 fillers / 39,475 | +0.7% |
>
> **Why AR drops to 42 users** (the calendar's own search):
> - 44 users gives a slot of 20,590, which is below the largest non-replicated window of 20,754. It is short by 164 cycles.
> - 43 is odd, and S002 cannot be 2-coloured.
> - So 44 users would come back if the largest non-replicated window shrinks by 164 cycles or more.
> - **Next optimisation (lead 10-21, not now):** shrink that window by at least 164 cycles to fit 44 users. The AR record stays at the 42 users the calendar admits.
>
> **L20 split:** the MTP L20-split record keeps 1 filler. With 3 fillers the S030 helper collides, so the build drops fillers until the helper check passes.
>
> **Stage hop on the wire:** NB stays 80 (lead 10-21: the existing lep and land masters; the closed land view 263e13fc3 has NS = 1).
> - The 320-beat h goes out as 4 back-to-back 80-beat tag windows: 4 mu_c commands a hop, all ab 0.
> - **AR:** every hop window cuts through with land = 0 (`circuits.hop_windows`). The tightest margin is 373 cycles at S005, so the NS = 1 landing slot is never used by stage hops.
> - **MTP: fixed with a TX hold (lead pick 10-21).** At 12 groups (S005, S007, S008, S010, S014, S015, S017, S018, S023, S024, S026, S027) the MTP step fills the slot exactly. Without the hold, the h would reach the receiving stage 440 cycles before the previous user frees it, and a landing leaf with NS = 1 cannot hold 4 windows.
> - The sender now holds the h TX 440 cycles (`stage_windows(hold)`, `hold_tx`). Those stages and every later one start later, and the step period grows by 5,280 (0.4%).
> - Every MTP hop window now cuts through (land 0, margin 0). NS stays 1 and the hardware and the CLOSED land view are unchanged.
> - L20-split MTP: 1,228,600 cycles a step, 9 users + 1 filler, 37,536 tok/s.
>
> **Rack wiring mismatch.** `connections_s81.csv` @5a1c6dcea does not wire the LINK5 lane plan:
> - It puts TP d+2 on WN<->WN (lk_WN0/1 at both ends) and the stage hop on EN0/1 -> WN2/3.
> - The lane plan puts d+2 on s_7N EN<->EN and the stage hop on s_0N pair A -> s_0N pair B.
> - In the rack wiring, s_0N receives d+2 TP on pair A AND the previous stage's h on pair B. Both release into ri, which is the sticky co-release fault.
> - The latencies are per class, so this calendar is unaffected. The wiring table should follow the lane plan.
>
> **Downstream copies not regenerated here:**
> - `calendar_*_q4.json` (TOK bench copies).
> - `token_path_1018/ds_rom.json` `multi_user`, which still says 46 x 1,224.1.
> - the xs_field_calendar MU check inputs. They read 42 users from `calendar_ar.json` the next time they run.

> **S81-LINK5 (owner-approved 10-21 06:00): 5 static circuits a stage die; the stage hop gets its own circuit.**
> The chain plan and calendars now use the real stage die. The stale "6 SerDes + 2 UCIe" p4l count is gone.
> `dv_mu_calendar.CIRCUITS` holds the circuit table and `chain_plan.json` `array.circuits_per_die` repeats it.
>
> **Lanes per die:** 10 SerDes = 5 lane pairs (8 copy-A SerDes + 2 pair-B SerDes on s_0N), 0 UCIe, plus 2 reserved slots.
>
> | endpoint | pair | SerDes | peer (die of TP rank r, stage k) | use |
> |---|---|---|---|---|
> | s_0S (WS) | A | lk_WS0/WS1 | k.(r-1).s_7S A | TP d-1, bidirectional |
> | s_7S (ES) | A | lk_ES0/ES1 | k.(r+1).s_0S A | TP d+1, bidirectional |
> | s_7N (EN) | A | lk_EN0/EN1 | k.(r+2).s_7N A | TP d+2: ONE bidirectional EN<->EN circuit (was 2 one-way EN->WN). The d+2 parts now land on s_7N RX at the E end. Also the host plane (see finding 2) |
> | s_0N (WN) | A | lk_WN0/WN1 | (k+1).r.s_0N B | stage NEXT: h TX. Every window opens with ab 0. RX carries only the link layer |
> | s_0N (WN) | B | lk_WN2/WN3 = link_0_4/0_5 | (k-1).r.s_0N A | stage PREV: h RX, merged into ri. TX carries only the link layer |
> | reserve | - | link_1_4/1_5 (E column B) | copy-A/B pair | blockage. Populated only on the 64 pre/post-group rank dies as the copy-B circuit |
>
> Per TP4 group there are 6 TP circuits (4 S-ring + 2 EN<->EN), so every peer is 1 crossing. There are 4 stage circuits per stage boundary. The first stage has no PREV circuit and the head die has no NEXT circuit.
>
> **Calendar** (`dv_mu_calendar.py`, records regenerated; slots, shifts, copies and bases are unchanged):
> - The stage hop leaves the ES TP circuit. Its TX is `link.<g>.<cp>` = s_0N pair A. Its RX is `rx.<n>.<cp>.s_0N.B`, landing 563 cycles later (+-2).
> - Copy-B hops use `link.<g>.A.rsv` / `rx.<n>.A.rsv`, the reserve pair.
> - Brute force: AR 8,142 windows and MTP 1,947 windows, 0 collisions. The L20-split records also have 0 collisions with their helper check PASS.
> - **Pair A and pair B never release into ri together.** Every stage-hop window is ab 0, and no ab 1 window is ever compiled on s_0N. So s_0N pair A RX only ever sees the link layer: the successor's pair B TX carries no ring beat.
> - s_7N has no pair B (AB_EN 0), so the d+2 RX on s_7N has no merge rule.
> - The TP endpoints carry no h window any more.
> - (Figures in this block are the switched-leg values. The direct-cabling block above supersedes them.)
> - `--hop-port es` rebuilds the old fold as a diagnostic and writes nothing. It also finds 0 collisions at stage granularity: the minimum AR margin, slot - (span + h), is 690.7 cycles at S005.
>
> **Compiler:**
> - `layer_prog/lower_vpx.py`: the d+2 leg in `LEGS` now lands on peer `u_s_7N`, and `STAGE_LEG` = s_0N -> next-stage s_0N.
> - `layer_prog/final_ffn_transport.py`: the d+2 end link is sid 15 -> 15 (was 15 -> 1).
>
> **Per-token cycle delta from LINK5 itself: 0 cycles, AR and MTP, single-user and MU.** The direct-cabling delta is in the block above.
> - The composition of record (`results/rtl/xdie_s81_1019/record.json`) already prices each of the 120 stage hops a token as ONE crossing: 321 beats on one port, E = 538 measured + 453 PHY/switch + 134 on-die = 1,125.
> - That crossing used to have no real circuit; LINK5 provides it at the same cost.
> - Moving the d+2 RX from W to E keeps the priced on-die leg at 67 cycles an end.
> - Against the no-hardware fallbacks [MODEL], LINK5 avoids about +135k cycles a token for relaying each hop through a TP peer (120 x 1,125), or about +160k for a TP ring.
>
> **Findings for the RTL / XDIE lanes:**
> 1. (Superseded by the lead 10-21: NB stays 80, and the h goes as 4 windows; see above.) s_0N now carries the whole h message on one endpoint, so its lep needs `NB` = 320 (40,960 B / 128 B; was 80 = one quarter per end slice). Otherwise the h ring beats must be funnelled to s_0N on die. The 652-cycle `H_MSG` window still covers 321 beats x 1.335 = 429 lane cycles.
> 2. **The host plane on s_7N has no host-side peer in any static-circuit plan.**
>    - s_7N sends THOST/TKD frames (types 3/4). A receiver accepts only ring, HOST and KS frames, so it takes them as a sticky protocol fault (`perr`, `ot_s81sl_slice_lep.sv` ~l.933).
>    - Under EN<->EN the peer s_7N faults. Under the old EN->WN the peer WN, which is HOST_EN 0, faulted the same way. The rank-asymmetric alternative faults on s_0N / pair B.
>    - So EN<->EN creates no new conflict, and it is kept. The asymmetric alternative was not taken because it fixes nothing.
>    - The host plane needs a lead decision: HOST_EN 0 on stage dies with host status carried in-band to a host-attached die, or a host circuit.
> 3. Copy-B circuits: if the reserve pair is placed on a TP endpoint (copyb_relay_plan's s_0S), its pair-B h RX shares ri with the TP pair-A RX. Then the calendar must keep copy-B h landings (land = 1) out of the TP RX windows, or the reserve pair goes to its own endpoint.
> 4. `calendar_ar_q4.json` / `calendar_mtp_q4.json` (TOK bench copies) were left as they were. Their slots and shifts equal the records.

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
