# TOK-S81-1 (2026-10-28): S81 strict bind on the current plan, composer reconcile, wired alignment checks

Lane TOK-S81-1 (COORD 20:14). Labels: CHECKED = run or read by this lane today; UNCHECKED = copied or estimated.
Every tok/s here is COMPOSER-ONLY (COORD 20:10): no bound-die token simulation exists for S81.

## 1. Bind on the current plan (plan_s11 778e9af860b0, intel2 die-s81-16/plan)
- Inputs: plan_s11 has 11 `clock.tap_note` keys (partition_types serdes__t*), which the main schema rejects
  (`gen.py latency`: "plan invalid ... unknown key 'tap_note'"). They are notes only; this lane binds
  `plan_s11_nonote.json` (c8ad231bcce7) = plan_s11 with those 11 keys removed, nothing else changed (CHECKED).
- Run b1 (PD7d manifest asbuilt_b178_coll_pd7d.json): elab rc 0 (25 min); strict bind FAILS CLOSED in 2 min:
  `plan dead-input proof is not selected by manifest: svc_lo_dsdv_svc_rs_w__t1` (CHECKED, b1_pd7d_bind.log).
  Root cause: plan_s11 descends from main die_plan.json (type names svc_*__tN, dead_inputs -> proof_closing.json),
  while the PD7d manifest belongs to the PD7f plan (types *_phy1026_svc_N, proof_closing_pd7d.json). The two lineages
  were never reconciled; plan_s11 cannot bind with the PD7d manifest. Not a tool bug.
- Run b2 (main manifest asbuilt_b178_coll.json -> proof_closing.json, same lineage as plan_s11): elab rc 0 (24 min);
  strict bind FAILS CLOSED: `stale dead-input dependency dsdv_svc_sx_hrow` (CHECKED, b2/bind_fail_stale_hrow.log).
  Root cause: rtl dsdv_svc_sx_hrow.sv changed in 2465260038 (10-27 18:43, live-select fix) after the dead-input proof;
  the proof records every opaque child's sha. Fix at source: re-ran tools/die_plan/s81_dead_prove.py on main
  410e940f4f -> results/token_pass/s81_dead_inputs_2148/proof_closing_1028.json: 36/36 declarations byte-identical to
  proof_closing.json (ports, parameters, module sha); only the hrow dependency sha changes b761a58162 -> 4e97c7465b
  (CHECKED). New manifest asbuilt_b178_coll_s11.json = main manifest with only dead_input_proofs pointed at it; plan
  copy plan_s11b (27e26b68d1da) = plan_s11_nonote with the 36 dead_inputs proof paths re-pointed (nothing else).
- Run b2r (plan_s11b + coll_s11, elab of b2 reused: the manifests differ only in dead_input_proofs), 21:32 PDT:
  strict bind rc 1, FAIL CLOSED, CHECKED. Port proof is CLEAN: 398 partitions, 212 types, 873 crossings,
  606,281 bits, unbound 0, tied 0, undriven 0, multiply_bound 0, straps 10,352 (declared). 447 errors, 3 classes:
  * 440 LANE_LANDING_LATENCY: plan_s11 latency table carries clock_landing cycles (e.g. x_W0_in 12, rt_W0_in_0 12,
    xo_W0_in_b 3) but no clock_landing_table is bound: main manifest has none, and the only one
    (pd7/landed_sidecar_pd7d.json, 169 regions) belongs to the PD7d/PD7f plan. Root cause: plan_s11's landed clock
    regions have no landing-hardware sidecar. Owner: DIE-S81-17 (clock). Not a bind-tool defect.
  * 6 TYPE_SPLIT: col_h10_r0_p1__t1__cl574cc59d (5 inst -> 3 variants), col_h10_r0_p4__t1, col_h9_r0_p1__t1,
    col_h9_r0_p4__t1__cl8ef405e8 differ only in the x_i0 input bus; serdes__t14/t16 differ only in coll_i0.
    Root cause: asbuilt_s81.py's x-forward rewire (p1->p2->p3, p4->p5->p6) makes the x_i0 source of p1/p4 frames
    position-dependent, and plan_s11 types merge frames from different W positions. Fix in the plan type split
    (one type per x-source class) or in the as-built x wiring; same for the two serdes coll_i0 pairs. Owner: plan.
  * 1 EMIT: wavefront core reset col_h10_r1__t1__cl95b37463/u_r1.u_e6.rst_n finds 0 bound leaves in fW0_p1_b1
    (plan_s11 reset wavefront names a leaf the as-built r1 band of that frame lacks). Owner: plan reset (DIE-S81-17).
  Evidence intel1:/srv/opentallas-scratch2/claude/tok-s81-1/b2 (summary.txt, bind.log, out/bind_report.json);
  b2/lat = gen.py latency on the bind (873 lanes) -- written, not trusted while the bind fails.
