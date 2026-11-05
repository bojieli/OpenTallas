# HBM-BIND-10 (11-05): HBM C-form plan event, bind-complete

Candidate plan event for the HBM C row form, built by HBM-BIND-6..9 and closed here. Plan files only plus the
bind evidence; nothing in this directory changes RTL or the plan of record by itself.

## What the event is
`delta_714_k13f.json.gz` is a per-item delta (made by `plan_delta.py`) from main 714dd1ea120 d44v `die_plan.json`
to `k13f` = C form (c4/ne4 rows + M8/M9 leftovers r5_NW/r5_NE + keep-lane re-thread k6/k7 + hub<->sm endpoint
reuse c_route8f + spb0->root c_route9 + hub->su00 +805 b) on top of p7 = d44v + B0 / b0l / pair leaf (HBM-BIND-5/6).
It includes the q_sm0 L29_i S-face window +69.168 um (COORD 12:40, option A). 4,095 ops: partitions (32 moved),
ports, lanes, latency.lanes, latency_groups, partition_types buses / ft_slots.

`k13f` = k13 minus 228 stale ops: the C route chain started from an older plan copy and carried old type bodies
(q_hub_nw/ne svg/wbk/hcollgi/hb_coll splits and q_b113 opstore splits reverted to whole cores). `filter_delta.py`
drops every partition_types.*.{hard_cores, contents, clock, internal_stations, cells} op and the die label.

`apply_event.sh` (run from a worktree root) applies the delta to the CURRENT d44v die_plan.json.gz, rewrites it and
its SHA256SUMS line, and prints every conflict. On main 79e52bd98b2 (= 267bb845674 for d44v): 0 conflicts.
Known overlap with DIE-HBM-74 ev74: q_sm0 L29_i (same value) and q_su01 L29x1 (ev74 moves it; C deletes it).

## Evidence (epyc2 /srv/opentallas-scratch2/claude/hbm-bind-9)
- As-built t11 = t10 (main 714dd1ea120 RTL) + obs re-home in the candidate top (`t11_top_obs_rehome.patch`,
  `mk_t11.py`: obs_NW N 209->205, obs_NE N 182->186, xc_NW7..4__done at the obs_NE MSB end; outside SYNC_MASK).
  Elab chain `r_chain11.sh` (r_chain7 steps), all rc 0.
- Strict bind k13 / t11: errors 0, unbound 0, crossings 420, bits 378,992 (`bind_t11k13.txt`).
- Strict bind k13f / t11: errors 0, unbound 0 (`bind_t11k13f.txt`).
- Strict bind m79f (event on main 79e52bd + main side files) / t11 and t12: unbound 0, 1 error = EMIT wavefront
  core reset q_hub_nw/u_hb_coll_Q_body_core__q0__ctl.rst_n (`bind_t11m79f.txt`, `bind_t12m79f.txt`). That core
  is part 28 (main 943aae934ca), after the t-series as-built RTL; it is the same in main and in the event, so it
  is an as-built refresh item, not a plan item. t12 (sub_core_leaf rows only) does not clear it: the as-built
  needs the part-28 split composition (rst_n on the ctl sub-core), like t9 did for parts 27/29/33.
- G0 (check.py, --plan-geom off) on k13, k13f, m79f: the same 23 errors, all schema 'slot in_face == out_face'
  from c4/ne4 (`g0_m79f_errors.txt`), advisory.
- Type changes vs p7 (`tdiff_p7_k13.txt`): 66 types, 2 hard (q_sm0 L29_i; PHY_NC +2 buses).

## TOK (ledger HBM-23, not a gate)
`su_leg_classes.py` / `su_leg_classes_p7_k13f.tsv`: per SU slice max lane cycles by signal class. Worst slice NW2:
pgp.command L1278 96 cyc (p7 6), read data L1280 48 (p7 2). S2 (intel2 ss38-tok/price38.out): round trip +128 ->
1338.18 tok/s (-18.0%), command only -12.1%, return only -8.6%, from 1632.01.
