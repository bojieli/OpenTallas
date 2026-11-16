# FABLE-CLOSURE-STRATEGY 2026-11-15 17:15 PST: what the TT repair clears, what stays, seven levers, stop list

Read-only review by FABLE-CLOSURE-1715. Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: the 15:30 strategy and r176; FABLE-PD-KV-1450 / S81-1515 / QC-1545 / HEAD-1650; rulings r176-r192; queue posts to
17:10; `failure_breakdown.py` (17:10).
Measured by me (17:12-17:20 PST): the latest wave kit of each type on epyc2/7/8/9/10 + intel1 that has a
`postcts_gate_tt.json` younger than 60 h (86 types, HBM excluded; 68 younger than 24 h): TT setup estimate at the gate
(GRT RC), FF hold estimate, last line class of `5_2_route*.log`. Also the route logs of the DRT-0255 proofs.
Scripts: `lanes/fable-closure-1715/scan.py`, `agg.py` (JSON and log text only; no database opened, no STA run).
MEASURED = read or computed by me today. REPORTED = from a lane post or a Fable PD review. INFERENCE is marked.
Limits of the sample: wave directories only (lane pilots such as hd_host_e v1k2 and hd_serdes sd9k are not in it); mixed
plan events; types held before P&R (S81 99, QC 54) have no kit and are not in it.

`failure_breakdown.py` 17:10: S81 types 40/394 (99 held, 3 running); HEAD 19/26 (4 running, hd_host_e / hd_host_w stopped
after CTS, hd_ctl route error); QC 6/127 (54 held, 37 running, 3 route errors); KV 5/56 (4 running). No change in the
signed counts since 15:10.

## 0. Answer first: what the TT setup repair clears

Table A. Latest wave kit per type, 86 types (MEASURED). Setup = TT estimate at the post-CTS gate; gate limit -42 ps.

| route result \ TT setup | >= -42 | -80..-42 | -150..-80 | < -150 | sum |
|---|---|---|---|---|---|
| DRC 0 | 30 | 2 | 0 | 0 | 32 |
| stopped with `DRT-0255` | 13 | 4 | 3 | 4 | 24 |
| other route result (DRC > 0, `DRT-0206`) | 1 | 0 | 0 | 3 | 4 |
| no route log (stopped at the gate, or running) | 2 | 0 | 0 | 24 | 26 |
| sum | 46 | 6 | 3 | 31 | 86 |

Per die (types, of which open): S81 38 (27), QC 27 (19), HEAD 14 (5), KV 7 (5). Open = 56 of 86.

- **The repair alone clears 2 of the 56 open types (4 %)**: kv3_phy_v1 (-56.1, DRC 0) and slice_station__t22 (-69.9,
  DRC 0). Measured gains of the repair on GRT RC are 46 ps (hd_host_e) and on placement RC 10-81 ps (REPORTED,
  GENBUG-IMPL 16:58), so the -80..-42 column is its reach.
- 4 more in that column (slw_su_l1 x2, sle_stm_v2, slw_sc_v1) also stopped with `DRT-0255`; they need both.
- The -150..-80 column (kv3_sys_SD -85.7, slw_sc_v1 cl63e5a7a2 -83.0, hd_spn -145.2) is INFERENCE "possible" for the
  first two; all three also have `DRT-0255`.
- **31 of 40 setup failures are below -150 ps and are not a repair class**: 26 S81 (22 col_h9, 2 leaf, 2 col on the old
  tree: -152 to -573), 4 QC (slw_fw_v1 / v2 -236 / -439, sle_st_b_v2 x2 -187 / -202), hd_host_w -198. These are clock
  window, half-cycle face, missing stations and tap load (levers 2, 4, 5).
- **`DRT-0255` is the larger class: 24 of the 56 open types (43 %), and for 13 of them it is the only failing gate.**
  QC 15 of 26 routed kits, KV 3 of 6, HEAD 3 of 12, S81 2 of 16.
