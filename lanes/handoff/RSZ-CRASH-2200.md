# RSZ-CRASH-2200 handoff (2026-11-20)
DONE. Census: 30 RSZ-0074 logs (~20 kits), all GRT-stage tt_setup_repair, all fatal on the OLD tcl (no chunk catch). Full text posted to lanes/posts/RSZ-CRASH-2200.md.
Fix pushed main 504fcadebf6: dont_touch regexp stripped the quotes of the net name (test_tt_setup_repair.py::test_rsz0074_net_name_is_unquoted_for_dont_touch).
Open: kits keep old tt_setup_repair.tcl until flow refresh; near-closing retry list was posted to COORD (sle_hc1__cl7d360508, slice_station__t40__cl1ea9de02, glue, hd_tile tilecomb3s, coll_ftc, hd_ctl a2). Not relaunched.
## Stand-down 11-20 22:1x
- failure_breakdown labels RSZ-0074 / tt_setup_repair_fallback as INFRA[rsz_crash] (test added). tools/rsz_crash_watch.sh (nohup, 12 h, every 30 min over 6 gen hosts) posts INFRA[rsz_crash] once per new fallback to RSZ-CRASH-WATCH; restart it if it ends: nohup bash ~/coord/tools/rsz_crash_watch.sh &
- hd_tile tilecomb3s resume skipped (HEAD-PLAN-R16 owns). Successor FLEET-WATCH-2000.
