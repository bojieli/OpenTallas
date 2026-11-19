# FABLE-PD-KV-0845: KV die clock, intra-die hold (review, 2026-11-19 08:45 PST)

Scope: KV D25c 4a40f1db, kv_7yhr clock, A4 crossing rows. Read-only review. Inputs read:
lanes/DIE-LEVEL-1119.md, posts of DIE-CORETAP-1119 / KV-CROSSING-1119 / DIE-LEVEL-CHECK-1119 / KV-PC-HGI-1119,
epyc10 die-coretap-1119/runs/qwen_kvsys/{c1119_early,c1119_pcsink,c1119_pcsink_k1} and die-level-1119/.../l1119d_7yhr
(tap_arrivals_TT/FF.json, clk/tree.json, ca/sta_ca.log, die_sta_related.json), tools/die_plan/die_trial.py and
core_tap_retarget.py of the lane worktree (9c60be3faa). All numbers below are computed from those tap arrivals
unless a lane post is named. Not run: no STA, no build. c1119_pcsink_k1 STA had not finished at 08:42 PST.

## 1. Why delivered = 1.83 x planned + 85

It is a tool modelling error, not merge physics. Two things stack.

(a) Unit error in the DME leaf. die_trial.py region DME, leaf():

    sd = tap_wire_ps(d) if delay_rep_um and (snake or DME_ACTUAL_MAX_UM is not None) else d

d is the Manhattan distance in um from the leaf driver site to the tap pin. Without --region-dme-snake (the KV
pcsink argv has none) the leaf sink delay is d in um read as ps. The docstring of tap_wire_ps describes this same
error on QC trial6/7 ("um read as ps ... delivered those pins ~150 ps TT early"); the repair exists but sits behind
the snake opt-in. On KV the pc core pins are inside the core outline:

| core tap class | leaf leg d (um) | sink offset given | delivered TT | offset + d |
|---|---|---|---|---|
| pcc (c0-c3), pcsink | 136.6 | +68.1 | +210.2 | 204.7 |
| pcf (c4-c7), pcsink | 47.4 | -54.1 | -15.6 | -6.7 |
| pcc, k1 | 136.6 | -9.6 | +129.1 | 127.0 |
| pcf, k1 | 47.4 | -75.1 | -29.5 | -27.7 |

Regular taps have d = 0. Fit over the 256 ports: delivered = 1.07 x (offset + d) - 8.5 (pcsink, r 0.97) and
1.00 x (offset + d) - 0.1 (k1, r 0.95). So the merge delivers what the model asks, with gain 1.0; the model asks
for offset + d instead of offset.

(b) The 1.83 is a line through two clusters. pcc and pcf each carry a different constant error (+137 and +47), so a
single line through (68, 210) and (-54, -16) has slope 226/122 = 1.85 and intercept 84. Per port, between pcsink and
k1, the incremental gain is 1.05 (pcc, 128 ports) and 1.06 (pcf, 110 ports). There is no 1.83 gain anywhere.

Consequences:
- The 08:28 CAUSE post ("routed RC of a shallower branch is ~200 ps where the model prices 68") is not supported:
  the residual after removing d is 2 to 6 ps mean (pcc) and -2 to -9 (pcf).
- The k1 correction divided the error by 1.83, so it removed only 55 % of it. k1 delivers pcc +129 (want +68) and
  pcf -29.5 (want -54); 196/256 TT ports are still outside 25 ps (180/256 FF).
- What stays after the unit repair is per-port routed scatter: sd 20 to 22 ps (pcc), 28 to 31 ps (pcf). A 25 ps
  per-port gate will therefore keep failing a quarter to a third of ports on scatter alone.
- The same error explains the region.early run: fit there is 1.30 x planned + 113, pcc +202 early.

## 2. Is per-port offsetting the right lever

It is the right form for the pcc/pcf mismatch, but the mismatch is the small term. The intra hold number is
12.3 ps minus the target-normalised skew of the worst tap pair in a partition, over all 1,529,668 ordered tap
pairs inside a partition (exactly sum n(n-1) over 160 partitions; zero data delay; CPPR 0 on the worst pairs).
Base worst normalised skew 233 to 235 ps gives -222.

Regular-tap spread alone, base TT, with no core tap involved:

| family | parts | median | max |
|---|---|---|---|
| pc | 32 | 117.5 | 180.4 |
| pv | 16 | 122.8 | 185.7 |
| hgi | 32 | 107.2 | 155.1 |
| hg | 32 | 106.6 | 148.4 |
| hub | 5 | 87.1 | 97.4 |

So with every core tap delivered exactly on target, intra hold is about -170 to -186 TT (the lane model said -198).
The whole pcc/pcf question is worth 25 to 50 ps of the 222. The spread is also local: pc tap pairs closer than
150 um reach 123 ps (p99 92), pv 144 ps (p99 104).