- Outside the sample the repair is decisive for the HEAD pilots: hd_host_e -77.7 -> -31.6 (GRT RC), hd_serdes
  -261 -> -109 -> -33.9 (REPORTED).

What stays after the repair, in order of size: `DRT-0255` (24); S81 col clock window and face (24, 216 types behind
them); hold (FF estimate below 0 at the gate on 54 of 86 kits, port share not split: QC 20 of 27, S81 23 of 38, HEAD 6
of 14, KV 5 of 7); congestion only on the held QC hc / cb types and on KV hg (no new kit result since 15:30).

## 1. Levers, ranked

| # | dies | lever | unblocks | owner | state 17:15 |
|---|---|---|---|---|---|
| 1 | all 4 | `DRT-0255`: read the proofs at the 1st iteration, then put the proven PG form into gen before the QC S4q7 and S81 G volume | 24 open types now, 13 by itself | DRT0255-PROOF-1115, GENBUG-IMPL | 6 proofs in route iteration 0, no verdict |
| 2 | S81 | col: per-port window + IFN 0 + ROM tap rows in one kit | 24 open kits, 216 types | DIE-S81-92, S81-PHYT1 | IFN 0 halves in LEC; G1d rebinding |
| 3 | all 4 | TT repair roll-out: three checks that decide whether the gain survives hold repair and detail route | 2 alone, 6-9 with lever 1, 3 HEAD pilots | GENBUG-IMPL | merged 17:02; no routed result |
| 4 | HEAD | NF11 kits; hd_serdes fan-out tree in RTL, not only the private leaf; die-phase PDN for face-pin types | 4 open types | HEAD-100, HEAD-SERDES-1115 | NF10 / NF11 posted |
| 5 | HEAD, then all | Die route: abstract `SIZE` differs from the plan outline, so mirrored tiles get cut windows 8.64 um off | 2 of 13 units now; every MY / R180 instance | HEAD-MYTILE-1115 | cause found 17:03 |
| 6 | QC | S4q6b / S4q7c / S4q7d: first hc and cb kit GRT; fw / st_b setup at the first gate | 54 held types | DIE-QC-103, QC-CB-GEN-1115 | binding |
| 7 | KV | 7u pilots to CTS (blocked on the kit_rtl tool skew); q2 clock leaves before any hold pad | 34 held types | KITRTL-FAIL-1115, KV-102 | pilots held |
| 8 | S81 | svc bands: tap sites before bands (attnh_i0), the 23 bands at 401-403 um on one tap with their pin flops | 120 non-col types | S81-PHYT1, CLKSITE-RESERVE-1115 | G3 rows v4 posted |

### Lever 1. DRT-0255

Evidence (MEASURED): Table A. Types by family: QC hc0 x3, hc2 x2, sc_v1 x4, sc_v3, st_b x2, stm_v2, su_l1 x2, coll_s; KV
io_cor, sys_SD x2; HEAD hd_spn, hd_ctl_n, hd_st_str; S81 leaf t25 / t54. Proof state at 17:14 PST (route logs): c2_t37
and p_t49 at 50 % of iteration 0 (37,729 and 13,831 violations so far); c3b_t37, c2_fe, p_hd_spn, su_B_cut started
route within the last 2 minutes; p_hd_ctl past CTS; c2_hroot, su_A_m7 in GRT. `DRT-0255` in these kits came in the 1st
iteration, so no proof has reached the point of the original failure.

Root cause: as in the 15:30 review (M6 guides in rows under the M6 PG pair; face pins under the M7 strap with core-phase
PDN). Unchanged.

Fix:
1. DRT0255-PROOF-1115: post each proof the moment its 1st iteration ends, per class: p_t49 / p_hd_spn = face pin class
   (die phase), c2 / c3b = capacity cut, the pair-row keep-out kit = cell class. Rule of 15:30 stays: a c2_t37 failure
   in gcell rows 238 / 276 / 2148 is not a verdict on the cut.
