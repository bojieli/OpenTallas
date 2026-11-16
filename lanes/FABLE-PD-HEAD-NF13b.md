# FABLE-PD-HEAD-NF13b: r199 review-before-adopt, HEAD plan rp21z20NF13b (FREG rows on hd_st_k5 / hd_st_turn)

2026-11-16 02:25 PST. Technical PD only. Evidence labels: MEASURED = I read the file or ran the tool; REPORTED = from a
lane post.

## Verdict

**BLOCKING as composed at 02:00 PST; the rows themselves are right.** One defect, four table rows, same event:
the hand table edit (`head-99/lat8.py`) raised 8 of the 12 lanes that gained the FREG cycle. The other 4 are
`fixed_cycles: 1` lanes whose +1 the checker reports as PASS. With the table as it stands the next LATCHECK will print
329/329 while 4 lanes deliver table + 1 (static schedule, wrong beat at hd_serdes x3 and hd_host_w). Fix below, about
10 minutes, no new rows. Everything else is NON-BLOCKING.

Reviewed state: epyc7 `/srv/opentallas-scratch2/claude/head-99/prep21z20NF13b/prep`, plan sha256 7f397a5e0f8c (after
lat8; the bind of 01:51 ran on 9dfbafecee87), sidecar aef151594c56. Base NF13a 810a66fa536a / 26cf4a623e9c. A republish
and a gen.py run on this prep were live while I read it.

## 1 Do the rows match the signed n4 / turn_a form? YES (MEASURED)

- Plan diff NF13a -> NF13b: 2 rows (+2 notes). `hd_st_k5.clock.landing_ring_wreg = {buses [u_i, d_i, tx_i, rx_i],
  dsrep 8, freg true, write_chunk 16}`, `hd_st_turn ... {buses [d_i, u_i], dsrep 8, freg true, write_chunk 16}`.
  hd_st_n4 has the same four keys and values (4 buses); hd_turn_a the same with dsrep 4.
- Published wrappers: the 6 rings now read `.WFALL(1), .WREG(1), .DSREP(8), .WRITE_CHUNK(16), .FREG(1)` = parameter
  for parameter the n4 rings (and turn_a). Diff of `published/` against NF13a: only `ot_s81hd_st_k5.sv` (4 lines) and
  `ot_s81hd_st_turn.sv` (2 lines), each line adds `.FREG(1)` and nothing else.
- One key n4 has and these do not: `clock.pregrt_ff_hold: true` (hd_turn_a also lacks it and is signed). Not a form
  mismatch; see next delta 2.

## 2 K + 1, sched_lat + 1, LATCHECK

**K + 1 is consistent with the standing HEAD form (MEASURED), so the "unverified" strap is not a finding.**
- Sidecar diff: exactly 12 count-aligned ports, each K +1, sched_lat +1, freg 0 -> 1, `ports[].added_cycles` +1.
- Precedent: the 11-11 FREG-DECL event (`kw45/head_freg1111` sidecar vs `codex-head-1105`) did the same on the ports
  it declared: `chE0_t__0` (hd_turn_a) K -5 -> -4, sched 2 -> 3; `coll_WN3_u__0` K 11 -> 12, sched 2 -> 3.
- Loop identity sum(sched_lat) = sum(K + 1) on every two-edge loop of the sidecar: NF13a 152 of 152 at residual 0
  (10 with a FREG port), NF13b 152 of 152 (22 with a FREG port). K unchanged would leave residual 1 on 12 loops.
- Physical ties (`count_align_bind.strap_ties` run on both sidecars): 12 strap values change, all +2 mod 64
  (sst5 d_i 63 -> 1, u_i 10 -> 12, rx_i 21 -> 23, tx_i 54 -> 56; nst1/sst1 d_i 49 -> 51, u_i 11 -> 13; nst10/sst10
  d_i 46 -> 48, u_i 14 -> 16) = raw K +1 plus ring depth 1 -> 2. No other instance, no type declaration changes.
- Note, not a finding on this event: the comments in `clock_landings.py` (FREG-DECL-1, "raw K unchanged") and
  `test_ring_wreg._declare_freg` describe the other convention. The sidecars follow K + 1. See next delta 1.

**LATCHECK (MEASURED, run z20nf13b 01:51 on the pre-lat8 plan): FAIL 321/329, 8 lanes at +1.** Bind PASS, cohort
26/26, G0 1 error (the info line) and 233 warnings, same as NF13a.

12 lanes shift, each by exactly +1 delivered; the other 317 rows of `latcheck.tsv` are identical to NF13a.

