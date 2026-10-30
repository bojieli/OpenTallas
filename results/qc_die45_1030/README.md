# DIE-QC-45 (QC die owner), 2026-10-30

Plan: plan_qc43 (sha e630ffb8). Run: the DIE-QC-44 TRIAL1 G2 die GRT (complete_pg/provider.odb, signal M4-M9, clock
M4-M7, 0 overflow) re-read on epyc2 `/srv/opentallas-scratch2/claude/die-qc-45`. All numbers are this lane's own and
UNCHECKED by NUMBER-CHECK. The exception is the PG census, which is an exact geometry count.

## (1) Related-pair die STA on the TRIAL1 arrivals
- Arrivals: `sta/edge_readout.tcl` reads the GRT RC and the clock SPEF and dumps rise and fall for every clock cell
  and tap. `mk_edges.py` resolves the source-rise edge. 44,590 CKINVDCx16 cells, 0 ambiguous taps. main
  `trial_tap_arrivals.py` then builds the proof: 7,889 taps, 313 regions, 0 missing.
- Shared `die_sta_related.py` (`run_sta.sh`: --cppr-lca, --clock-ocv table, --clock-droop shared,
  --clock-cal spice_edge):
  - intra: TT setup +91.53 ps, FF +180.97, 209,284 pairs
  - seam: TT setup +162.09 ps, FF +245.35, 7,012 pairs
  - coverage: 377 parts, 0 uncovered bits
  - hold: BLOCKED(kits). There are 0 measured pairs because QC has no signed views. Under 12.19 this is UNMEASURED,
    not a failure.
- What "1590 ps between neighbour taps" means: those taps are in different regions. They are LANDED (count-aligned)
  crossings, 414,044 pairs. The +-T/2 default window says FAIL, but that is not a verdict. QC has no
  count_align_bind file yet, so the landed class stays UNMEASURED until `--count-align BIND` runs.
- In-region spread (diagnostic, not a gate): intra max 196 ps FF, seam 174 ps. 58 DME regions are above the 12.15c
  150-ps target, and every one of them is a c_*_b{f,n}_11 region. The cause is the stage model. The tree was priced
  with inv2_ndr_qc_trial13b, and on the retained placed-stage legs that model has 18.15 ps rms. The refit on these
  routed legs (`refit/refit_trial1p.json`, ot_clk refit --placed-stages, 19,458 legs) gets 4.96 ps rms TT and
  4.13 FF.
- Estimate for a DIE-QC rebuild with the refit model (`path_model.py`): the worst residual in-region spread is
  82 ps TT, and 0 regions stay above 150.
- Decision: no related pair fails (setup passes, hold is unmeasured), so no clock variants were started. Variant A is
  queued for the next tree rebuild only: the region DME with the refit model.

## (2) PG IR
`pg_census.py`: the complete-PG ODB M8/M9 grid equals the plan grid exactly (M8 3040/3039, M9 3613/3612 VDD/VSS, 0
missing). The QC-PG-5 plan-grid PDNSim (worst 33.95 mV < 35) therefore applies to this ODB. Added clock/provider
load, by estimate: about 0.5-0.6 W die-wide, which adds 0.2 mV or less. IR PASS by grid identity plus estimate. A
real PDNSim on this ODB was not run.

## (3) Pin abutment (materialized abstracts)
FAIL. `abut_check.py` checked 1,277,486 plan port bits:
- 823,352 abutted
- 438,159 not touching
- 15,975 touching but misaligned

The cause is 221 of 377 partitions sitting 0.02 or 0.04 um off their plan origin_um: 126 c_*, 94 sl_*, 1 io. Most
of them equal round(origin, 0.1 um). Master sizes match the plan. The clock taps follow the shifted pins
(7,889/7,889). Fix: materialize at the exact plan origin (die-local), then re-check.

## (4)/(5)
- coll_ucie: the PHY is 777.6 um wide, but the core width is 768.96 → plan delta in the next QC plan event.
- coll_ft stage sites: waiting on the kit regen (DIE-QC-44 ruling).
- VMR V1 signed off → handed to SIGNOFF-SPRINT-1.
