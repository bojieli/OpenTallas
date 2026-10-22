# S81 Gunit L5 historical view import and native HOLD

All26 immutable files from record87bbb46b9 are QUARANTINED under results/history/s81_gunit_l5_ro3_87bbb46b9. No canonical physical/ref_tile view or closure-result paths are published. quarantine_manifest.json maps original paths to historical destinations and verifies every byte; import_manifest.json retains the original source inventory. No source RTL, kits, shared helpers or main policies were imported. Historical CLOSED means TT setup+26.16ps/FF hold+15.42ps/DRC0; SS setup-298.12ps is sensitivity only.

**Binding eligibility is false.** Actual original6_final.odb has4558 unbound PG ITerms on2279 PLACED/do_not_touch cells (2272clkbuf,6delaybuf,1wire). Canonical native global_connect on a separately loaded copy preserves all4558 failures; OpenDB warns protected cells skipped. Original files were mounted read-only and preserved. TrialODB is separately retained on ep9 and is ineligible. No protections cleared, no custom connection commands, no route launches.

Historical cl/route.a1.sh explicitly exports OT_PG_STRICT=0 at line20. Its saved clk_net_protect.tcl protects CTS clock buffers before repair_timing_helper, with PG-before-protect conditional on strict1. This explains the source obligation; no current holdfix is retroactively attributed to this route.

Final native all-driver census FAIL:264441 examined roots,622 violations/0Liberrors. Clock input1816 is reported separately;621 other violations still fail(max101), including199 sequential/422combinational-or-macro drivers. The complete47MB original report stays on ep9; compact committed report keeps every violation, library/netlist hashes and full-report hash while omitting driver_counts/constant-output details. This census used the exact648ee10c0 macroLib plus containerRVT TT libraries (including3unusedFAKE cell libraries from its wildcard; report lists hashes).

Direct-net endpoint geometry has0>405um; that is narrowly a Manhattan endpoint check, not transparent-cone reach/detailed wire-length/pin registration/physical grid qualification. PG full-grid check is not claimed: logical bindings already fail. Clock spread historical23.7/23.0ps does not waive PG or census. The closed master is dsdv_gunit_l5, a child; there is no dsdv_gunit parent view, so this import cannot remove the die stand-in.

The next eligible implementation needs structural native32 RTL and prospective native-PG-before-protect qualification, then the normal physical route/clock/reach/PG checks. No pure PG ECO suffices for these data-fanout failures.
