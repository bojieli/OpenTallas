# FAM-S81-COL-H10-R2 handoff (successor of FAM-S81-COL-H10; started 11-21 05:4x PST)
Family: S81 col_h10_r1/r2/r0_p1/r0_p4. Read lanes/handoff/FAM-S81-COL-H10.md for census + ROM-PVAL finding.
Work dirs: epyc10 + intel2 /srv/opentallas-scratch2/claude/fam-s81-col-h10-r2 ; predecessor intel1/intel2 fam-s81-col-h10.
## Live (waiters: see re-arm)
- Rep pv1619ecc6 J5 route ap 4dbbbc4cb44f (intel1 ot-jobs ...pv1619ecc6-route-key-cardinal-3781851-1795233324/work), DRT late iterations ~13 viol. Alt rep cld01bb4ae ap 0c4abfb40abd (DRT early).
  Read: <work>/signoff/tt/ep_tt.tsv + signoff.json. Near-miss ECO allowed if TT within ~10 ps of -42 (u_s13/q6 RDX path); else cld01bb4ae rep.
- Proof A (predecessor): bind2 + LATCHECK PASS 873/873; intel2 fam-s81-col-h10/chain.sh -> run-item wave/spec.json (place+geom). Then private route via ot-run run_kit.sh route on the kit host, A/B vs J5 pv1619ecc6.
- x2 t2_payload row proof: epyc10 bindx2.sh, unit oth-ubuntu-2012452-1795269735, log bindx2_otrun.log (pass = BIND_RC=0 + LATCHECK_RC=0). Tree srcx2 = J5 + plan_x2.json (79d448fd34ea).
  Row: relay_branch u_r0_u_y_x2_2_0 copy u_r0_u_y_x2_2_t2_payload_0 sinks [u_r0_u_t2_payload] D 0 on the 6 col_h10_r0_p4 types. Delta j7_delta_x2_t2payload.json (94f2d5f35af8). Made by relay_branch.branch_rows limit 300 (x2scan.py); the generator gate drops it (measured 584-um leg is class core). r0_p1/col_h9_r0: no candidate (x2 relays carry relay_depth).
- Proof C rebuild (COORD BIND-GEN-TOOLSKEW): epyc10 srcC = J5 src + rt b8c28cb91890 tools (main, contains 87f8bb96ef, unpatched) + R3 plan 421bc20f1c5d. bindC.sh unit oth-ubuntu-2254655-1795270280. Hub intel2 chainC.sh (log chainC.log) -> run-item waveC/spec.json = J5 wave a6 spec + OT_RELAY_MID_FIT_CHAIN=1, hosts epyc10. Reads relay_mid coverage at place. If gen fails: read waveC/root/items/<T>/attempt_1 logs + gen.live.log traceback.
## Done
- Lever-6 row posted to S81-J6-ASSEMBLY-R3: j7_delta_lever6_ucf_mx.json (6c8c2380f06c), u_r0.u_cf R0->MX on 12 types; re-solve of u_cf-pin stations needed in J7.
- Cleanup: epyc8 gap_pvcc166a6d deleted (logs kept in gap_pvcc166a6d_logs); intel1 fam-s81-col-h10/bind deleted.
## Re-arm waiters
- until ssh intel2 grep -q AP_RC ~/coord/autopilot/jobs/{4dbbbc4cb44f,0c4abfb40abd}/a1.log
- until ssh epyc10 grep -q "^ot-run: RAN" .../fam-s81-col-h10-r2/bindx2_otrun.log
- until ssh intel2 grep -qE "CHAIN_DONE|BIND_FAIL" .../fam-s81-col-h10/chain.log  and  .../fam-s81-col-h10-r2/chainC.log
## Next
1. Rep sign-off -> export. 2. x2 row green -> post to S81-J6-ASSEMBLY-R3. 3. Proof A route. 4. Proof C place read -> post R4/COORD.
