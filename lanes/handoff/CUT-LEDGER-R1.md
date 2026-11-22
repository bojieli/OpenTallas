# CUT-LEDGER-R1 (Sonnet; class K1 of FABLE-FLOW-0600)
- 11-22 05:5x PST task 1 done, posts sent: KV D28 (FIX-SYNC-KVHEAD c2736959a155 and KV-RINGMAC-R1 3a0f01f89763 not in rows.json; PV-R7 and HGI-R6 have no rows file), S81 J8 (IQF-R1 499b52ae75d6 and SERDES-R7 j8-phy-eng dir not in intake), QC V4 (3 OPTIONAL padleaf + rstcotap not ranked).
- TODO re-check KV 11:00 PST (ls d28/rows on epyc8 vs rows.json, new ROWS-READY posts) and S81 15:30 PST (intake list vs posts "J8 ROWS").
- Task 2 landed: main bc9603f67b tools/die_plan/cut_ledger.py + test_cut_ledger.py. Use: cut_ledger.py compose --die KV --event D28 --base ... --out ... --manifest rows.json --rows-dir d28/rows ; then cut_ledger.py seal --die KV --event D28 [--allow-drop ROW]. Ledger autopilot/CUT-LEDGER-<die>-<event>.tsv; ACK file autopilot/CUT-ACK-<die>-<event>.tsv.
- TODO: ask KV-PLAN-R6 / QC-PLAN-R13 / S81-J6-ASSEMBLY-R5 to switch d28_compose.py / their compose to it and call seal before seal_wrap.sh.
