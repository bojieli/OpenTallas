# LEAF-ROUTE-CBC handoff (updated 11-23 ~01:45 PST)
Lane clone epyc9 /srv/opentallas-scratch3/claude/leaf-route-cbc/clone ; work dir E9=/srv/opentallas-scratch3/claude/leaf-route-cbc/row ; J8 fork j9tree (same parent).
## J9 row 3d J9-LEAF-LANECH+EDGESTRIP (to R5 adfaf0f3fdaedfc9f)
- A/B plans: row/j9_{A,B}_final.json PRE PASS; then tapfix.py (clock added_taps out of core halos; t44 probe died on clk_t19) -> j9_{A,B}_final2.json + PRE (tapchain.sh).
- Strict bind A: row/j9final_bind.sh A (plan_src j9_A_final2, out lanechA3_j9_out, G=j9gateA3), run --crit --mem 380 (R5: real use ~370 GB). NOT yet launched after tapfix.
- t44 in-plan probes: intel2 .../leaf-route-cbc/probe/pfork.sh ITEM PLAN TAG (launch A and B sequentially, as runitem unit names collide).
- Kit-only t44 probe (OT_MACRO_MOVES): place FAIL, OT_CLAND BAND (ring up_s_4N_L0x3_i ratio 1.01).
- Fallback ruling: A-only to R5 if not sealed ~11:00.
## J10
- VIS-DIE a5cb7d854ffa9743b die row J10-LEAF-GROW-276 (vis-die-s81/out/plan_j8_grow.json v2). My j10c.sh composes ON it: lane reshape 151.2x86.4 on 20 types (t14/t75 square), LANECH A, hopfix, tapfix (renumber t8 taps), reprice, PRE -> row/j10c_final.json. v1 compose PRE PASS (65 OK / 10 PARTIAL).
- COORD (2): quick placed probes of t4 and t9 on J10 draft, then read the renders; if the window edge overflows, re-place cores off the blocked N/S face (no Y growth).
- Lane core kit corekit/ot_dsrom_su_hcpost_lane_pr_ls: queued, waiting on epyc9 load cap.
## RC-GAP (hub 601a8437): J10-LEAF-FTCORR (t58/t61/t17 ft corridor + junction tap seeds), J10-LEAF-LANECH-KV (kv_leaf t1/t4), J10-LEAF-RST-PIPE (step 2 after R10 ASYNC_TREE); R10 owns SELREP + reset RTL.
