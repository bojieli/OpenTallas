# FABLE-PD-QC-S4q9: r199 review-before-adopt of QC event S4q9 (S4q8 + QC-MISC delta)

2026-11-16 02:45 PST, FABLE-FIX-QC-HCFE. Read-only on DIE-QC-103's tree. Scripts and outputs: epyc9
`/srv/opentallas-scratch2/claude/fable-fix-qc-hcfe/q9/` (d1.py diff, d2.py / d3.py checks, knee_s4q9.tsv / .out).
Subject: epyc9 die-qc-103/treeA plan_of_record `zz_s29_qc103_s4q9.json` against `zz_s29_qc103_s4q8.json`.
MEASURED = computed by me from the two plan files and treeA tools. State when written: first bind S4Q9BR and G0 running;
no bind gate is reviewed here.

## 0. Verdict

**S4q9: BLOCKING as composed, for 34 types; the fix is one tool run.** The plan's own checker
(`tools/die_plan/istation_knee.py`, the Python mirror of the kit rule) reports **113 per_bit chains over the 403 um kit
limit in 34 types**. The kit stops `3_3_place_gp` on that rule ("internal station knee needs a plan depth change";
the same line is in the pinned tree `src_qc_pin_e594a73db756`, kit_istations.py 396). 89 of the 113 are rows that
S4q9 just completed with `leaf_um` (21 types: the whole fe / sc / su_c set of this delta); 24 are older fw / su_l1 rows
(13 types) that carry the same miss since S4q4c. Everything else in the delta is sound.

## 1. What changed (MEASURED: 1,322 values, 27 types, nothing outside partition_types)

| item | values | check | result |
|---|---|---|---|
| (c) `leaf_um` on per_bit internal stations | 268 rows, 21 types | rule (out bus: from_um, in bus: to_um) holds on 268 / 268 and on all 988 per_bit rows; 0 rows without leaf_um now | rule OK; **depth not OK**, section 2 |
| (b) sle_su_l0__cl7a55c676 early taps u_lane0..3 | 16 | TT 392.5 -> 397.07 / 397.09 / 397.47 / 393.41, FF 321.0 -> 327.17 / 326.44 / 322.45 / 319.31 | shift at most +5.0 TT, +6.2 FF; inside any window; non-blocking. DIE-QC-103's own caveat on the l0 / l1 record identity stands |
| (a) PHY contents rows: lef + origin_um | 6, 3 types | both LEF files exist in treeA and in the pinned tree (302,545 and 446,082 bytes); SIZE 1563.570 x 2320.056 inside the 1563.84 x 2324.16 outline at origin (0, 4.104): top edge 2324.16; 777.6 x 777.6 = outline | OK |
| (d) cbn_q00 rsf station out of cl_rsf_i | 2 regs + 1,030 bit sites, 2 types | 515 sites per type moved by exactly +108.0 / +86.4 um in x, 0 in y; moved-site box against all 9 hard cores + 4.32 um halo: 0 overlaps; no landing band under it; no other station within 30 x 10 um; hops 207.8 / 194.4 and 186.2 / 216.0 um | OK, closes the r242 finding |

hc: no hc type is in the delta (the S4q8 review stands). fe_v1: its station rows (regs_um, counts) are unchanged; only
leaf_um was added.

## 2. Finding F1 (blocking): per_bit chains over the kit knee limit

`istation_knee.py treeA zz_s29_qc103_s4q9.json`: chains 988, types 47, **FAIL > 403: 113**, margin (400, 403]: 7.
(On S4q8 the tool cannot run: KeyError leaf_um. The missing key was hiding these rows from the check.)

Why a simple length / (n + 1) read misses it: the kit uses one integer split for the whole bus on the bounding box of
all its pins. Example sle_fe_v1 x_stm_i: 544 bits on the W face at y 1,339-1,440, leaf at the outline centre
(311.04, 915.84), ONE station: straight estimate 417 um, kit rule 523.87 um.

