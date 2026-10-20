# TOKSIM-S81: measured decode rate, DeepSeek-V4.1 on the S81 ROM release die (p4l-MU), 2026-10-19

Owner request (18:18 PT): replace the prices of record and the estimates with cycle-accurate RTL simulation of the real
decode rate, for 1 user and for multiple users (46 AR / 10 MTP).

**Verdict: NOT YET RELEASE-GRADE.** 37.2 % of the AR token's cycles (31.0 % of MTP) are now measured on current RTL.
Excluding the modelled off-chip PHY legs, the figure is 43.6 % (35.2 %). The TOK.FREEZE target is 90 %.
Using the new measurements, the decode rate is lower than the composition of record.

| workload | cycles / token (fixed path) | re-solved DAG | tok/s @ 1.2 GHz (833 ps) | composed 10-19 (mixed) | price of record | measured | measured on-chip | modelled PHY |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 user AR | 1,173,913 | 1,187,258 | **1,022.2** (re-solved 1,010.7) | 1,212.6 | 1,334.6 | 37.2 % | 43.6 % | 14.7 % |
| 1 user MTP (tau 4.159) | 1,566,172 / step = 376,574 / accepted token | 1,566,172 | **3,186.6** | 3,611.7 | 3,838.2 | 31.0 % | 35.2 % | 12.0 % |
| 46 users AR | per user 1,173,913 > calendar period 980,428 | | **47,022 aggregate** (1,022.2 / user) | 55,780 | | | | |
| 10 users MTP | per-user step 1,566,172 > period 1,303,400 | | **31,866 aggregate** (3,186.6 / user) | 36,985 | | | | |

Multi-user: the release seq_host / fixed_issue RTL was measured (HEADMU `run_mu_mtp.sh`, ot-epyc6, PASS). Every user
issues at its calendar shift + 360 cycles, with 0 collisions and 0 inter-user interference, and a forced-collision mutant
faults. With the measured per-user token now longer than the calendar period, every user is bound by its own token
cycles, so aggregate = users x f / T_user. The cross-die multi-user co-sim on MU die ceaed19c4 has **not** run: the 46-user
real AR run u_ar46r and the 10-user real MTP run u_mtp10r were in job u, which was killed (exit 143) before simulating.
LEAD2-S81/XDIE owns the relaunch. In the dense 46-user run a_a46d, 3,164 of 278,024 beats land 1 cycle late; the bits
are exact.

## Method

The S81 schedule is static, so cycles are deterministic. `tools/toksim_s81_compose.py`:

- takes the static token DAG (`results/arch/token_path_20261009/ds_rom{,_mtp}.json`: 2,742 nodes, a 1,794-node critical
  path);
- replaces each node's cycles with the measured start->retire cycles of its op type wherever an element record measured
  that op, at that shape;
- adds the inter-die terms of the committed composition (`results/arch/token_path_1018/ds_rom.json`, from the
  `xdie_s81_1019` co-sim: die RTL measured, switch/PMA modelled at 453 cycles a crossing, on-die leg priced) and its p4l,
  scan and residual terms;
- sums the result two ways: over the committed critical path ("fixed": measured cycles per type x count) and by
  re-solving the longest path ("solved": catches a measured change that moves the path; AR +1.1 %).

Nothing is re-priced. A node whose shape was not measured keeps its committed number and grade. `--selftest` proves that
with no element records the tool reproduces the committed composition exactly (989,618.6 / 1,381,860.8). `--check`
proves `cycles.json` is current.

Grades:

- **measured-release-RTL**: the bench ran the release source GEN mu4c, `origin/claude/s81-bind-mu4-1019` @19bf4121e
  (blob-identical files).
- **measured-newest-element-RTL**: the element is not yet bound in the release source, or a newer bench-passing revision
  was used. The label names it.
- **measured-current-RTL**: the xdie co-sim on G8R2 p4m die RTL.

These three count as measured. **measured-old-RTL** (10-08/10-13 benches on pre-p4l RTL), **priced** and
**modelled-PHY** do not.

Element records: `elements/{FIELD,SU,IDX,HEADMU}.json` come from four sub-lanes, all on Verilator 5.050. `elements/zz_curation.json`
is the parent's mapping onto DAG nodes (definitions, merged ops, per-layer shapes, priced wire tails) and wins per op.
`op_types.json` is the op-type table. `su_evidence/` holds the SU job scripts and the extracted measurements; the logs
are on ot-epyc7 `/srv/opentallas-scratch/claude/toksim-s81-su`.

## Measured (AR critical path, old -> new cycles)

