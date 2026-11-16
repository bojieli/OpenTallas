# FABLE-PD-QC-S4q9k: r199 structural review of QC plan event S4q9k item (a)

2026-11-16 13:50 PST, FABLE-PD-QC-S4q9k (Fable, read-only). All files on epyc2, L = `/srv/opentallas-scratch3/claude/fable-fix-qc-knee-hc`.
MEASURED = computed by me from the files named. EMULATED = the real R8 derive tool run by me on the J bus groups with the
24 lane bounds raised by hand (the K bind was 15 min in when I wrote this: BR ends about 14:30, BQ about 15:28).
Plan `treeJ/.../plan_of_record/zz_s29_qc103_s4q9k.json` sha c73c1acfd1ee.

## 0. Verdict: ADOPT-WITH-SPLIT (no BLOCK)

Condition: the real BQ bind must show errors 0, r8rc 0, LATCHECK PASS, hcparam 0. The emulation says it will (section 1).
Split: of the 15 changed types, 8 are also in the FABLE-DIE-QC clock-row list. Release the other 7 on K; hold the 8 until
the clock rows (b) are in the plan, or they are built twice (section 4).

## 1. W5 nb_od regen without the pad pin: PASS expected; the ctl +3 is NOT absorbed

`qc_fabric_transport.py` 177-183: `rd[r] = E[r] + delta(u_ctl.r_d[64r..])`, `nbo[r] = E[r] + delta(u_fup.l9_c[64r..])`,
error unless region 0 is the latest in both. delta = landed - as-built. Regions 0-3 come through st_a, 4-7 through st_b.

EMULATED derive (`land_r8_derive.py derive` + pin_r8_v2, same arguments as the chain; control on the unchanged J bus
groups reproduces the F-seam table exactly, 9050 members):

| W5 member | F-seam table (bound / pad / landed) | J with pad pin | K emulated |
|---|---|---|---|
| st_a ctl (r_d, r_v, l9o_v ...) | 9 / 11 / 20 | 9 / 14 / 23 | 12 / 11 / 23 |
| st_a fe l9_c | 17 / 0 / 17 | 17 / 6 / 23 | 23 / 0 / 23 |
| st_b ctl r_d | 8 / 0 / 8 | same | same |
| st_b fe l9_c | 10 / 0 / 10 | same | same |

- All 168 pinned members (108 ctl + 60 fe, 12 slices): K emulated landed == J pinned landed, 0 differences. So the regen
  sees the same deltas as the adopted J bind: RD_PAD regions 4-7 = 2 (W), 14 (E); NB_PAD regions 4-7 = 0 (W), 12 (E).
- Why the pad stays 11: the base r8 derive aligns the st_a ctl bundle to the st_a fe leg (ctl landed = fe landed);
  pin_r8_v2 is only a floor (st_b r_d + 12 = 20 on W5). Old 11 = floor 20 - bound 9. New 11 = fe 23 - bound 12. Same
  number, different cause. Checked by two more emulations: ctl rows only -> ctl 12 / 8 / 20 (absorbed, would FAIL r_d by
  1 cycle on all 6 W slices); fe rows only -> ctl 9 / 14 / 23 (passes).
- So the 6 ctl station rows are redundant for the regen: the fe rows alone carry the ctl leg. They cost nothing in flops
  (9,648 pad flops become 9,648 station flops) but they change 6 ctl types (223k-240k cells each). Optional: drop them and
  K touches 9 types, not 15. Not blocking.
- Margin: nb_od W slices 0 cycles (equality by tuning), r_d 2 cycles. One more cycle on any W st_b fe leg breaks it again.
  Next event: let the regen pad nb_oc of region 0. Not blocking.
- Check at DERIVE_DONE: `gates/r8_s29q103S4Q9K.derived.json` must equal my `/tmp/fable-pd-s4q9k/r8_k_emul.json`
  (sha 935502958f01) on the 168 members; W5 ctl 12 / 11 / 23, fe 23 / 0 / 23.