| family | failing chains | worst (um) | buses | stations to add (to <= 400) |
|---|---|---|---|---|
| slw_sc (5 types) | 15 | 728.86 | x_fe_o, x_fe_i, flt_fe_i | 15 |
| sle_sc (4) | 10 | 699.30 | flt_fe_i, x_fe_o, x_fe_i | 10 |
| slw_fe (5) | 34 | 518.90 | x_stm_i, hr_eo, x_fw_o, x_st_b_i, ard_ei, x_stm_o, x_stm_p1_i, treq_eo | 34 |
| sle_fe (4) | 23 | 523.87 | x_stm_i, hr_wo, x_st_a_i, x_st_b_i, ard_wi, l9_eo, x_stm_p1_i, treq_wo, x_sc_i | 23 |
| sle_su_c / slw_su_c (3) | 7 | 456.38 | x_su_l0_i, x_ctl_o, x_su_l1_p1_o | 7 |
| sle_fw / slw_fw (11, older rows) | 22 | 599.82 | dr_ei / dr_wi, x_ctl_i | 22 |
| slw_su_l1 (2, older rows) | 2 | 431.65 | x_su_c_i | 2 |

Every failing chain needs exactly one more station (need_limit = stations + 1 on all 113). 179 of the 268 new rows pass.

Second point on the same rows, non-blocking: on the 9 fe types 201 of the leaf points are the outline centre and the
type has no hard core there (contents u_fup / u_pstn carry no box). The stations then converge on a point where no
cell is pinned. It is consistent (in and out buses meet at one point) and the S3R routed fe_v1 failed on exactly these
unstationed runs, so the rows are the right structure; whether placement brings u_fup to the centre is a read on the
first placed fe kit, not a plan defect.

## 3. Fix (DIE-QC-103, about one bind)

1. `python3 -I -B tools/die_plan/istation_knee.py <treeA> zz_s29_qc103_s4q9.json out.tsv --fix zz_s29_qc103_s4q9b.json report.json`:
   adds the fewest stations that bring each failing chain to <= 400 um (113 stations), re-spaces regs_um and sets lane
   fixed_cycles = source out-stations + destination in-stations on every lane through a changed type. Then
   `gen.py latency --inplace`, G0, bind chain as S4q9b. Re-run the checker on S4q9b: pass = FAIL 0.
2. The running S4q9 bind can finish for its report; it does not see this rule (the stop is in the kit placer).
3. If the chain must not wait: adopt S4q9 only for the 6 types it fixes without per_bit rows (su_l0 cl7a55c676,
   phy_serdes, phy_serdes_b, phy_ucie_kv, cbn_q00 x2) and keep the 34 held. Not recommended: one more event.

## 4. Stop list

- Do not release the fe / sc / su_c / fw / su_l1 types on S4q9 as bound: each stops at place on the knee rule.
- Do not raise the 403 um limit: it is the one-cycle reach of a station hop.
- Do not hold S4q9 for (a), (b), (d) or for the outline-centre leaf point.

## 5. Not checked

- Any bind gate, LATCHECK, G0 of S4q9 (running).
- A kit log with the knee stop on S4q6d fw types (none found in the S4Q* place logs on epyc10; the fw miss is from the
  plan tool only).
- plan_gate_pre GEOM on S4q9 (PLAN-GATE-PRE's tool); my rsf check is the box test in d2.py.
- Latency effect of the 113 added cycles on the token schedule (the latency table carries them).

## 6. Recheck on S4q9b (r199 verdict), 2026-11-16 02:45 PST, QC-HCFE-O (Opus successor of FABLE-FIX-QC-HCFE)

Knee only, as scoped. Plan: epyc2 kw45/src_qc_pin_e594a73db756_q9/physical/die_plan/qwen_compute/plan_of_record/
zz_s29_qc103_s4q9b.json, sha256 dcf35395a229a1e1... (byte-equal to die-qc-103/plans9 copy). Checker: that tree:
tools/die_plan/istation_knee.py. Outputs epyc2 /srv/opentallas-scratch2/claude/fable-fix-qc-hcfe/q9b/knee_s4q9{,b}.{tsv,out}.

| plan | chains | types | FAIL > 403 | margin (400,403] | unchecked | worst um |
|---|---|---|---|---|---|---|
| S4q9 (same tree, control) | 988 | 47 | 113 | 7 | 0 | 728.86 |
| S4q9b | 988 | 47 | **0** | **0** | 0 | 399.98 |

Diff of the two tables: exactly the 120 chains that were > 400 um (113 fail + 7 margin) got +1 station each, in 34 types; no
other chain changed station count. **Verdict r199: S4q9b NON-BLOCKING on the knee rule (F1 closed).** Sections 1 (a), (b), (d)
stand. Not checked here: bind / LATCHECK / hcparam / G0 of S4q9b (DIE-QC-103 gates), latency effect of the 120 cycles.
