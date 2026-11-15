# FABLE-CLOSURE-STRATEGY 2026-11-15 00:3x PST: technical closure levers for S81, HEAD, QC, KV

Read-only review. Technical physical design only. HBM is parked and not covered. No job, plan or kit was touched.

Sources: the seven Fable reports since 21:21 (FABLE-METHOD, PD-S81, PD-HKQ, QC-CB, ROUTE, PD-S81-2250, PD-HEAD-CLK), the FABLE-KVOVF post (22:59; `lanes/FABLE-KVOVF.md` and FABLE-GENBUG do not exist on the hub), `lanes/PLAN-TIMING-AUDIT-1115/`, the queue from 22:20 to 00:20, and my own read of the S81 die clock run that finished at 23:03 (epyc8 `/srv/opentallas-scratch2/claude/die-grt0-s81/s81/b3x2d`), plus the HEAD plans on epyc7 `head-remap-1/`.
`failure_breakdown.py` (00:13) has no technical class beyond "congestion 1, timing after route 1-2"; it was not useful for this review.

MEASURED = read tonight from a log, plan, record or my own script. INFERENCE is marked.

## 0. What the reports and lanes miss, in one place

1. The S81 die clock result landed at 23:03 and nobody has read it (no RESULT post by DIE-S81-GRT0). It settles two open questions and raises one (levers 1, 2, 5).
2. Two S81 clock fixes are in flight that exclude each other: 7,796 early core taps (C1, in B6c) and the 450 ps budget (PD-S81-2250 verdict a). I found no COORD ruling that picks one.
3. The plan timing audit's "boundary arc" rule gives false FAIL rows on the QC tile cores (22 of the 32 QC rows), and DIE-QC-103 has been asked to fix those rows.
4. The element halves, which sit in all 216 col types, are last in the S81-RESIGN-DEEP queue and not started.
5. The same wrong landed check that FABLE-PD-HEAD-CLK found on HEAD ran on S81 tonight.

## 1. Levers, ranked by types or dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | One clock budget decision for col and leaf: 450 ps with grid-tap split; C1 early taps withdrawn for cores of 236-301 ps | 216 col + 79 leaf | DIE-S81-92 (B6f), COORD ruling |
| 2 | S81 | Kit tap windows for col from the built die clock (related grid pairs), not the 179-208 ps per-port values | 216 col | DIE-S81-92, KIT-OPS-5 |
| 3 | S81 | Re-sign the two element halves first (boundary spread, measured insertion) | 216 col | S81-RESIGN-DEEP |
| 4 | QC | cb family: head-hop patch needs an owner and its proof; do not act on the audit rows or on the 483 -> 568 tap change | 16 | TYPE-QCCOLLN, DIE-QC-103 |
| 5 | S81, QC | Die landed check: both-edge readout and count-aligned judgement, then K / DEPTH / lane latency from the built clock | 2 dies (lane latency gate) | DIE-S81-GRT0, DIE-QC-GRT0-2, die owners |
| 6 | KV | hg / hgi: `OT_KEEP_WIRES = ti_b` before any other form | 9-16 | TYPE-KVHGI2, KV-102 |
| 7 | S81 | Release the three col GRT-only A/B proofs from the col stop | decides the col floorplan for 216 | TL-COLH9R0P6, S81-COL-STREET, TYPE-COLH9R1 |
| 8 | HEAD | hd_host_e: adopt only a plan with the signed u_epc model and no 330-400 ps tap; bank move form decides | 1 type (last hard HEAD type) | HEAD-REMAP-1, HEAD-99 |

### Lever 1. S81 clock budget: two fixes in flight that exclude each other