## 2. Station geometry (MEASURED from the K plan rows)

| types | stations | line um | hop um (first hop = 2 hops) | clear to nearest core / macro box | nearest other station |
|---|---|---|---|---|---|
| 6 sle_ctl | 2 -> 5 | 475.2 | 67.9 (135.8) | 60.2 um (16 boxes) | 28.6 um, b_hw_hc1_o 1,574 bits |
| 4 sle_fe | 3 -> 6 | 936.8 | 117.1 (234.2) | no core box in type | 34.2 um (sle_fe_v2 only) |
| 3 slw_fe_v1 | 1 -> 6 | 421.3 | 52.7 (105.3) | no core box | 40.0 um, x_stm_i 544 bits |
| 2 slw_fe_v2 | 1 -> 7 | 463.0 | 51.4 (102.9) | no core box | 25.9 um, x_stm_i 544 bits |

- Max hop 234.2 um <= 405. All points inside the outline (min 69.1 um from an edge). 0 sites in a core + 4.32 halo.
  Note: the composer script tests station points only, not the row box its docstring names; the 60 um clearance covers it.
- Added flops per type 774 / 804 / 1,290 / 1,548 (about 230-450 um2 of flop area) in types of 56k-240k cells. No density
  or pin-access risk from the plan. No placement or GRT read (no K kit exists yet).
- Watch: slw_fe 51-53 um flop-to-flop hops on 258 bits x 6-7 stages = hold-buffer candidates; read hold on the first kit.

## 3. Latency

- Plan lane fixed_cycles 6,366 -> 6,453 = +87 (fe E 6x3, W 3x5 + 3x6; ctl 12x3). Leaf diff J -> K = 126 leaves: 24 lane
  rows, 30 station leaves on 15 types, 72 latency.lanes fields. latency_groups, clock and reset: 0 leaves.
- Landed depth against the adopted J: 0 cycles on all 168 members (EMULATED). Token cost 0. None of the 24 lanes is a
  die-pair lane; seam and calendar untouched (confirm SEAM 7,7,7,8,7,7 in the BQ log).
- Flops: 22,806 pin pad flops become 22,806 station flops; net 0.

## 4. What still needs the next event

- Clock rows (b): K has 0 clock leaves, so all 52 types still need them. Only run so far is on S4q9c
  (`/srv/opentallas-scratch2/claude/fable-die-qc/delta/clock_c_1116/report.json`); no re-run on J or K yet.
  - 8 of the 52 are K types (hold until (b)): sle_ctl__cl503337ff, sle_ctl__cl67434795, sle_fe_v1__cl8210183c, sle_fe_v2,
    sle_fe_v3, slw_fe_v1__clfe325744__cl08d14f0d, slw_fe_v2__cle312294d, slw_fe_v2__clf110fab2.
  - 7 K types not in the 52 (release on K): sle_ctl__cl372cea1c, sle_ctl__cl503337ff__v1, sle_ctl__cl67434795__v1,
    sle_ctl__cla4f6f12f, sle_fe_v1__cl1cbb7497, slw_fe_v1__cl95cd1d0c, slw_fe_v1__clfe325744__cldb4efe33. Re-check
    this list when the tool is re-run on K: the c-based list may miss type names created after S4q9c.
  - 44 other types wait for (b) only.
- st_a_v1 (c): 6 types, sle_st_a_v1__cl67389ecd (E0), __cl989804f6__cl18eece69 (E2), __cl989804f6__cled3c1d7b (E4),
  slw_st_a_v1__clb036e152 (W2), __clfc5867a6__pvdf8e5ca4 (W4), __clfc5867a6__pvf82a6c28 (W0). K changes no st_a type and
  no st_a parameter (same landed as J, J hcparam 20 types 0 mismatches). Still open for all 6: proof from the signed
  config.mk that the hardened views carry the die HI_PAD / SKEW. None of the 6 is in the clock-row list.
- (d) 2 inherited G0 faces rows (sl_W5_fw.W, coll_f4.E): not in K.
