# Recovered KV physical chain

The source launcher `kvs14p.sh` is recovered from claude/kv-plan5-1018
fa7fe4ff9 onto current main. The sixteen forwarded-lane views retain their
CLOSED closure-record provenance in `kvs14p_views.tsv`. The optional r7t D2D
view is deliberately not imported: its NTX/TXDP and native-port qualification
are not the actual die configuration. Explicit NTX/TXDP graph bindings are
restored separately from the unqualified attention landing branch.

This source is **not a qualified die input**. `KVS14P_DIAGNOSTIC=1` is required
to invoke the recovered launcher; its result is always NOT_A_DIE_RESULT.
Physical lane prep must include `kv_lane_reach.py` from 64d77f341 (or its main
merge). That gate has no diagnostic bypass and refuses the known invalid
transport reach before any physical case/CTS/GRT job. A diagnostic invocation
is only useful after a concrete question has a legal source graph.

HKV-STATIONS 10-19: step 1 is IMPLEMENTED in kv_fwd_lanes.py + kv_lane_stations.py: every overreaching
incident hop gets a real relay stage (all slices of the bus, re-formed into its lane role, recompiled n/E/K/landed
age) and unslotted wide landings get a legal free frame. On the fa7fe4ff9 actual inputs the reach gate goes 17,130
overreaching bits -> 0, unmeasured 0, PASS (evidence/lane_stations_fa7fe4ff9.json: 178 stages, 4 moved landings,
0.0905 mm2, +1/+2 fixed edges on 128 buses). Steps 2-6 remain.

Next qualifying chain, in dependency order:

1. Repair incident relay reservation/stages, including the two wide unslotted
   landing runs rly_aq_WS_73 and rly_pvin_WN_3_40. MY-to-R0 adaptation solves
   track-grid legality but creates extra long actual pin spans: the adapted
   fa7fe4ff9 graph fails 16,060 transport bits in 170 distinct instance pairs.
   Require `case_kv/lane_incident_reach.json` status PASS with no unmeasured
   actual endpoints. Recompile every changed age/calendar; never waive reach.
2. Use each lane view's real independently measured clock insertion (ck_s or
   ckf alongside ck). No zero-insertion or all-sink substitution. The restored
   measurements use structural first/last sequential data cones so false-path
   constraints cannot hide boundary flops. Preserve original insertion evidence.
3. Bind actual ASTK expanded leaves, resettable in-strip relays and registered
   fault glue. They are work in progress; generic no-reset relays cannot stand
   in for the actual RTL. Include the distributed e-read tap and its exact ERL
   only once its real views and cycle programme are qualified.
4. Resolve D2D configuration's double producer (dcal versus boot link_cfg),
   bind the actual closed NTX=3 / compiled TXDP view, and pass native bind.
   The optional historical r7t view is not adequate evidence for this step.
5. Reconcile the compiler with actual current source: attention PV_LEAD/F_DLY,
   registered embedding I/O and slots, group-chain position ages, updated
   programme loader/dispatcher and sequencer views. Price a tree alternative
   for the group-control chain as recorded in KV-PLAN5. Preserve fixed-cycle
   execution with no production credits or backpressure.
6. Exact clean source prep -> strict physical-lane bind -> compiled relay/
   bundle equality -> native port bind -> real case + PDN -> GRT -> TT setup,
   FF hold and DRC 0 -> die clock delivery at each pin's phi minus measured R,
   landed pairs and reset-release window. Report SS sensitivity. A marker or
   placeholder anywhere prevents a real die qualification claim.

No recovered launcher or view import changes a CLOSED tile's sign-off.
Missing or failed prerequisites remain blockers rather than ideal assumptions.
