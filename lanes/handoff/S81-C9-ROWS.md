# S81-C9-ROWS handoff (Opus 5.5; fresh post-limit lane, started 11-24 07:45 PST). Report to S81-ALLFIX-INT.
Job: drive S81 scoped c9 rows to ROW-REBASED / ROW-DROP. NOT tapskew, NOT kv_leaf rows (other lanes).
Lane dir: epyc9 /srv/opentallas-scratch2/claude/s81-c9-rows (c9_oldcheck.py, oldcheck_c9.json 7536827c6576, bits_other.txt).
c9 plan = epyc9 s81-allfix-int/c9/p6w_c9_geom_model_t3_tap_1124.json 048fa468f0a2.
## 08:07 verdicts posted
- ROW-REBASED: SELLK 1109984697f5 1/1 (plan side; scope gate pending), BITS d2 d3d6e6e041df 588/603 (15 superseded by FT-MACRO/ft geom/COL-FT405),
  LP-CORETAP 2ef1a5f50c30 14/14, LEP-RIP 40ea48d792bf 20/20, SERDES-RING revert 877bf1f92e06 22/22, lk_ES0 AB sidecar 3badadef97b7 in stage.
- BKSEL-ETM-C9: ROW-REBASED as post-seal tree row (copy main b102021b views_off_main dsdv_bksel_q_{ff,tt}.lib 60a761d3fea9/74bf4e996541; pins equal). Offered to run swap+re-seal.
## Open (background ot-wait waiters from localhost)
- SELLK scope gate E9 oth-ubuntu-483920-1795527839 (s81-allfix-svc/gate_c9sellk), in PRE at 07:48.
- VPW WREG scope gate E9 oth-ubuntu-2118116-1795531627 (s81-vpw-cone/gate_wreg_sitegrid, c8 base, 6 scope types); define-append 80/80 appendable on c9; outside exact c9 gate.
- D3 E11 oth-ubuntu-1734004-1795534036 (s81-t2-refloor/rows/D3tapfix_e11_recovery_1124), FILL then ANCHOR/PRE/G0/CENSUS; base = B1 b1_tree -> needs rebase onto c9 after.
## 08:15 COORD orders
- (1) BKSEL swap is MINE after the c9 seal: E11 s81-c9-rows/bksel/bksel_swap.sh (copy+mv both libs, re-seal -> bksel/postseal_bksel_1124.json.gz). Posted to INT 08:13 (reply HOLD to wait). Run via ot-run --hosts epyc11 once materialize_1124 RAN rc0 + prebind_src_1124.json.gz exists; check INT posts for HOLD first.
- (2) D3 rebased directly on c9 in parallel: E9 s81-c9-rows/d3c9 (rec_D3_c9.json, d3c9_row.sh, out/, d3c9.otrun.log); tools rt d56b624b5029. Gate whichever of E9 d3c9 / E11 1734004 finishes first.
