# DIE-QC-34 — QC fixed-tree provider prebuild (QC-001 step 3) — FAIL retained

Run (intel2 unit oth-ubuntu-2231204, 37 min, `run_prebuild.sh`): Codex `tools/clk/fixed_tree_provider.py`
(codex/qc-provider-clock-0834@d1f6310e9, tools archived to die-qc34/src_pc) around mesh5 `fixed_tree.py`, with
access2_jointpg clock_loads_access (22,365 provider FF loads), qc-import-1 bound bindings, die-qc29 formA landings
(7,885) + die-qc30 b1 PHY stubs (4), reachfix clkonly.v/endpoints, plan_qc_import1, mesh5 backbone_plan, and
`--reserved-access` = the full 185,698-contact PG candidate (2,947,537 rects, sha eca744f0) that is materialized in
`../pg`. Prebuild PG grid == readback pg_rects.json (sha e44d9c27, identical).

- PASSED: endpoint access 7,889/7,889 (VIA78 landings incl. 4 PHY stubs; the old mesh5 run stopped here at 32).
- FAILED (CHECKED, `prebuild_FAIL_no_clock_track.json.gz`): `top access reservation` stage, PlanError
  **65,862 no_clock_track** on 43,896 of 44,591 nets (23,772 M8 trunks, 19,106 drivers, rest jogs/drops) incl. the root
  trunk ck_nr0 (M8 ideal y 12463.335). Systemic (98% of nets), not local congestion.
- Hypothesis (UNCHECKED): the full PG access reservation (M8 access runs from each stack to the nearest same-net M9
  strap, 109,168 groups) occupies the M8 inter-stripe channels the clock trunk/driver tracks need; the PG access was
  planned landing-first for the 7,889 M7 landings but not against the clock M8/M9 trunk tracks.
- Control LIVE: same run WITHOUT --reserved-access (`run_prebuild_ctl.sh`, unit oth-ubuntu-3680533, out
  die-qc34/prebuild_ctl_noaccess). If it passes the track stage, the cause is the PG access reservation -> fix =
  reserve the planned clock trunk/driver tracks first and replan PG access around them (same landing-first order),
  not a new check.