2. KIT-OPS-5 with DIE-QC-103: 15 of 26 routed QC kits stop here, on the same families S4q7 will relaunch (hc, sc, stm,
   su_l1, st_b). The PG flags act at floorplan, so a kit launched without them cannot take them at resume. Put the first
   form that passes a 1st iteration into the QC gen env the same hour; until then the S4q7 hc / sc kits are GRT evidence
   only (INFERENCE: they will stop in route as their S4Q2 / S4P kits did).
3. GENBUG-IMPL: the TT repair in grt mode adds cells after the cut and after the pair-row site search. Run the 15:30
   `gd2.py` on the repaired guide file of hd_host_e (`tt_5_1_grt` guides, epyc10): pass = 0 new long M6 guides in
   0-track rows. If the pair-row keep-out is on, the repair's detailed placement must honour it (INFERENCE: not checked).

### Lever 2. S81 col

Evidence (MEASURED): the 22 current col_h9 kits (tree 3fa87b84b18) stop at the gate with TT setup -152 to -573; FF hold
estimate below 0 on 23 of 38 S81 kits (-165 worst). REPORTED (S81-1515): 208 of the -229 ps on reset removal and 416 of
833 ps on the element face are the flat tap window; ROM -> cfg7_seq is -12 / -102 at window 0.

Root cause: one flat 208 ps window paid by every cross-port pair; half-cycle face capture; ROM clock on the wrong tap.
The TT repair does not act on any of them: both setup and hold of the same endpoints are short (h9 he).

Fix: unchanged from 15:30 levers 2 + 3, with one addition. DIE-S81-92: the col delta (Event F part 2) carries the
measured per-port window, the ROM tap rows and the split of clk_t13 / t14 / t15 together with the IFN 0 halves; one
col_h9_r0_p6 kit with all of them plus `OT_TT_SETUP_REPAIR=both`. Read at its gate: endpoints that fail TT setup and FF
hold together. More than 0 means the window is still charged twice; that is a clock row, never a buffer.

### Lever 3. TT repair: three checks

Evidence (REPORTED): the six kit results of 16:58; guide handover checked by file existence only. MEASURED: every one
of the 86 kits has `SKIP_CTS_REPAIR_TIMING` in `config.mk`; none has the new flag yet.

Risks (INFERENCE, each with its check):
1. Order. cts-mode repair runs before the FF hold repair. The FF session has +124 ps of setup slack where TT has -78
   (hd_host_e), so hold pads are placed with no view of TT setup. The grt-mode pass comes after and can repair again,
   but it re-sizes cells on paths whose FF hold was just closed. Check on the first 10 kits: FF hold at the gate must
   be read on the database written by the grt-mode pass, and TT setup after it; print both before / after per kit.
2. Detail route of repaired kits: first DRC counts (GENBUG watch, r192) and item 3 of lever 1.
3. -42 on placement RC is not -42 at the gate: hd_host_e lost 54 ps from CTS to GRT RC. slw_sc_v1 at -41.8 and
   hd_serdes at -33.9 after their repairs are on placement RC; both need the grt mode result before any READY.

Use: relaunch kv3_phy_v1 (on 7u) and slice_station__t22 (after G1d) first; they are the two clean reads of the repair.

### Lever 4. HEAD

Evidence (REPORTED): NF10 measured windows 0-25 ps per port (plan had 20-69 and a 69 fallback); NF11 = early tap for
u_epc + ISLICE tap group + 40 taps on hd_host_w (9 of 12 were at the 3000-sink cap). hd_serdes: worst path is
pma_rck -> pma_rck, clock skew -18 ps net, data 1,074 ps with 5-8 BUF fan-out stages (355 ps in one chain); -109 after
TT repair, -33.9 with a cloned leaf buffer for the 3 `done[0]` flops. MEASURED: hd_host_w attempt 7 (NF6) -198.2 at
the gate; hd_spn -145.2 with `DRT-0255`.

