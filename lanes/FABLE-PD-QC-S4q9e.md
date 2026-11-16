# FABLE-PD-QC-S4q9e: r199 structural review of QC plan events S4q9e and S4q9f

2026-11-16 13:25 PST, FABLE-PD-QC-S4q9e (Fable, read-only). MEASURED = computed by me from the files named, on epyc2
`/srv/opentallas-scratch3/claude/fable-fix-qc-knee-hc` (treeE / treeJ plan_of_record, bind/, gates/, log/). REPORTED = lane post.
The review started 09:40 and resumed 13:20 after a usage limit; binds finished in between, so bind results are final reads.

## 0. Verdict

| event | plan sha | verdict | reason |
|---|---|---|---|
| S4q9e | 00974ed8e7bd | **ADOPT-OK as rows; its own bind is not the adopt bind** | rows disjoint and sound; bind S4Q9EBQG ended RC 1 (37 errors, none from a collision) |
| S4q9f | 42b8ae2b7256 | **ADOPT-WITH-SPLIT** | its own bind S4Q9FBQG ended RC 1 (100 errors, stale R8 seed); the same rows bind clean as S4q9j. Split = release types now, hold the die-pair programme until the link calendar is recompiled |
| S4q9j | 79bca8d5b9bb | the bind to adopt | = S4q9f + su_l1 geom2 rows (4 leaves, 2 types). S4Q9JBQL: errors 0, r8rc 0, LATCHECK 1921/1921, hcparam mismatches 0, G0 2 errors (the 2 inherited faces rows) |

No BLOCK: nothing measured fails on a released type.

**Correction to the brief:** item (a), the W5 l9_c[0..63] station row, is NOT in S4q9e, S4q9f or S4q9j. The composer replaced it
by a bind-side st_a pad pin (section 2).

## 1. Collisions between (b) reset leaves and (c) fault stations: none

MEASURED, leaf-level JSON diff S4q9d (9c0f8e750f07) -> S4q9e: 20 leaves.
- (b): `clock.landing_local_resets` + `clock.reset_tree_anchor` on coll_core, native59, tt_ctlm (6 leaves).
- (c): glue `reach_homes` + `internal_stations` (2), `fixed_cycles` on 3 lanes (3), 9 latency fields (9 -> 12, 9 -> 12, 9 -> 10).
- No type, lane row or region is touched by both. Answer to CBGLUE: FABLE-DIE-QC's rows do not touch glue or the 3 lanes' cycle rows.
- The two sets do meet on the same 3 lanes at opposite ends: the source landing cells (coll_core `u_cland_fstart_flt_o` /
  `_fltv_o` on leaf fstart_0; tt_ctlm `u_cland_fstart_flt_o` on fstart_2) get a local reset copy, the glue end gets stations.
  The leaves add 0 cycles, so the lane counts are set by (c) alone. The 3 lanes are in no latency group (12 groups unchanged).
- Bind S4Q9EBQG: LATCHECK 1921/1921 PASS; 1 R8_STALE = `sys_face.io_shared_fault` bound 12 against table 9 (the planned +3 with the
  S4q9c seed; gone in the J bind with a derived seed).

## 2. Does (a) satisfy the per-region check? Yes, by a pin, not by a station row

`qc_fabric_transport.py` line 180-183: `nbo[r] = E[r] + delta(u_fup.l9_c[64r..64r+63])`, error unless `nbo[0] == max(nbo)`.
MEASURED in the S4q9c derived R8 table, W5: regions 0-3 land through st_a fe (bound 17), regions 4-7 through st_b fe (bound 10).
The pin (`bin/pinpad_rel.py`, `gates/pin_S4Q9EBG.json`, identical to the R0 run) pads only the st_a leg: fe +3 on E0-E5, +5 on
W0 / W2 / W4, +6 on W1 / W3 / W5; ctl +3 (unchanged). 168 members, 579 pad cycles; against the old pin (fe +1) that is about
10,062 more pad flops over 12 fe landings.
- Result: no PARAM_REGEN from qc_fabric_transport in S4Q9DBQG, S4Q9EBQG or S4Q9JBQL; `param_regen.json` written; hard_core_param
  mismatches 0 on 20 types. The 48 HARD_CORE_PARAM_WRAP rows are gone.