| lane | table NF13a | delivered 13a -> 13b | fixed | 01:51 verdict | table after lat8 |
|---|---|---|---|---|---|
| m0S_tx | 74 | 74 -> 75 | 0 | FAIL | 75 |
| m0S_rx | 80 | 80 -> 81 | 0 | FAIL | 81 |
| coll_WN2_u | 36 | 36 -> 37 | 0 | FAIL | 37 |
| coll_WN2_d | 32 | 32 -> 33 | 0 | FAIL | 33 |
| coll_EN1_u / WS1_u / ES1_u | 22 | 22 -> 23 | 0 | FAIL | 23 |
| coll_HOST0_d | 10 | 10 -> 11 | 0 | FAIL | 11 |
| **coll_EN1_d / WS1_d / ES1_d** | 19 | 18 -> 19 | 1 | PASS (masked) | **19, not raised** |
| **coll_HOST0_u** | 13 | 12 -> 13 | 1 | PASS (masked) | **13, not raised** |

**F1 (BLOCKING).** The last 4 lanes carry `fixed_cycles: 1` inside a core. `gen_lane_latcheck --fixed-in-core` says the
wrapper transport must equal table - fixed: NF13a 18 = 19 - 1 and 12 = 13 - 1 (PASS as FIXED_IN_CORE, delta -1).
NF13b wrapper transport is 19 and 13, so the lane delivers 20 and 14 against tables 19 and 13. The checker passes them
because `lane_asbuilt_latency` accepts delta 0 before `reclassify` looks at fixed cycles: a fixed-in-core lane passes
at delta 0 and at delta -fx. lat8.py raised only the 8 lanes the checker named. Tell: the summary field
`fixed_in_core` reads 12 on NF13a (`latcheck.json`) and 8 on the 01:51 NF13b run: these four dropped out of it.

Fix (HEAD-100, this event): raise `latency.lanes[...]` `cycles`, `natural`, `clock_landing` by 1 on coll_EN1_d,
coll_WS1_d, coll_ES1_d, coll_HOST0_u as well (20, 20, 20, 14). Better: regenerate the table with the tool that wrote
it instead of the hand edit, and diff: exactly 12 rows +1. Accept test: LATCHECK 329/329 with `fixed_in_core` = 12 and
delta -1 on those four rows in `latcheck.tsv`.

## 3 dsrep 8 on hd_st_turn: CORRECT (MEASURED)

The NF13a wrapper (no `landing_ring_wreg` row; default CLAND-RING-LOCALITY reach) already built both hd_st_turn rings
with `.WREG(1), .DSREP(8), .WRITE_CHUNK(16)`. The NF13b row reproduces that and adds only `.FREG(1)`: "dsrep as
today" is 8. Same for hd_st_k5. The read side of both types is unchanged.

## 4 Does any released type get worse? NO (MEASURED)

- 24 of 26 published wrappers are byte-equal to NF13a; the two that change are the two that cannot pass on NF13a
  (-258.27 TT / 4,632 endpoints, REPORTED FABLE-FIX-HEAD-TYPES; their signed records are 11-03 builds).
- No strap value changes outside sst5, sst1, sst10, nst1, nst10. hd_st_n4 and hd_turn_a ties and rows are untouched.
- Die level: +1 cycle on 12 lanes, pre-approved. No other lane moves.
- Timing of the two types on this form: UNMEASURED until k5b prints (REPORTED: past prefloor after land_slots were
  aligned to the turn_a form). The reference is n4 +83.23 and turn_a +97.26 on the same ring parameters.

## Next delta (non-blocking)

1. Close the K convention in code: one RTL ring bench on a k5 crossing (TB_FREG form) with the tied physical K, q
   against sched_lat; then make the FREG-DECL-1 comment and `test_ring_wreg._declare_freg` say what the sidecars do.
2. `pregrt_ff_hold` on hd_st_k5 / hd_st_turn only if the first routed kit shows the face-register FF hold class
   (n4 signed with FF hold -10.75 on the port-overlay form).
3. LATCHECK: a lane with `fixed_cycles` in a core must pass only at delta -fx (observed kit stations aside), not at 0.
4. Gen check from lever 4: a type in `ring_hold.write_fall_types` whose ring has no `freg` is a gen error.
5. `freg_fix.py --apply` to do K and `added_cycles` itself (today fix2.py does it by diff against NF13a) and to print
   the lanes whose table must move, fixed-in-core ones included.

## Stop list

- Do not post READY+ADOPT on a 329/329 from the lat8 table: 4 lanes are +1 behind a PASS.
- Do not hand-edit only the lanes LATCHECK names; the set is the 12 lanes of the 12 changed sidecar ports.
- Do not take K + 1 back out; it matches the 11-11 FREG-DECL sidecars and the loop identity.
- Do not rebind on `src_head_pin_e594a73db756` with the 01:51 results: G0, bind, cohort, LATCHECK re-run there on the
  final plan sha.
- No change to hd_st_n4 / hd_turn_a rows or to dsrep in this event.