Evidence (MEASURED unless marked):
- B6c carries C1: 7,796 early core taps on 220 types, common 250 ps (FABLE-PD-S81). The offset is capped at 250, so the element halves stay 41-80 ps late.
- PD-S81-2250 verdict: budget 450 for col and leaf by per-type override. 164 of the 257 audit FAIL rows are cores of 205-271 ps with no tap, and pass at 450 with no tap at all.
- My read of the S81 die clock (B3x2d, 20,647 taps, 6,255 of them early core taps): the tree is 190 inverter stages deep, tap insertion 1,108 to 11,631 ps. Every early core tap is one more die landing with its own offset. The 7,796 C1 taps are in no die proof.
- col_h10_r1 form fa: tap trees 218-519 ps against the 250 target, 16 grid taps for 21,664 flops, three taps at the 3,000 cap (PD-S81-2250).

Root cause: cores of 236-553 ps internal depth inside types balanced to 250. C1 answers it with die landings; the 450 budget answers it inside the type. Doing both doubles the die clock load and leaves two reference points per type.

Fix:
1. COORD rules (a): `insertion_target_override` 450 on the 12 col bases and the leaf types in B6f.
2. In the same event, remove the C1 rows for cores at or under 301 ps (they return to grid taps). Keep an early tap only where depth exceeds 450 + 40: gb_he, if its 555 ps is confirmed against the plan lib sha.
3. Split every grid tap over 1,500 sinks (`tap_max_sinks`; 186 col types have none set).
4. Do not run b6f1 as written (raise to liberty maximum, FF by ratio): withdrawn by its own author.

Proof: col_h10_r1 to CTS on that plan. Pass: tap mean spread under 80 ps, no tree over 490 ps, FF hold before repair under 1,500 endpoints.

### Lever 2. Col kit tap windows are about twice what the die clock delivers

Evidence (MEASURED, my script over `proof/tap_arrivals_{TT,FF}.json` of the 23:03 run):

| grid taps of one partition, max minus min arrival | TT | FF |
|---|---|---|
| median over 397 partitions | 68 ps | 64 ps |
| p90 | 100 ps | 96 ps |
| worst col partition (216 `fW*` / `fE*`) | 139 ps | - |
| worst of all (bk_sel) | 263 ps | 244 ps |

- The col kits carry early source latency of 179-208 ps on every grid tap, with no shared-path credit between taps. On col_h10_r1 that window alone makes 7,281 of the 12,948 hold endpoints (PD-S81-2250 cause B).
- The 23:3x ruling puts measured related-pair windows into B6f for the leaf types only. `clock.tap_window` is null on all 216 col types.
- The run wrote `kitwin.json` at 23:01 (per-port values, same directory).

Root cause: col kits take the die per-port default; the default is older than any built S81 clock.

Fix: DIE-S81-92 writes related-pair windows for the col types too, from this run, with `die_sta_related --kit-window-related` (the script is already in the S81 source, KIT-OPS-5 22:28). Use grid-to-grid pairs. Do not copy `kitwin.json` per-port values blindly: bk_sel shows 200-300 ps there because core taps are mixed in.

Limits: the run is on plan B3x2d, not B6. Re-run the die clock on the B6 plan once it binds; with lever 1 the tap set shrinks, so the numbers should not get worse (INFERENCE).

### Lever 3. Element halves first in S81-RESIGN-DEEP

Evidence (MEASURED, PD-S81-2250 and the lane handoff of 00:13):
- `qxpq_w10_gb_hw` / `gb_he`: internal sink spread 191 / 154 ps, `go_tag` pin window 557 ps at FF. No tap value fixes a spread.
- col_h10_r1 fa: setup repair ran 7,516 s and left -222.8 ps on 3,375 endpoints at `u_e8_u_w/go_tag[1]`.
- Eight halves per col type, 216 types. They are also 864 of the 954 UNMEASURED audit rows together with front_roots and the ROM.
- S81-RESIGN-DEEP has built only idx_tx_n32 forms (one type, bk_sel). The halves are "not started": kits exist only in the AGIdock archive and need regeneration.

Fix: reorder the lane: halves first, then kp4_dchn, bksel_q, idx_tx_n32. Targets for the half re-sign: boundary-register spread at most 60 ps, insertion at most 400 ps, `go_tag` setup + hold window under 250 ps, and an `insertion.json` with the boundary mean per corner, stamped with the module name (the shared-directory defect of the audit).