Root cause: control registers with 400-800 loads behind place-stage buffer trees (hd_host_e isl_rp, hd_serdes ldr);
tap load; fallback windows.

Fix:
1. HEAD-SERDES-1115: the cloned leaf is a clock ECO on one database and has 8 ps of margin before the GRT adder. Put it
   in the plan as a tap group for the three flops (the NF11 key used for ISLICE), and replicate the `ldr` registers in
   RTL (0 cycles, as proposed for isl_rp) in parallel. Adopt the first that reads -42 or better on GRT RC.
2. HEAD-100: hd_host_e / hd_host_w kits on NF11 with the repair in `both`; hd_host_w is read first at its
   `OT_TAP_BALANCE` line (tap means were 359-446).
3. hd_ctl, hd_spn: lever 1, die phase; no wave kit with M7 offset 4.128.

### Lever 5. Die route: mirrored tiles

Evidence (REPORTED, HEAD-MYTILE-1115 17:03 and HEAD-100): 11 of 13 units at DRC 0; u042 218 and u046 243 markers, each
inside one MY hd_tile (shorts M1-M7 in about 26 stacks). The abstract carries the closed view `SIZE` 708.48 against the
plan outline 717.12 (hd_st_n4: 1,123.2 against 993.6); placement mirrors about the master width, the window tool about
the plan width; MY / R180 windows land 8.64 um off.

Fix: HEAD-MYTILE-1115 makes one of the two the single reference (abstract `SIZE` = plan outline is the smaller change;
INFERENCE). Then a table for all four dies before any further unit launch: closed-view types whose abstract `SIZE`
differs from the plan outline x instances in MX / MY / R180. hd_st_n4 differs by 129.6 um, so check it first. The
other 313 HEAD units and the later S81 / QC / KV die routes depend on this.

### Lever 6. QC

Evidence: REPORTED S4q6b (23 lanes at the station sum), S4q7c / S4q7d (31 bands to 0.49-0.50, hops at or under 375 um)
binding. MEASURED: QC kits older than S4q6 at the gate: slw_fw_v2 -438.7, slw_fw_v1 -236.4, sle_st_b_v2 -186.7 /
-201.7; FF hold estimate -93 to -112 on sle_fe_v1, sle_fw_v3, sle_stm_v2, sle_st_b_v2.

Fix: (1) first slw_hc1 kit GRT with "target 0.45 -> rows 5" and one cbn_q11 kit GRT stay the two proofs (15:30 lever 4).
(2) First S4q7 fw and st_b kit: gate setup against -236 / -439 and -187 / -202; the 18,500-19,700 new station flops per
fw type are the expected cure (INFERENCE). (3) Lever 1 item 2 decides whether the hc / sc kits can finish.

### Lever 7. KV

Evidence: REPORTED: both hg / hgi pilots and 8 more 7u items held at kit_rtl (tool skew; `gen_phys.py` cannot import
`rck_island` in the 7u source tree). q2 hold is a clock cause: leaves clkbuf_leaf_191 / 192 at 125 ps against 30-54,
pair skew FF 121 against 77 on the signed lineage. MEASURED: kv3_phy / kv3_phy_v1 FF hold estimate -241 / -223 at the
gate, kv3_sys_SD -85.7 setup with `DRT-0255`.

Fix: KITRTL-FAIL-1115 closes the 7u tool skew, then the 15:30 lever 5 list is unchanged (two pilots to CTS, max wire
143, unsigned ring masters). KV-102: split the kv3_phy hold estimate into port and internal paths before any pad.

### Lever 8. S81 svc bands

Evidence (REPORTED, BANDTAP v4): compose OK, max hop 402.807 against 405.16, 23 bands at 401 um or more; attnh_i0 has
27 band points with no legal tap within 200 um; forms (b) ring split and (c) tap column run in parallel (r191).