- Weakness: the pin is a bind-side R8 extra table tied to the S4Q9BQ relation. Any later change of a st_a or st_b fe leg breaks
  it again (it already broke once on the knee stations). Next event: make it structural (the regen pads nb_oc of region 0 itself,
  or the station row). Not blocking.

## 3. Cost

| item | cycles | reach (MEASURED from the rows) |
|---|---|---|
| (b) 17 reset leaves, 80 consumers | 0 | relay -> leaf max 365.9 um (tt_ctlm rst_rl_67 -> fstart_2), all <= 405; largest group 17 consumers; every leaf inside its outline, none in a macro + halo |
| (c) 3 fault chains, 214 flops | +7 on 3 sticky lanes | hops 297.0 / 296.8 / 280.4 um |
| S4q9f: 17 d2d seam chains in glue, 1,768 bits, 5,304 flops | +3 on 17 lanes = +51 | hops 281.7 (14 chains), 294.2, 322.1, 325.8 um |

Plan lane cycles (sum of latency.lanes): S4q9d 21,640 -> S4q9e 21,647 -> S4q9f / j 21,698. Latency groups equal in all.
LATCHECK passes as bound on E, F and J. Token latency: not simulated by me. The 17 seam lanes are the QC <-> KV native link:
+3 cycles needs both dies' link calendars recompiled (REPORTED by the composer: "programme explicitly unqualified", pair image
waits on the KV-HG1 bind). This is the split.

## 4. Congestion, density, pin access (glue a6 placement, flops only; no GRT read)

- Fault stations at x 765.6: 0 flops in a 50 x 50 um box at each of the 3 sites; home rect holds 3,814 flops in 51,360 um2. Room.
- Seam station rows y 611.7 / 893.4 / 1175.1, x 0-400: 32 / 710 / 1,499 flops there now, plus 1,768 new per row. Flop area stays
  under 15 % of the band. Room.
- **Watch, glue:** `bus:d2d_rom__x3` (524 bits) station 1 is at (298.08, 1187.58) = exactly on the W halo edge of the
  embed_prov `codes` SRAM (halo box x 298.08-478.0, y 1101.6-1188.02) and 0.44 um inside it in y; x3_generation and x3_identity
  station 1 share x 298.08. 585 station flops stack on that macro edge, where 1,193 flops already sit in x 248-298, y 1163-1245.
  Same class as the S4q9g su_l1 geometry FAIL, but on the edge, not inside. Read legalisation displacement and the SRAM W-face
  pin access on the first glue kit; if it fails, move the three sites 20 um west. Only glue carries these rows.
- coll_core leaf fstart_2 (199.2, 198.7) sits in a 31-um channel between two SRAMs (1 consumer). Watch only.
- Released types: no row of E or F changes a signed or released type other than glue, coll_core, native59, tt_ctlm.

## 5. Missing for the ~60 waiting types

1. Adopt + data-pack of S4q9j: failure_breakdown 13:2x shows QC 7 / 127 signed, 25 flow errors, 6 kit input missing. The
   kit_istations classes (sle_fe_v1 x2, sle_fe_v3, slw_sc_v2, sle_sc_v1 x2, slw_su_c) all close on the event (988 per_bit rows
   complete) and on nothing else. I found no ADOPT post for J after its 11:45 gate pass: 1 h 40 min idle.
2. HARD_CORE_PARAM_ALL: 36 rows on the E tree (6 st_a_v1 types HI_PAD die 15-17 against hardened 0, 3 su_c MIF). On the fallback
   S4q9d too, so not from this delta. J clears them with the MIF1 profile; the 6 st_a_v1 hardened views must be confirmed built
   with the die values before they count.
3. FABLE-DIE-QC clock rows (52 types, 15,391 ports, seam 110 -> 180 ps) are not in any of E / F / J. They change the kit SDC of
   52 types: compose them into the next event before the volume relaunch, or 52 types are built twice.
4. 2 inherited G0 errors (sl_W5_fw.W, coll_f4.E 72 pins / 10 um) still open.
5. glue item 3 (d2d_rom -64..-152, ~400 endpoints) is what the seam rows answer; the proof is the first glue kit GRT-stage TT.