Until the halves are re-signed, a col type can close hold but not setup at `go_tag`. This is the longest pole for 216 types and it is one core pair.

### Lever 4. QC cb family: one patch, and two follow-ups that are wrong

Evidence:
- FABLE-QC-CB (MEASURED): re-siting the head-hop cells takes GRT overflow 102,780 -> 2,480 and the D3 bus from 514 violations at -770 ps to 0 at +452 ps. The fix is in `core_input_chain.tcl`; the hold residue is in `core_input_anchor.tcl` (0 of 6,148 pipe registers anchored).
- I found no TYPE-QCCOLLN post after 20:03. The patch and its one-build proof have no visible owner.
- Audit rows (MEASURED, `full2_QC.tsv`): 18 rows `qfd_tile_nk_a0c` and 4 rows `qfd_tile_nl_a0c` FAIL with "clk->q 923 + setup 0 leave -90 ps". The 923 ps is from the clock pin and contains the 733 ps internal depth. With the planned early tap (483) and parent flops at 250, the tile output leaves 190 ps after the parent edge: 643 ps remain. These 22 rows are an artefact of the rule, not a core fault.
- The same table gives measured boundary depth 733.2; 733 - 250 = 483. The planned tap is exact. The kit warning "effective 335" uses the liberty maximum 818.

Wrong or conflicting, to stop:
- FABLE-QC-CB item 5, second part (early offset 483 -> 568): withdraw. It follows the liberty maximum. PD-S81-2250 section 2 measured that this costs setup and buys no hold.
- The METHOD lever 2 order to DIE-QC-103 for "32 failing rows": 22 need no change. The real ones are `qfd_dv_s5_sc2_leaf` (7 rows + 2 variants; tap declares 335, measured 406): set the tap from the measured depth.
- PLAN-READERS-1: the arc rule must subtract the measured depth on the launch side and add it on the capture side when the other end is a parent flop. The sum rule is only valid core to core. The HEAD row "hd_host_e -595" has the same defect.

Fix: assign CB-HEADHOP + CB-LOCKUP to TYPE-QCCOLLN (or a new lane) now; proof as written in FABLE-QC-CB section 3 (about 2.5 h, no plan change). DIE-QC-103 keeps only the y_o23 stations (already in S4e).

### Lever 5. S81 and QC die landed check repeats the HEAD error

Evidence (MEASURED, S81 `CHAIN.log` 23:03):
- `proof TT landed pairs 1,272,578 setup -3,126.79 ... landing window_ps 416.5 verdict FAIL`: the half-period model.
- `TTA_TT ... fall taps 0 fall nodes 0`: rise-only readout.
- Synchronous classes are sound on setup: intra +420, seam +364 ps TT. GRT overflow 0, layer use 0.8-4.3 %.
- FABLE-PD-HEAD-CLK measured on HEAD that the same clock judged count-aligned gives 427 of 427 crossings fitting, and that 191 of 427 lane latencies differ from the plan.

Root cause: `die_sta_related` is called without `--count-align`, and the arrival readout has no fall rows. S81 phase between regions reaches 3.9 ns, so the cycle counts in the plan cannot be right by chance.

Fix (tool calls on existing data, no build):
1. DIE-S81-GRT0: both-edge readout on the b3x2d clock, then the count-aligned planner, as HEAD fix 1. Report crossings that fit, worst margin, and how many lane latencies and ring DEPTH values differ from the plan.
2. DIE-S81-92: take K, DEPTH and lane latency from that run into the bind of the plan being adopted, then LATCHECK. This is the blocking lane-latency gate, so it belongs before volume col and leaf builds, not after.
3. DIE-QC-GRT0-2 has a count-align waiter; check that its readout has fall rows before quoting DEPTH.
4. Do not adopt DEPTH 8 anywhere from a rise-only run (HEAD-99 already holds this for hd_tile).