Fix: S81-PHYT1 / CLKSITE-RESERVE-1115: generate tap sites before bands in the next compose, so a band is never placed
where no site exists. For the 23 bands: put the pin flops and the first ring stage on one tap (tap group), so the hop
pays no window. No re-floor for them (section 2).

## 2. Two risk questions

**Hold ECO cost (KV q2: 2 passes + a DRC fix).** Risk: medium, and it rises with the TT repair. MEASURED: the FF hold
estimate at the gate is below 0 on 54 of 86 kits (port paths included). REPORTED: q2's cause was the clock (pair skew
121 against 77), not missing pads. Each post-route pass costs an incremental route and a DRC round. Rule from the
evidence: a kit that needs a second post-route hold pass goes to a pair-skew read (worst launch / capture leaf stage),
not to a third pass. Before route, list endpoints that fail TT setup and FF hold together; those are clock or window
items and no buffer count closes them. The pre-GRT hold build stays the main form (S81-1415: until a call adds 0 cells).

**405 um hop limit, 23 S81 bands at 401-403 um.** Risk: low as geometry, not measured as timing. The margin to the
rule is 2.4 um (0.6 %); the rule is a plan distance, the route can be longer. INFERENCE: with the pin flop and the ring
stage on different taps the hop also pays the tap window (flat 208 ps on S81 today), and that is worth far more than
2 um. Check on the first G3 svc_hi kit: TT setup of the ring-stage endpoints of these 23 bands at the gate. Do not move
bands for this before that read. attnh_i0 (402.753) is in the list and changes anyway.

## 3. In flight: wrong or redundant

1. Counting the TT repair as the fix for the gate failures in general: it reaches 6 of the 40 failing kits in the
   sample, and 4 of those 6 still stop in route.
2. S4q7 hc / sc volume expected to sign off without a PG form: their last kits all stopped with `DRT-0255`.
3. hd_serdes READY on the cloned leaf at -33.9 (placement RC, one database).
4. More die-route units with mirrored closed-view tiles before lever 5 lands.
5. From 15:30, still open: three separate col pilots without the combined kit; cb bands at density 0.5 or 1.0 read as
   the cbn_q11 clump fix before a kit GRT.

## 4. Stop list (technical dead ends)

1. Unchanged relaunch of a type that stopped with `DRT-0255` (24 types, section lever 1 list).
2. `SETUP_SLACK_MARGIN`, fan-out 20, or more FF-scene `repair_timing -setup` as a TT setup fix.
3. TT repair as the cure for S81 col, hd_host_w, QC fw / st_b kits below -150 ps.
4. A third post-route hold ECO pass on one kit; hold pads on q2 before the clock leaves; pads for endpoints that fail
   setup and hold together.
5. Re-floor or band moves for the 23 bands at 401-403 um; reach relaxation for attnh_i0.
6. Kept from 15:30: `OT_PG_TRACK_TRUTH=1` alone, stripe-sized regions, `OT_PG_CELL_KEEPOUT` in `die_gen_env`,
   `MAX_ROUTING_LAYER = M7`, density / `band_spread` for `DRT-0255`; new col reset forms; per-pin IFN split; S4q5 and
   hc height; hg / hgi kits from kvgeom5 / 6; M7 core close as a KV default; register stage at the u_epc input.

## 5. Not checked

- No proof has a 1st-iteration result; lever 1 has no cure verdict.
- The hold counts include port paths (not in the hold gate); the internal share was not split.
- The gate numbers are estimates on GRT RC, not sign-off STA; 18 of the 86 kits are 24-60 h old, some on superseded plans.
- No hop timing was read for the 401-403 um bands; no abstract `SIZE` table was built for lever 5.
- Whether the gate reads FF hold after the grt-mode repair (lever 3 item 1): script order not read.
- G1d / G2 / G3 bind results, S4q6b / S4q7 bind results, any NF11 kit, any 7u kit past kit_rtl.
