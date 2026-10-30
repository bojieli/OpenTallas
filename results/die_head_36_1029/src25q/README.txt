DIE-HEAD-36 fault paths (2026-10-29; OWNER (A) 21:03, COORD DIE-HEAD-35-PARK (1)): local status relay stages.
Tool: tools/die_plan/clock_landings.py _dataflow_monitor reads sidecar field collector.types[T].local_status_depth
(int, or {local status output bus: int}; default 1 = the previous form, byte-identical).  depth d on a LOCAL status
output b adds d-1 ot_dp_landing_collect stages u_cland_loc_<b>_<k> (first N = #landed inputs, then N=1) before the
dedicated output register u_cland_up_<b>.  Status only: 0 data cycles; ready/fault reach the pin d-1 cycles later
(fault sources are sticky, so nothing is lost; START still waits on actual registered root ready).  The aggregate /
tree-bus / observer path is unchanged.  Tree bus, unknown bus or non-integer depth -> LandingError (fail closed).
Test: tools/die_plan/test_clock_landings.py::test_local_status_depth_relays_only_the_local_status_output
  FAILS on origin/main 5d8770d6d (1 failed, 33 passed), PASSES on this branch (34 passed); all 30 landing/collector
  test files in tools/die_plan: 183 passed, 4 skipped.
Byte-identical (CHECKED):
  HEAD src25p (no field): gen_rtl.write_rtl(plan, landing=sidecar) old vs new tools -> 27/27 files identical
    (bytecheck_head.txt, hash e959de0494fcbb14).
  S81 (ws3v2 sidecar, 203 types), QC (die33 sidecar, 119 types), KV (die-kv-40 eW_sidecar, 56 types): collector
    monitor = "reset" -> Landings.dataflow is False -> _dataflow_monitor (the only changed function) is never called.
    HBM: no plan on main has clock.landing_network -> no landing RTL at all.  (Full write_rtl on S81/QC needs each
    die's leaf RTL environment; it fails identically before landing on both old and new tools.)
HEAD source src25q = src25p + local_status_depth on 3 types (src25q_status_depth.py, intel2
  /srv/opentallas-scratch2/claude/dh36a/src25q; plan unchanged sha dfc1826f..., sidecar sha in src25q_report.json):
  depth = ceil(max Manhattan(local source pin -> status pin) / 450 um):
    hd_st_str d_o, hd_st_n3_transit d2_o, hd_st_m tx_o: path 1442.88 um -> depth 4 (3 relays), hop 360.7 um.
  Only these 3 wrappers change (+14/-2 lines each, the relay stages; asserted by the script).  Boot budget unchanged:
  the sidecar's local boot depth (local_registered_depth 5) already exceeds 4.
Strict die port-bind on src25q (DIE-HEAD-33 run_source_portbind.py): HEAD_DIE_PORTBIND_SOURCE PASS, nested PASS
  (4308 instances) (bind/portbind_run.log).
Benches: bench/relay.log = generated depth-4 form vs depth-1 reference delayed 3 cycles, 4074 checks 0 errors, sticky
  fault +3 cycles and held; existing rtl/test/meso/tb_landing_collect 576 checks 0 errors (bench/collect.log).
Synth LEC vs the relay-added RTL golden: runs in the HEAD-KITS-U kit rebuild (kit lec.py); not run here (UNMEASURED).
Same class NOT in this event (COORD scoped 3 types; local status path > 450 um at src25p, depth by the same rule):
  hd_spn_end 6, hd_st_turn 4, hd_st_n4 5/5/4, hd_st_k5 4/5/5, hd_st_n3_turn 3, hd_mesh 4/3, hd_lep0N 5-6,
  hd_ctl 2/2/2/3, hd_host 4/3, hd_ctl_n 4, hd_host_n 4.
