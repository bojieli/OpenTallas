# FABLE-DIE-QC: whole-die verdict and plan event, QC die (qwen_compute)

2026-11-16, FABLE-DIE-QC. MEASURED = computed by me from the files named. Work dir epyc9
`/srv/opentallas-scratch2/claude/fable-die-qc` (bin/ scripts, an/ outputs, delta/ plans); epyc2 same path for the S4q9c chain.
Render (place + clock + GRT, 4 panels): intel2 `~/fable-die-qc/qc_die_s4k.png` (+ `_zoom.png`, `render.py`).

## 0. Verdict

**The floorplan and die routing are sound. The die clock is the weak structure, and one reset class was unowned.**

- Die GRT0 passes: overflow 0 / 0 / 0, use M4 3.0 %, M5 5.8 %, M6 5.4 %, M7 4.1 %, M8 0.6 %, M9 1.1 % (S4k, 50 it, TT = FF).
- Die STA had never produced a result on QC: `die_sta_related` crashed on every plan since S3R. Fixed (section 3).
  First result (S4k routed clock): setup passes (+362 intra, +540 seam), **hold contract fails** (-115 intra, -59 seam)
  and 5,014 of 84,302 taps are outside their plan offset band.
- Plan of record at die level is S4q9c (S4q9b + 3 PHY outline rows; FABLE-FIX-QC-KNEE-HC). S4q9b itself never bound.

## 1. Data read

| item | source |
|---|---|
| floorplan, lanes, clock rows | treeA `zz_s29_qc103_s4k.json` sha 146326183743; treeE `zz_s29_qc103_s4q9c.json` sha dd47490db390 |
| die kit, GRT0, routed tap arrivals | epyc9 `die-grt0-qc/qc/s4k` (DIE-QC-103, 11-15 17:01): the latest complete die run |
| die STA | epyc9 `fable-die-qc/an/sta_s4k/sta.log` (mine, on that proof) |
| reset audit | epyc9 `fable-fix-qc-knee-hc/bind/bind_s29q103S4Q9CBR` bound RTL, `fable-die-qc/an/raw/audit_s4q9.json` |

## 2. Whole-die numbers (S4k die run)

Die 31,216 x 25,644 um (800.5 mm2), 377 partitions of 130 types, abutted, 97.7 % covered, 3 channels in the west strip.
12 slice columns (E0..E5, W0..W5); slice row in the band y 10.2..15.4 mm; cb fabric above and below (192 partitions,
604 mm2); coll / glue / native59 / tt_ctlm / PHY in the west strip (x < 1.56 mm).

| structure | number | judgement |
|---|---|---|
| die GRT0 | 613,429 nets, 649.6 m, overflow 0 | PASS |
| M4-M7 demand | concentrated in the slice row; hottest gcells on the slice-row seams y = 11,556 and 13,414 um (M4 409, M7 430 tracks of demand in one 10.8-um gcell, no overflow) | watch: the 12 st_a / st_b ft bands (b_hw_ctl_hc, 37,788 ft bits over 405 um) all cross these two seams |
| M8/M9 demand | clock feeds; hottest at (1,890, 2,538): M8 515, at the corner serdes PHY / c_W5_bf_00 | watch |
| clock network | 127,530 inverters, 9.45 m wire, 42,256 taps, 313 regions, link_htree feed rooted at sl_E0_fw | see below |
| clock insertion (TT routed) | 0.67 ns at the root to **14.12 ns** at c_W5_tn_10; up to 306 stages; feed chain depth 21 regions | BAD shape |
| late - early at one tap | up to **1,828 ps** (c_W5_tn_10) | BAD: OCV of the serial feed |
| clock phase across plan ports | 2,993 ports: 1,583 over T/2, 689 over one cycle, worst 7,509 ps (sl_W3_hc2 cws2) | absorbed by count-aligned rings (S3R: depth 8 on 113 crossings, worst margin 104 ps) |
| adjacent partitions, 7.3 ns apart | sl_W3_su_c -> c_W3_bn_10 landed pair, clock damage 7,277 ps | BAD: feed order does not follow this data edge |
| related-pair skew inside a region | intra 356 ps, seam 183 ps (after declared early taps) | over the 87 / 110 ps kit windows |
| same type, different instance | cb types: per-port offset differs by up to +-129 ps between instances (cbn_q01 cld9ff4c40, 10 instances) | BAD: each instance gets its own region tree (entry face and site slides differ) |
| clock cells | 5 of 127,530 outside a partition; 0 illegal after slide (4,084 nodes moved) | PASS |
| lanes | 1,921 lanes, 18,010 cycles (stations 4,546, clock landing 6,766), longest 49 (rsf, 12 lanes) | OK |
| reset | wavefront from glue (west strip); die stand-in net only | reset timing is per type, section 4 |

## 3. Die STA: tool fix and first result