## 2. The die_b178 die_port_bind FAIL list (81 tied / 59,845 unread / 31 open) -- root causes
The TOK-ALL-13r FAIL is die_port_bind on the AS-BUILT die top (inputs/die_b178.v) run with NO declared straps or
pads (port_bind.json straps_declared [], pads_declared []). The release gate for a bind is the bind.py strict proof
(tied/unbound/undriven/multiply 0) plus die_port_bind on the BOUND top. Every as-built item has one of these causes
(CHECKED by grep of die_b178.v on main 410e940f4f):
| class | count | cause | where it goes in the bind |
|---|---|---|---|
| ID/position straps sid uid eg_n ek ik sink_k tap_k si bi ch_b select_hbe gid | 50 tied pairs | declared position/ID straps (OWNER 10-25 B) | manifest `straps` regexes -> partition parameters (b3: 10,352 straps, tied 0) |
| landing K/nw/rb on dsfd_dvland_*, dsdv_svc_busland_*, pv_local_land, dvland_pvrd | 14 tied pairs | per-landing static K of the as-built forwarded-clock landings | landings are manifest `transport`: removed by the bind, path re-emitted as boundary flops at plan latency |
| relay `i` on dsfd_dvrlyh_276/562_* and dvland_276 `i` | 9 tied pairs | width-class zero pad: e.g. st_q_W_l1_0 .i({39'd0, w_q_W_l1_src[236:0]}) on a 276-bit relay | transport, removed; bus re-emitted at its true width |
| ICGx4 SE (803 inst) | 1 | scan-enable 0 on the forwarded-clock gate of each relay chain (LANDING-CONTRACT L3) | forwarded clocks retired (12.11/12.16, one die clock); removed with the transport |
| unread *_lnd high bits (erc/erq/hrrq/hrrd/erd/epc/iq/pvso/jd/jw/q/mu/lr_lk/hf/eks/rt/ht/cw) | 18,121 b | the same width-class pads on the landing side (e.g. 276-bit ld_erc_00 read [42:0]) | transport removed |
| unread w_x_f_*_dst | 26,496 b (96 x 276) | asbuilt_s81.py x-forward rewire (p1->p2->p3, p4->p5->p6) feeds p2/p3/p5/p6 frames from the previous frame's xo; the old slice->frame relay chains to those frames are left dead | dead relay chains: transport collapse leaves an unread slice xc segment (bind open output) |
| unread u_s_*_xc_nc* | 17,664 b | slice xc fields with no frame at that position (cap5r slices drive 2 of 4 frame slots) | open slice outputs in the bind |
| unread forwarded clocks nx_*_fck, ck_line, ck_xc, ck_v, CAP_CE | 704 b | retired forwarded-clock network | removed |
| open xok (48 frames) | 2 masters | asb wrapper exports xok, die no longer uses forwarded x clocks | dropped |
| open fault (landings, bk_col) | 13 masters | landing fault ports of removed transports | removed; bk_col.fault: see bound-top check |
| open bo / ck_rt (9 slice masters) | 9 masters | unused slice bypass out / clock return of retired forwarded clocks | open outputs of slice partitions |
So the as-built-top list is not a set of bind defects: it is the as-built forwarded-clock/relay transport that the
bind removes, plus declared straps. The bound top is checked separately (section 4).

## 3. Composer disagreement (3655/1260 vs 2749/785 tok/s) -- explained, B kept
Reconciliation walk A -> B, residual 0.0 (CHECKED: both reran on origin/main; reproduce AR 1,259.6 / MTP 3,655.3 and
AR 784.9 / MTP 2,749.3). Same inputs: 1.2 GHz, MTP tau 4.159, the 10-09 token graph. Differences (AR cycles/token):
-123,817 remove A's 19 ledger rows; +520,704 node prices -> 10-19 MEASURED element records (field +341,926, coll
+79,052, select +60,293, hbm +31,752, hop +14,979, su -13,700); +67,609 B ledger extras; +21,664 critical path
re-solved; -20,398 10-25 latency lanes; +38,600 release terms; -69,766 off-chip 453 -> direct cabling 251/266/257;
+141,639 241-stage map. A (compose_tok_s.py) sums ledger rows on the 10-09 PRICED graph; B (compose_tok_ds.py) uses the
measured records, re-solves the path, checks the plan digest and is the only one with --layer-cycles/--components
inputs for real replays. KEEP B. A-only rows not yet in B: 80,287 AR / 99,662 MTP cycles (IDX_SCAN_RG3_K3,
IDX_TOPK_TREE_K3, REIDX_GATHER_RG3, ROWS_INGRESS A/B, FRAME_LANDED_RESCHEDULE, FIELD.RETURN_NODE_R2, CFG7, COL_PINREG,
MTP.p2, HEADB4) -> must enter B as receipts/element records, not a flat sum (flat add ~745.7 / ~2,606, UNCHECKED
linearity). Scripts: composer walk in the lane tmp (walk.py, walk2.py copied here).
B on the CURRENT plan: gen.py latency on plan_s11_nonote (873 lanes, digest 710edbef2f13; 740 of 869 common lanes
change, sum 10,028 -> 11,918 cycles) -> compose_tok_ds --lat: AR 772.9 / MTP 2,711.0 tok/s (-1.5 % / -1.4 % vs the
10-25 table), COMPOSER-ONLY, CHECKED run (composer_s11/). B's main table (bd2b875c) is stale: table_of_record False.

## 4. Alignment checks wired into the S81 bind script
`physical/die_plan/s81/bind/bind_s81_current.sh PLAN OUT` runs and logs, fail-closed: (1) FRAME_LK per-frame landing
K vs results/s81_unblock3_1027/fi_seam/frame_lk.json (new check_frame_lk.py, the lower_xs.frame_lk rule at bind time;
die_b178: PASS 72 frames / 216 band checks, CHECKED; 7 tests incl. mismatch/override/missing-row/illegal-K mutants);
(2) bind.py elab + bind --strict; (3) gen.py latency rebased on the bind's bind_latency.json (the composer's table);
(4) count_align_bind on the plan's count-aligned crossings when the clock flow input is given (CA_LPO/CA_FLAGS);
without it the verdict is INCOMPLETE (exit 3), never PASS. Attach OUT/summary.txt to every S81 bind READY.