Also read with care: `typepairs.json` lists "intra skew 300 ps, seam 356 ps". All 120 worst rows I checked pair an early core tap with a grid tap in the same region. They are raw arrival differences that contain the intended early offset. They are not die clock skew. DIE-S81-GRT0 should re-report the seam class for grid-to-grid pairs only; that number, not 60-90 ps by assumption, sets `seam_ps` for the port-hold contract of the 23:3x ruling. The FF "kit contract needs 332.65 ps against 40" line has the same mix.

### Lever 6. KV hg / hgi: the synthesis fix comes before every route form

Evidence (MEASURED, FABLE-KVOVF): yosys folds 6 pipeline banks of 1,559 bits into 3; one chain then feeds both head columns over about 1.1 mm. Setup at CTS -586 (hgi_v2), -572 (hgi_v1), -753 ps (hg). `OT_KEEP_WIRES = ti_b` restores 6 banks (registers 32,599 -> 37,276).

Conflict: TYPE-KVHGI2 still runs m7a and m7hg_g without the keep. They can answer the overflow question only; they sit at -480 to -540 ps setup and cannot sign off. The wave launched hgi_v1 and hgi_v4 on kvgeom5 / kvgeom6 at 00:03-00:13, also without it.

Fix: KV-102 puts the keep into the hg / hgi kit environment as soon as one k_ form passes placement timing (due about 02:00). No hg / hgi launch without it. The overflow fix (M7 closed over the 16 head cores, no antenna step) rides on the same kits.

Class check for the other dies (INFERENCE, not measured): a kit preflight that compares the register count per RTL bank before and after `opt_merge` and fails on a folded bank of 64 bits or more. `reg_fanout` does not see this case because each merged flop has few loads.

### Lever 7. Three col proofs are held by the col stop, and they do not depend on B6

- TL-COLH9R0P6 (00:15): fd GRT A/B with the M8 grant is ready from `3_place.odb` and waits "until B6 is adopted".
- FABLE-ROUTE lever 1: col_h9_r1 cl49d7a23e from its `4_cts.odb` with `-allow_congestion` to detail route. The 26,865 figure is 4 gcells and 5 nets at one core edge. Not run (TYPE-COLH9R1 process gone at 22:50).
- S81-COL-STREET base / street A/B: kits generated 23:04, no run log yet.

These are GRT or route runs on existing databases. Their answers (is col_r1 a wall or an edge case; does M8 or the street carry the 2,271 N-strip bits) decide what the col floorplan event contains. Holding them until B6 binds puts the answer after the event it should shape. Release the three; keep the stop on volume col kits.

Also not dispatched from FABLE-ROUTE lever 3a: layer adjustment 0 on M6 and M7 above cores (the blanket 0.25 is the second derate on the only free layer). One GRT on a col_r1 placed database measures it.

### Lever 8. HEAD hd_host_e: check the plan that is adopted

Evidence (MEASURED, epyc7 `head-remap-1/`, files of 21:06-21:49 PST):
- `rp21z20.json` still has the tap row "u_epc tap from the pin-referenced arcs (L 330-400 ps)". PD-HKQ measured that L = 350 gives output setup -435 ps on 509 pins and input hold -261 ps on 824 pins. The audit table "HEAD (rp21z20)" was run on this file.
- `rp21z20N.json` has no such row, but its u_epc lib is still `results/head_he_epc_h2_1110/` (the stale model).
- HEAD-99 has the repoint overlay and two private forms chained: S (signed lib only) and A (S + banks 5-8 moved about 230 um nearer the pins).

Fix: HEAD-REMAP-1 adopts only z20N + the repoint, and checks two things in the prepared kit: lib sha f663e343 and no u_epc early tap other than the measured 421-432 ps reference. Form A is the closing form: with the signed model the path is still -173 ps and the wire must drop from 456 to at most 325 ps.

## 2. Dispatched fixes that are wrong, unproven or in conflict

