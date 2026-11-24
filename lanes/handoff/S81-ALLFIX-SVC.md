# S81-ALLFIX-SVC handoff (Opus 5.5; started 11-23 16:30 PST). Brief: localhost scratchpad allfix_brief.txt + resume_1123e.txt + rules.txt.
Family lane: svc*, eng, serdes, gunit, seqhost, bk_sel rows onto S81 B1 ae3101241d6b -> post ROW-REBASED to S81-ALLFIX-INT.
## State 17:50
- Work dir epyc10 /srv/opentallas-scratch2/claude/s81-allfix-svc (epyc10 DRAINING: ot-run --dir must be an existing dir with data, e.g. .../frame). No private tree: epyc7 fork failed (epyc7 cannot reach epyc10); PRE/G0 run against epyc10 b1_tree READ-ONLY (plans in my dir; G0 via frame/g0_wrap.py: plan_dir = b1 plan root, census from frame/census/).
- DONE: native crossings on ae3101 itself: 817 pairs / 604099 bits / 0 dropped (nx_b1/out_ae3101/verify.json).
- SVC-CENSUS-PIECE: census_map_split_1.json (= split_0 + 8 groups svcsplit_svc_{1,3,5,7,9,11,13,15}); census 28 -> 0 on ae3101.
- SVC-FRAME-G0 row: frame/out_f1 (B2 R1 svc deltas: frame_no_new_hops 894, station_t14_svc5_west 6972, svc3_l18 3; 0 conflicts) -> frame/f2_svc_g0.json 7ae818a4c1cd (+ R3 three-layer seam seats + svc15 bypass, 4338 fields / 24 ports, + census map). G0 (frame/g0_f2) and PRE (frame/pre_f2.log) running.
- svc chain rows (WE-STRIP, FACEHOP, ATT-ENG-ORDER rc14/rc20, YTRADE/ES1, LAND-CAP, LOSTART rc25, STRAP, LATFIX, PORTSEG, START-PIN, partner grow, HI4 split x1): IN BASE (svc types of ae3101 == S81-SVC-J9 c13 except clock tap fill + ft_slots from the tail).
- Sub-units: MISC done (lanes/handoff/S81-ALLFIX-SVC-MISC.md; ENG-HXFACE-1 ff0626d19bcb PRE PASS; serdes t2 RTL 6e0fb23a41fd PRE PASS; rest IN BASE); ENG-MON (engine row, boot +11 pricing, rc18 TAP-INV; notes S81-ALLFIX-SVC-ENGMON.md); SVC3 (Codex full-place 1717 adopt: render + PG + endpoint clocks, no route).
