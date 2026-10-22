# HEAD H10 fallback clock correction

Derived from 8d29a1f09 h10f, preserving all physical geometry, links, lane widths and RTL. Existing H10bf GEN safety reports four unlanded crossings on lk_WN3. This successor assigns lk_WN3.clk to ck_head_lep_B, the actual regional endpoint clock for LEP tx3/rx3. The group returns to the existing edge group, exactly as MAIN H10 does; explicit instance-clock binding controls the logical root.

Local route construction: 439 links, 2559 stations, zero route failures, maximum hop 397.8 um. Generated bind table resolves both ends of all four abutted links to ck_head_lep_B; ck_B metadata comes from the existing hd_bind implementation. These are construction and contract checks. Strict whole-top elaboration, regenerated GEN safety, actual clock reach and physical qualification remain pending. Existing MAIN/FB H10/H10b jobs are preserved.

Replay: run the existing tools/s81_dv/head72/run_head_h10.sh with HD_VARIANT=h10cf, a fresh HD_RUN_DIR, and this immutable source ref. It retains exact CLOSED SPR, SPO and MTP peer bindings. Dispatch only through the scheduler after an existing COLLA controller terminates. No functional HEAD CUT-A/B bench is duplicated.