## 5. Programme compile and whole-die vehicle on this bind: blocked by the compiler's die source (root cause)
- tools/s81_dv/dv_layer_compile.py compiles DATA programmes only against the legacy as-built die tree
  (mk_vehicle_current.sh: die_b178.v + the fc31 p4l plan/land ages, identity-checked against fc31). The only mode that
  reads a strict bind (`--bound-control-only`, bound_control.py/bound_die.py) compiles control routes, and it refuses
  `--die-src` (CHECKED, dv_layer_compile.py 1255-1311). So a programme compiled today prices die_b178/fc31 transport
  ages, not the ages of the current bind: plan_s11's table changes 740 of 869 common lanes (sum 10,028 -> 11,918
  cycles, CHECKED). The L0 24 LOWERED / 41 PARTIAL (10-27, UNCHECKED here) is on that legacy tree.
- Root fix (compiler, not padding): extend the bound mode from control to data transports (frame x/ret, svc, coll),
  reading per-bus ages from the strict bind (bind_sinks.json + bind_latency.json), then compile L0 first.
- Vehicle: building the 400-700 GB whole-die model before a programme compiles on the same bind gives nothing to run;
  it waits for L0 on the bound mode. ESTIMATE (UNCHECKED, TOKEN-COVERAGE): 8-16 h build, intel1 only.