| op type (count) | old | new | grade | evidence |
|---|---:|---:|---|---|
| attn.wq_b (40) | 45,754 | 142,160 | newest-element (fullsix slice, every field/frame file = release) + 195/inst priced tail | `claude/toksim-s81-field-1019`@3d55d499a results/rtl/toksim_s81_field_1019: law 231 + 224 x (epochs-1) + 1, 15 epochs = 3,359; tightest passing epoch spacing 224 |
| attn.idx.topk_local L2/L8/L14 (3 of 8) | 11,784 (8) | 47,945 (8) | release (dsdv_bk_sel) | root span incl. the scan: 14,231 / 14,242; `claude/toksim-s81-idx-1019`@204539a89 |
| attn.idx.topk_final L2/L8/L14/L20 | 1,424 | 27,059 | release | 6,554 / 6,541 / 6,698, rung-ingress bound (INDEXED13, not in release: 1,033) |
| attn.idx.score L24..L36 re-index | | 5,829 each | newest-element (dsdv_idx_rg unbound on mu4c) | sweep_1019 sw_g_p4; scan layers 0 here (inside topk_local) |
| attn.scores (40) | 2,104 | 11,560 | newest-element (svc 809c78aa5, 1M) | GO -> last fold score 289 (release blob at bench context: 161) |
| attn.quant / q_quant / ffn.norm.scale (40 each) | 324 / 288 / 306 | 418 / 418 / 438 | release | 112 leaf + 247 16-slice exchange + 59/79 finish (q_quant is an upper bound) |
| z_quant, q_rope, softplus_sqrt, bias, hc_post x2, quant2 | | 19 / 57 / 145 / 115 / 63 / 191 | release + old wire stations priced | slice benches L0 = L2 |
| top6 + top6_order | 8.9 + 44 | 0 + 56 | release | dsdv_gunit_l1 single pass |
| eng.gate / eng.add / eng.dot | 494.7 / 106.9 / 269.6 | 697 / 82 / 0 | release (gate is an upper bound, dot inside gate) | slice_eng |
| head.lm_head / argmax; draft.head / markov | 8,429 / 21.6; 8,387 / 65.5 | 8,416 + 34 / 10; 8,416 + 34 / 6 | newest-element (no head/draft netlist on p4l, gap G9) | `claude/toksim-s81-headmu-1019`@87607ecc1 |
| collectives + hops | | | measured-current (G8R2) + modelled PHY + priced leg | xdie_s81_1019 (unchanged) |

## Findings: the measured release RTL is slower than its prices

1. **wq_b field phase: 3.2x the old number (+96k cycles a token, -8 % AR).** One slice share of 512 rows over 15
   epochs, with a tightest passing epoch spacing of 224 edges. The spacing is set by the compiled source schedule (at 223
   and below the source stops reading from epoch 1), so it may be a compiler-schedule limit rather than the field rate.
   This goes to LEAD2-S81/TOK2 + FRAME.
2. **Index path (+72k cycles, -6 %).** The p4l reader is HBM-bound (8,702 cycles for 43,691 keys, against 3,724 in
   record D). The release topk_final is rung-ingress bound (6.5k against a price of 178). The opt-in INDEXED13 selector
   (1,033) would recover about 22k cycles but is not in the release. This goes to LEAD2-S81/TOPK + L20.
3. **Attention scores at 1M context (+9.5k cycles).** The svc GO -> last score is 289 against a price of 52.6.
4. **Norms (+14k cycles).** The 16-slice exchange (247) replaces the hub reduction.
5. **Gains.** z_quant, q_rope, softplus, hc_post and Engram dot save about 6.5k cycles.

## Still not measured (63 % of AR cycles)

| part | cycles (AR) | why / next |
|---|---:|---|
| field experts_gu, wo_a, down, router, a_proj, wo_b, shared_gu, idx.q | ~372k old-RTL (32 % of AR) | only 6-row frame phases and the wq_b fullsix vehicle exist; next: a fullsix-style vehicle per op, largest first (experts_gu, wo_a, down) |
| hops / collectives: modelled PHY + priced on-die leg | 173k PHY + part of the priced share | PHY is off-chip (allowed); the on-die leg needs a stage bench |
| softmax max/exp/sink/den/normalize | ~41k old-RTL | the svc bench feeds P; no separate release timing |
| attn.gather, window_load, re-index topk_local | ~12k | gather: no release consumer (gap); window_load job pending (ot-epyc9) |
| HC H_LOAD/H_STORE/COEF, embed, argmax_merge, MTP DSpark draft blocks | old-RTL | no release bench prints these cycles |
| price_of_record_residual + p4l DV deltas + scan legs | ~53k priced | ledger terms of the price of record |

Pending runs are listed in `pending_results.txt` (TOKSIM-S81/SU svc_rs release rerun, TOKSIM-S81/IDX window_load,
XDIE u relaunch). After they land: drop the new records into `elements/`, rerun `python3 tools/toksim_s81_compose.py`
and commit.