| item | state | problem | action |
|---|---|---|---|
| C1 early core taps (B6c) and budget 450 (PD-S81-2250) | both in flight | exclude each other (lever 1) | one ruling; C1 rows out for cores <= 301 ps |
| b6f1: tap rows raised to liberty maximum | script exists | boundary flops 41 ps early; setup worse | do not run |
| QC early tap 483 -> 568 on the tile cores | proposed for S4c | measured depth 733 makes 483 exact | withdraw |
| QC audit FAIL rows as a work list | ordered to DIE-QC-103 | 22 of 32 are rule artefacts | only the sc2_leaf rows |
| PG keep-out rollout "proven" (00:2x ruling) | on for all new kits | proof is a cell count under PG crossings; no route has passed. 16 of the 48 located DRT-0255 kits already carried `OT_PG_TRACK_TRUTH`; the failing nets are type ports, first station ranks and ring select cells; 44-1,669 fixed cells stay under crossings | keep it on, but relaunch only the 10 keyed kits; no leaf volume until one passes detail-route iteration 0 |
| Port-hold contract at -60 to -90 ps | ruled 23:3x | value assumed; the S81 die run can measure it (lever 5) | set from grid-to-grid seam pairs |
| KV m7 forms without the keep | running | cannot sign off | route answer only |
| S81-RESIGN-DEEP order | idx_tx_n32 first | 1 type before 216 | halves first |
| HEAD DEPTH 8 on 165 rings | held by HEAD-99 | rise-only | correct as held |
| S81 die GRT "Total resource -517,968,102, usage -13.21 %" | in the log | 32-bit sum overflow in the report line; per-layer rows are valid | ignore the total line |

## 3. Stop list: technical dead ends

S81
- Reading the S81 landed FAIL (-3,127 ps) or the 300 / 356 ps typepairs rows as clock failures.
- More per-core early taps on col or leaf; tap values taken from the liberty maximum.
- Hold repair, density, layer or max-wire forms on col types before the window (lever 2) and the tap split (lever 1) are in the kit.
- Col builds that expect `go_tag` setup to close before the halves are re-signed.
- Lockup latches or hold padding on the lane-pad ranks; M8 grant as the answer to the col N strip before the fd A/B says so.
- More stations in leaf feed-through slots; leaf routes on kits with `OT_TAP_WINDOW` 68-162.

QC
- The t00 + t11 mirror; any cycle added to the D3 links; allow-congestion relaunches of cb kits before the head-hop patch.
- Tile early-tap or budget changes taken from the audit arc rows or from the kit's "effective 335" warning.
- Waiting on S4 to cure fw / sc / stm: they stop earlier on strap pins (DRT-0206) and the hold accept test.

KV
- Any hg / hgi form without `OT_KEEP_WIRES = ti_b`; column re-floor, M9, density or extra congestion iterations for hgi.
- Moving the pcc tap off the internal-delay reference.

HEAD
- Any u_epc tap shift; a build from a kit that carries lib sha 8aad8716.
- A die H-tree or mesh; partition or core changes justified by hop deltas against 450 ps.
- K, DEPTH or latency tables from an earlier clock, and DEPTH from a rise-only readout.

All dies
- Die GRT wirelength read as die-top wire; feed-through nets sent to die detail route.
- Unchanged relaunch after the same net failed in the same place.

## 4. Not checked

- Whether COORD has ruled on the 450 budget outside the queue lines I read (22:20-00:20).
- The split of intended early offset against real error in the S81 core-tap pairs; I measured grid taps only.
- QC die run (clock kit stage since 22:48) and KV die route (route stage started 00:12): no result yet.
- The cb patch, the keep forms, the col A/Bs and hd_host_e form A have no result yet; every "closes" above rests on the cited what-if, not on a routed build.
- A wave-wide flow error appeared at 00:03-00:14 on all four dies (`ModuleNotFoundError: No module named 'ot_store'` at place). It is not a design result, but no wave kit passes place until it is fixed (KIT-OPS-5).
