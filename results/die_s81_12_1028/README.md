# DIE-S81-12 (2026-10-28): S81 local clock form — re-treed plan (ESTIMATE), built clock GRT0, built-arrival CA with START-TREE-1, duty sweep

Data: intel2:/srv/opentallas-scratch2/claude/die-s81-12. Inputs: plan_s5 (locality model) / plan_s10 (build), region map = bind of
die-s81-8 gate_sspice (398 regions = 398 partitions), v 351.2 ps/mm (335 x spice 1.0485), main locality.py (unchanged).

## 1. Local-form plan, estimate first (plan_eval.py; locality.score with the feed injected + count_align_plan unchanged via cap_reading)
Baseline = CLK-LOCAL-EST-1 fish feed, reproduced exactly (min CA 114.6, D4 2253 / D8 53, 270 long-loop): CHECKED.
Re-tree = edge-swap search on the feed spanning tree (retree.py greedy, then anneal.py simulated annealing; objective long-loop count
+ bits x unshared excess, chain arrival cap). A tree-parent choice from the planner, not a per-crossing tweak (12.16c).

| feed | long-loop (>2.5 ns, off-feed) | LL bits | LL max unshared | D4/D8/FAIL | min CA lo/hi | chain hops / ns | root |
|---|---|---|---|---|---|---|---|
| fish (CLK-LOCAL) | 270 (127 dir. pairs) | 107,962 | 21.31 ns | 2253/53/0 | 114.6/147.9 | 32 / 15.3 | s_0S_L0 |
| rt3 greedy | 221 | 117,154 | 16.42 | 2264/42/0 | 107.6/167.8 | 29 / 14.0 | s_2S_L0 |
| **sb5 anneal (chosen)** | **128 (65 dir. / 34 region pairs)** | **72,237** | **14.85** | **2273/33/0** | **105.0/105.0** | **26 / 12.8** | **s_2S_C** |
All 128 residual long loops are >= 105.0 ps at D8 on the plan-time bound (sb5_long_loops.tsv). ESTIMATE / UNCHECKED (count re-derived
by a second script longcls.py = 128, same model code). Residuals: tier-boundary vertical links (s_xS_L3/L4/x06/x11x), the svc row and
phy_hbm fan-in (renders fish.png / sb5.png VIEWED). Tree-edge crossings 1459 (max 1.88 ns unshared), short loops 719.
Fork start ports (startedge model): 397/397 clean, width median 75 / max 184 ps (limit 208).
Restoring stages every 5 hops: 78 feed nodes — SUPERSEDED by COORD 08:4x (inverter clock tree, see 4).
Faces: the 4 "over supply" faces (svc_2/3, 4/5, 6/7, 14/15, flat 1.039-1.078) are an artefact of locality.tracks using the flat
6 pins/um; these faces declare 3 face_layers (M7/M5/M3) and check.py already budgets 6 x 3/2 = 9/um there (COORD 10-23 07:43):
ratio 0.69-0.72, 0 over. Real pin windows 6.3-6.6 bits/um. No plan change needed (locality.tracks should read face_layers: info).

## 2/3. Built clock (go_build.sh): main die_trial link_htree on feed_sb5 + map398, leaf 200 / rep 250 / --tree-site-slide, plan_s10
36,882 clock cells (8,451 repeaters), 6.23 m wire (feed 568 mm), 106 levels, 8,501 taps, 0 illegal. Die GRT incl clock, 50 it,
crit 0, TT + FF EXIT 0: overflow 0 on every layer (M7 8.58 % max) CHECKED (built/grt_*.txt). Slew: 12 pins > 320 ps per corner,
2 large (ck_r879_3 1.66 ns, ck_r763_4 1.44 ns: legs over the lk_* SerDes macros, same class as DIE-S81-4). Render ctree.png VIEWED:
feed follows sb5 (central row spine + column spines), H-trees in every partition, red = node legs > 450 um (mostly SerDes rows).
Built-arrival CA (post.sh: proof -> main landed_phase_ocv -> count_align_plan, START-TREE-1 --start-tree clock, CA-OCV-1 model:
spice, cppr-lca, clock_variation table, shared droop):
* --start-clean phase: 2306 crossings, D4 2254 / D8 52, 0 FAIL, amb 0, min lo 105.0 / hi 118.1; 492/492 start ports clean
  (95 virtual / 91 retime nodes), port width median 287 / max 561 ps. CHECKED (own run).
* --start-clean width (release target): 4 FAIL (svc_5<->seqhost / s_3S_C, 2 cycles path ambiguity), 815/841 start ports clean,
  26 unclean (svc_0/1/4/8/12/13/14/15, lk_WS0/1, phy_hbm/lk_ES0 retime nodes), width max 582 ps. NOT YET MET.
* old data start tree on the same arrivals: 201 FAIL (start tree is the cause, as START-TREE-1 found).
* die STA start-port recheck (main die_sta_related + bind, phase; bind run without --parts ocv, STA keyed part = region here):
  COUNT-ALIGN TT worst lo 104.8 / hi 119.3, FF 108.3 / 228.9, 0 fail, start-skew fail 0/492, PASS. CHECKED.
  Same run: intra related pairs FAIL — FF hold -421.7 (kit-contract W180 -194.3, needs W 374), skew 432 TT / 374 FF: in-partition
  H-tree balance on big partitions (same failure class as DIE-S81-4). Not a gate pass.

## 4. Duty-cycle risk sweep (COORD 08:4x; QC-11 duty_eval.py, both edges, spice x1.0485/x1.0552, lib DFF MPW)
| clock | TT duty min/med/max | TT outside 45-55 % | MPW fail TT / FF | fall-rise TT med/max |
|---|---|---|---|---|
| current built packed-G (Codex clock_G_body) | 0.53 / 1.14 / 1.63 | 8111/8127 | 5408 / 4359 | 531 / 937 ps |
| DIE-S81-12 local BUF build | 0.56 / 1.25 / 1.88 | 8501/8501 | 7528 / 6843 | 625 / 1149 ps |
MEASURED (clock GRT reruns with fall arrivals: duty/d_*, duty/l_*). OpenSTA report_check_types -min_pulse_width prints nothing on these
clock-only netlists (ports, no sequential sinks), so MPW is the lib DFF value from duty_eval. Both S81 forms fail: the inverter tree
(die_trial --clock-cell inv, QC-11) is required; the BUF local form is not a release form.
