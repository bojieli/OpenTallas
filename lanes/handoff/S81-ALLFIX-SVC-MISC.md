# S81-ALLFIX-SVC sub-unit MISC (serdes/eng/seqhost/gunit/bk_sel rows) -- 11-23 17:35 PST
Base: B1 ae3101241d6b (epyc10 s81-j9-r6/b1_tree, used READ-ONLY for PRE with the tree tools). Work dir: epyc10 /srv/opentallas-scratch2/claude/s81-allfix-svc-misc (scripts inbase.py, inbase_ptr.py, keyhash.py, apply_ptr.py, eng_pre.sh). epyc7 tree fork failed; no private tree; epyc10 disk ~70 GB, so keep to one plan.
Posted: ADOPT to S81-MISC-SERDES-J9 16:34 (no reply yet); ROW-REBASED batch to S81-ALLFIX-INT (hub 4d019a48d64).
NEW rows:
- ENG-HXFACE-1 ops 503cbe8a158d -> plan_b1_eng_hxface.json ff0626d19bcb, PRE PASS 0/178.
- serdes t2 RTL x3: plan s81-misc-serdes-j9/rows/plan_b1_serdes_rtl3.json 6e0fb23a41fd, PRE PASS 0/178. Needs tree files ot_pl_land.sv b96518167517 + flat_lp.sv d16ec5728426. The KLOCK lp.py hook is not landed.
IN-BASE: RCKROOT-1, LOCKUP-1, TXFACE-1 (v2), CORETAP-1 v2, DECSITE-1 + T4T14, ENG-UEH0-CHAN-1, ENG-XT1-STN-1, hop-eng, eng relay_lockup (reset-async), SEQHOST-VLG-STN-1, GUNIT-L1-REACH-1, BKSEL-IDS-RSPLIT v2.
Owed after compose: probes on the composed bind (eng__t1 hx hold + reset-async re-read; seqhost; gunit; serdes t4/t14).
Live units (not mine): MISC-SERDES-J9 scoped bind 5802d62df515 (epyc10 comb_b1), t2 P13 pair-CTS, t2row.
## 17:50 PST: took over S81-MISC-SERDES-J9 serdes/eng/gunit/seqhost (hub e47c5c02, ea556fd5)
- P13 triple pair-CTS (unit oth-ubuntu-1856062) ended rc 0 and was posted (hub ee234d68). Worst hold is now -225.99 inside the ring dsel (skew +313); FF gate -206.9 PASS. FABLE-RC ruled it structural; the SERDES-RING sub-unit owns RING-ONEGROUP. t2 stays HELD.
- t2 probe bind (t2b1/bind.sh) DIED with TOOLROOT; fork_bind never started (epyc10 disk HOLD). Not relaunched: t2 is held.
- DCHN-KLOCK lp.py hook + tool + test ON MAIN, ot-push-main @25b59295d482 (lane clone epyc10 s81-misc-serdes-j9/repo, branch claude/s81-serdes-klock-1123).
- MIDVLD EQ proven compositionally (epyc10 s81-allfix-svc-misc/midvld lem.ys/lem.log: L1 induction SUCCESS, L2 reset-align BMC14 SUCCESS); posted hub 2e70c0e1.
- Probes: intel1 tree fork of epyc10 b1_tree, unit oth-ubuntu-2721176, into /srv/opentallas-scratch3/claude/s81-allfix-svc-misc/b1_tree. SLOW: ~3 MB/s from draining epyc10, ETA hours.
  Waiter intel1 probes.sh (pid 2828697, log probes.log). On fork done: eng__t1 private-spec (plan_c2 5802d62df515 + scope_bind_5802d62df515, --goal grt, wave env, host intel1) + run-item.
  On B1 gate BIND_RC=0 (epyc10 compose/b1/gate_1429.otrun.log): seqhost__t1 the same way on the B1 plan + j9_b1_exact_1123_out. Each posts PROBE ... when run-item ends.
  Still owed: diff config.mk vs wave env, hotspot_census.py run --bound-ps -42, re-read eng reset-async -22.1 + hx_res hold.
  If the fork is too slow, these probes ride the ALLFIX amendment kits (23:00 slot).