`die_sta_related.kit_windows` built a two-field shim for `gen_phys.tap_window_ps`; with a `tap_offset` row on a type with
early core taps it raised AttributeError, so chains s3r_b and s4k ended `REG_STA 1`. Branch `claude/fable-die-qc-1116`
@f7cee816db7, gate GREEN 37/37 (main e671bdd4a26), READY posted.

| class (S4k) | pairs | TT setup | FF hold, kit contract | window / need |
|---|---|---|---|---|
| intra region | 5,965,594 | +362.0 | **-114.9** (64,762 pairs) | 87 / 201.9 |
| plain seam | 2,015,980 | +540.4 | **-59.2** (2,797 pairs) | 110 / 169.2 |
| landed (no count-align) | 12,913,089 | info | info | damage 7,887 ps |

Hold on real views: BLOCKED(kits), 0 measured (no signed view of most types yet). Early core taps: 1,461, all declared.

## 4. Reset reach: raw reset -> FSTART face flop (COORD lever C audit)

All 130 types, bound RTL of S4Q9CBR: 1,142 FSTART face flops. 1,014 (110 types) take a local same-cycle copy
(`clock.landing_local_resets`). 128 in 9 types share one START raw reset:

| type | flops | over 405 um | worst um | fix |
|---|---|---|---|---|
| glue | 32 | 32 | 2,108 | S4q9d (FABLE-FIX-QC-CBGLUE); r199 review ADOPT-OK posted |
| cbf_q01, cbf_q01_s2 | 5 + 5 | 2 + 5 | 2,339 | S4q9d |
| **coll_core** | 14 | 4 | 1,745 | **my rows**: 6 leaves / 15 consumers |
| **native59** | 37 | 28 | 1,228 | **my rows**: 7 / 38 |
| **tt_ctlm** | 26 | 23 | 957 | **my rows**: 4 / 27 |
| coll_n, slw_hc3 x2 | 3 + 3 + 3 | 0 | < 300 | none |

So this is not a die reset-tree problem: the die tree and per-type relays exist; six types lacked the leaf rows.
0 added cycles (leaf depth = old reset depth), hops in <= 366 um, out <= 148 um.

Not checked: writer_start / reader_start chain members (no site in the bound RTL; needs a placed dump per type).
QC-CBGLUE's 06:43 raw-branch delta must not be applied to the 14 cb types that already have local resets.

## 5. Plan event

| # | rows | types | cycles | state |
|---|---|---|---|---|
| 1 | `landing_local_resets` + `reset_tree_anchor` on coll_core, native59, tt_ctlm | 3 | 0 | rows handed to FABLE-FIX-QC-KNEE-HC (lanes/handoff/FABLE-DIE-QC-rows.json), which composes the one S4q9e; my own copy is withdrawn |
| 2 | clock rows from the S4q9c routed proof: `clock.tap_offset.per_port_ps`, `seam_hold.seam_ps`, `tap_window.per_type_ps` | all | 0 | method PROVEN on S4k (section 6); rows for the current plan wait for the S4q9c chain |
| 3 | region trees built once per type and reused in every instance (tool change in die_trial region DME), so the +-129 ps instance spread goes to the +-10 ps floor | 14 cb types, 192 partitions | 0 | not started; next step |
| 4 | feed: cb regions fed from their own slice column instead of the 21-deep chain | clock only, K re-plan | lane cycles re-derived | not started; do only if count-align on S4q9c shows margin under 50 ps |

## 6. Proof

RUNNING: die chain on S4q9c, epyc2 `fable-die-qc/chain/qc/s4q9c` (kit, GRT0 TT / FF 50 it, tap arrivals, die STA,
count-align C / D, STA with count-align). Client log intel2 `~/fable-die-qc/chain_s4q9c.client.log`. The S4k kit stage took
3 h 35 min.

### 6.1 Clock rows delta proven on S4k (epyc2 `fable-die-qc/s4k/out`, a = plan rows, b = rows re-derived by `bin/clock_rows_delta.py`)

Second tool cause found: the offset rows were mean +- half range over the instances of a type, which cannot cover a skewed
set of 3 or more instances. Branch head @dd7250845f3 writes the mid-range (gate GREEN 37/37).

| check (FF, same routed clock) | a: S4k rows | b: re-derived rows |
|---|---|---|
| TAP-OFFSET-GATE | FAIL, 5,014 of 84,302 outside | **PASS, 0 of 84,512** |
| intra kit-contract hold | -114.9 (W 87, need 201.9, 64,762 pairs) | **0.00** (W 79, need 79.0, 0 pairs) |
| seam kit-contract hold | -59.2 (W 110, need 169.2, 2,797 pairs) | **+10.8** (W 180, 0 pairs) |
| TT setup intra / seam | +362.0 / +540.4 | unchanged |

Delta b = `clock.tap_offset.per_port_ps` (52 of 130 types change), `clock.tap_window.per_port_ps`, `seam_hold.seam_ps` 110 -> 180.
Cost: the 52 changed types get a new kit SDC; seam hold repair covers 180 ps instead of 110. Hold on real views stays
BLOCKED(kits) until types are signed.
