# S81-ALLFIX-SVC sub-unit MISC (serdes/eng/seqhost/gunit/bk_sel rows) -- 11-23 17:35 PST
Base: B1 ae3101241d6b (epyc10 s81-j9-r6/b1_tree, used READ-ONLY for PRE with the tree tools). Work dir: epyc10 /srv/opentallas-scratch2/claude/s81-allfix-svc-misc (scripts inbase.py, inbase_ptr.py, keyhash.py, apply_ptr.py, eng_pre.sh). epyc7 tree fork failed; no private tree; epyc10 disk ~70 GB, so keep to one plan.
Posted: ADOPT to S81-MISC-SERDES-J9 16:34 (no reply yet); ROW-REBASED batch to S81-ALLFIX-INT (hub 4d019a48d64).
NEW rows:
- ENG-HXFACE-1 ops 503cbe8a158d -> plan_b1_eng_hxface.json ff0626d19bcb, PRE PASS 0/178.
- serdes t2 RTL x3: plan s81-misc-serdes-j9/rows/plan_b1_serdes_rtl3.json 6e0fb23a41fd, PRE PASS 0/178. Needs tree files ot_pl_land.sv b96518167517 + flat_lp.sv d16ec5728426. The KLOCK lp.py hook is not landed.
IN-BASE: RCKROOT-1, LOCKUP-1, TXFACE-1 (v2), CORETAP-1 v2, DECSITE-1 + T4T14, ENG-UEH0-CHAN-1, ENG-XT1-STN-1, hop-eng, eng relay_lockup (reset-async), SEQHOST-VLG-STN-1, GUNIT-L1-REACH-1, BKSEL-IDS-RSPLIT v2.
Owed after compose: probes on the composed bind (eng__t1 hx hold + reset-async re-read; seqhost; gunit; serdes t4/t14).
Live units (not mine): MISC-SERDES-J9 scoped bind 5802d62df515 (epyc10 comb_b1), t2 P13 pair-CTS, t2row.