k1 already sits on that floor: worst pc partition 197 ps (pc_WS_6 clk_t48 vs clk_t32, both regular taps), pcc to
pcf core pairs median 39 ps (base 117). My estimate for the k1 STA: about -185 TT, set by pc_WS_6 regular taps or
by pv. It would be an improvement for the wrong reason (the /1.83 step happened to cancel part of the unit error).

Alternatives, against that floor:

- (a) Separate sub-trees or roots per core type. A zero-skew merge with a sink delay is already a per-class
  sub-tree joined with an offset. Gain no better than exact offsets (25 to 50 ps), less shared path, CA rows have
  to be re-derived. No.
- (b) Pad stage on pcf taps (+122 ps, about 8 stages at 15.9 ps per leg stage, 128 ports). Identical in effect
  to a correct -54 sink offset, which the merge realises with gain 1.0 once the unit is repaired. No separate work.
- (c) Re-sign pcc/pcf at 250 ps. Same ceiling (25 to 50 ps). pcf 196 to 250 is cheap; pcc 318 to 250 needs a
  shallower core tree and may not close. Four cores plus six pc types (48 E2 rows) re-signed. Only worth it if
  the per-port scatter of 20 to 30 ps turns out to be the last blocker, which it is not today.
- (d) Hold buffers at die level. Not possible as stated: all 1.53 M pairs are tap pairs inside one signed type
  (seam class has 0 pairs), so the paths are inside the kits. The real form is a type-kit hold fix against a tap
  window: kits are signed for W = 36 ps and the tree needs 178 (base) to about 200. Count on the all-pairs
  diagnostic: 570,091 tap pairs negative TT, 760,990 FF, 118,494 beyond the kit contract. The number of real
  register paths is not known: the diagnostic assumes a zero-delay path between every tap pair. It has to be
  counted from the kit related-pair list (tools/die_plan/kit_tap_related_pairs.tcl) on one pc type first.

## 3. Ranked fixes

| rank | fix | expected intra hold TT | cycles | time to prove | owner | applies to QC |
|---|---|---|---|---|---|---|
| 1 | Count real cross-tap paths and their min data delay on one pc type (related-pair list), then hold-fix inside the type kits to a tap window of about 200 ps; pilot kv3_pc_v1, then pv, hg, hgi | only lever that reaches 0 | 0 | count 2 h; pilot kit about 1 day | KV-PC-HGI-1119 (window rows applied by KV-D23-COMPOSE) | Yes. Same class: QC kit contract -93 on a tap window; pilot on qfd_tile_nk_a0c |
| 2 | Measure hold on real views: apply the E2 pc lib/lef rows in D25e so pc pairs leave BLOCKED(kits) and are timed with real data delay | replaces -222 diagnostic by a measured number | 0 | with D25e apply | KV-D23-COMPOSE | Yes: QC tile_nk 68 + su_lane 36 taps are unsigned |
| 3 | Cut regular-tap leaf spread: region DME on all pc/pv/hg/hgi regions (base: DME _7 pc parts median 77 vs 119 for link_htree parts), CA rows re-derived on that tree | -222 to about -120..-150 | 0 (re-price A4 lat) | 1 kit + CA, about 1.5 h; risk: early1 lost 32 crossings on the deeper tree | KV-CROSSING-1119 | Yes, larger: QC M4 kit has no DME at all, 579 taps over 25 ps late |
| 4 | Repair the leaf unit (tap_wire_ps on merge-mode sinks without the snake opt-in), rebuild with the original +68/-54 offsets, one gain-1 per-class correction if a bias stays | about -185 (same as k1 estimate; removes the 61 ps pcc error, worst pair stays regular taps) | 0 | 1 kit, 45 min | DIE-CORETAP-1119 | Check only: applies if the QC n46ct_e kit runs merge mode without --region-dme-snake; QC hang mode with ratio 1.548 already uses tap_wire_ps |
| 5 | Re-sign pcf (and pcc if it closes) at 250 ps | at most +25..50 over base, nothing over rank 4 | 0 | 1 to 2 days | KV-PC-HGI-1119 | No (QC cores need 568 ps early; matching to common is not available) |

Ranks 1 and 2 run in parallel now; rank 4 is a one-line repair plus one build; rank 3 after 4 so one tree carries both.

## 4. Stop list

- Region-wide early on regions with mixed core types (twice worse: -253, -260).
- Raising declared early rows without a tree that delivers them (KV core2, QC n46ct_m4 -407.6).
- More feedback passes with the fitted 1.83 gain (k2, k3). The gain is 1.0 and the error is a constant per class.
- Fitting one line through pcc and pcf together and calling the slope a tree gain.
- The 25 ps per-port delivery gate as an adoption gate: port scatter is 20 to 31 ps sd and regular taps spread
  106 to 197 ps in the same partitions.
- Driving the all-pairs zero-delay number to 0 with tree offsets: the floor is about -110 even for taps under
  150 um apart.
- Hold buffers at die level for this class; separate clock roots per core type; pad chains on pcf taps.
- Reading a k1 improvement as proof that the feedback loop works.
