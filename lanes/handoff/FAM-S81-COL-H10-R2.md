# FAM-S81-COL-H10-R2 handoff (successor of FAM-S81-COL-H10; updated 11-21 07:5x PST)
Family: S81 col_h10_r1/r2/r0_p1/r0_p4. Census + ROM-PVAL finding: lanes/handoff/FAM-S81-COL-H10.md.
Dirs: epyc10 + intel2 /srv/opentallas-scratch2/claude/fam-s81-col-h10-r2 ; predecessor fam-s81-col-h10 (intel1, intel2, and now epyc10 src1 + bind2).
## Results
- pv1619ecc6 J5 sign-off: DRC 0, TT -99.84 (74 below -42: u_sN/qN RDX 33, bn e_r ROM-PVAL 7, xs_q 29, ...), FF hold internal -4.2. COORD 07:45: no setup ECO; J7 RDX + ROM-pval rows fix it; after J7, hold -4.2 = small ECO.
- x2 t2_payload row PROVEN (strict bind + LATCHECK 873/873), posted to S81-J6-ASSEMBLY-R3: epyc10 j7_delta_x2_t2payload.json (94f2d5f35af8).
- Lever 6 u_cf MX delta j7_delta_lever6_ucf_mx.json (6c8c2380f06c). J6-R3 held it pending the porous probe; probe posted 07:5x (shorts = via-on-OBS through-routes, not stubs; both u_cf faces point away from peers) -> recommended release.
- Cleanup done (epyc8 gap dir, intel1 bind dir).
## Live
- Rep cld01bb4ae J5 route ap 0c4abfb40abd (intel1 ot-jobs ...cld01bb4ae-route-key-cardinal-1989934-1795229931/work), DRT. Read signoff/signoff.json checks + tt/ep_tt.tsv. Sign-off -> export (standard export). Expect the GRT->sign-off gap (pv1619 -46.8 -> -99.8).
- Proof A via private-spec (ENV-PROVENANCE; attempts 1 and 2 failed for flow reasons: tree only on intel1, then no provenance record): hub intel2 fam-s81-col-h10-r2/chainP.sh -> run-item fam-s81-col-h10/waveP/spec.json (rt 625a0f6f0e63, J6 wave env, plan 321f4e3369c3, bind2, epyc10 only). Then route privately (run_kit.sh route via ot-run on epyc10) and A/B against J5 pv1619ecc6 (-99.8).
- Proof C via private-spec + A/B OT_RELAY_MID_FIT_CHAIN=1: chainCP.sh -> waveCP/spec.json (srcC = J5 + rt b8c28cb91890 tools, R3 plan 421bc20f1c5d, bindC PASS). Prints relay_mid coverage. The older chainC (waveC, hand spec) will be refused at place by ENV-PROVENANCE; its gen answers COORD's gen-on-matching-tools question.
## Re-arm waiters
- until ssh intel2 grep -q AP_RC ~/coord/autopilot/jobs/0c4abfb40abd/a1.log
- until ssh intel2 grep -q CHAIN_DONE .../fam-s81-col-h10-r2/{chainP,chainCP,chainC}.log
## Next
1. cld01bb4ae sign-off -> export or class read. 2. Proof A place/geom -> private route -> A/B. 3. Proof C place + relay_mid coverage -> post (FAM-S81-COL-R4, COORD).
