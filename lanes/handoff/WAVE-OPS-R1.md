# WAVE-OPS-R1 handoff (11-22 ~06:50 PST)
W1 dups: 18 items double-launched (04:41 units -51xxx, 05:10 units -53xxx; both share one spec dir a1 and unit.log, state row / OWNERS name the -53xxx unit).
Cancelled (systemctl --user stop of the exact older unit, same as cancel-rows does): 13 where both were live: col_h10_r0_p4 -51258, col_h10_r1 -51262, col_h10_r2 -51263, col_h9_r1 pv4bd36c74 -51269, col_h9_r2 cl87f3ff59 -51269, dsdv c1x_C t9 -51270, c3x_C t1 -51270, lepe_mu_C -51271, lepe_mu_LP t2 -51271, lepw_mu_C -51271, lepw_mu_LP t2 -51277, lepw_mus_C -51277, lepw_mus_LP t2 -51278. Kept the recorded -53xxx unit of each (tie on stage; recorded wins).
Already one live (older unit dead): col_h9_r0_p6, col_h9_r2 clce45cab5, dsdv iq_C, kv512_C: nothing to do. dsdv lepe_nh_mus_LP t1: both dead (row stage geom).
H1: main 7d5348dba7 kit_wave_edit refuses no-op hold records on stops_off dies; hold_items removal needs --expect-launch N (dry select count, prints LAUNCHABLE n); event_census hold passes N from a dry run. Lane clone intel2:/srv/opentallas-scratch2/claude/wave-ops-r1/repo.
Open: watch next ticks that no -53xxx row turns CANCELLED/dead.
- 11-22 18:0x RESUMED then DONE: T1 1c8b40168f landed; 0 TOOLSKEW fails 08:05-17:xx; W1 dups, H1 7d5348dba7, HOLD-LEAK 397d746987 done. P1 (ot-run ticket) open with FLOW-FLEET-R2.
