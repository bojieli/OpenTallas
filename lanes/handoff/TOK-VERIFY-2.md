# TOK-VERIFY-2 lane handoff (refreshed 2026-11-12 ~07:05 PST)

## 1 Scope
Functional token verification for RTL that lands or is about to land:
(a) ds_native READY bc62f30f4e -> DONE, already on main (ROOT-MERGE-59 train Z; ancestor of d767dc851b).
(b) BUS-GEAR-2 S81 x feed 2:1 gear: TOK-VERIFY on the geared RTL (A/B ungeared vs geared, same base).
(c) S81 token check on main after each merge train that touches RTL (train 60 = KV vN + qc-verify-gaps, next).

## 2 Worktree
intel1:/srv/opentallas-scratch2/claude/wt/tok-verify-2, detached at main d767dc851b (no branch, no edits).
Git dir: intel1:/srv/opentallas-scratch2/claude/tok-verify-1/repo (origin = intel2:/home/ubuntu/OpenTallas).
Run root: intel1:/srv/opentallas-scratch2/claude/tok-verify-2 (scripts s81tok.sh, s81tok_v2.sh; run dirs per name).

## 3 Running jobs
- S81 check on main 8eeefa4716dd (train 60 part: qc-verify-gaps + taps hotfix): ot-run unit oth-ubuntu-1705981-1794496824 on intel1, run dir intel1:/srv/opentallas-scratch2/claude/tok-verify-2/main_8eeefa47, log intel2:~/tok-verify-2-logs/main_8eeefa47.otrun.log (REFCC = main_d767/cc). Worktree now detached at 8eeefa4716dd. main_d767 done.
  Run dir intel1:/srv/opentallas-scratch2/claude/tok-verify-2/main_d767 ; log intel2:~/tok-verify-2-logs/main_d767.otrun.log
  Check: `ssh intel2 'tail ~/tok-verify-2-logs/main_d767.otrun.log'` -> ends with DONE (or FSA/CC rc!=0, FROOT_FAIL).

## 4 Watchers
None on hosts. (Local Claude-side waits only.) Codex: just poll the log above.

## 5 Results not yet posted
Posted 07:4x RESULT main d767 PASS: compile identical to b2, compose AR 769.6 / MTP 2700.0 (new reference, run dir main_d767). Older reference: TOK-VERIFY-1 S81 baseline AR 769.02 / MTP 2691.86 (dfaf, re-confirmed 0 delta on ef870e b2).
Prior b2 compile on ef870e: CC rc 0 all; L0 65 ops (PARTIAL 41 LOWERED 24) rows 949; L2 83 ops rows 1271; L14 92 ops rows 955; L20 84 ops rows 951; HEAD 8 ops rows 98.

## 6 Next steps
1. When main_d767 DONE: read the "===vs .../b2/cc" cdiff block + CC lines + comp.log head.
   PASS = all FSA/CC/COMP rc 0, op/status counts equal to b2, cdiff shows no P/span changes (or explained ones). Post RESULT (PASS/FAIL, sha d767dc851b, command, log path).
2. Train 60: watch `git ls-remote intel2:/home/ubuntu/OpenTallas main`. When main moves past d767dc851b with RTL/compiler changes:
   `git -C <wt> checkout --detach <newsha>` then from intel2:
   `ot-run --mem 96 --threads 16 --hosts intel1 --dir /srv/opentallas-scratch2/claude/tok-verify-2 --stage /srv/opentallas-scratch2/claude/tok-verify-2 --stage /srv/opentallas-scratch2/claude/wt/tok-verify-2 -- env REFCC=/srv/opentallas-scratch2/claude/tok-verify-2/main_d767/cc bash /srv/opentallas-scratch2/claude/tok-verify-2/s81tok_v2.sh main_<sha8> /srv/opentallas-scratch2/claude/wt/tok-verify-2`
   Same PASS rule, diff vs main_d767.
3. Gear: when BUS-GEAR-2 posts paths (see 7), run two arms with s81tok_v2.sh: MAN/BIND/PLANREL env per arm, lat = gear plan s81_latency.json for the geared arm; worktree at gear sha (add one: `git -C .../tok-verify-1/repo worktree add --detach /srv/opentallas-scratch2/claude/wt/tok-verify-2-gear <sha>`). PASS = rc 0, same op counts, only x/xo-lane calendars move, priced delta within AR -2.5..-4.4% (TOK-VERIFY-1 01:52).
4. Post STATE every 60 min.

## 7 Open ASK
- 06:58 ASK TOK-VERIFY-2 -> BUS-GEAR-2: post final gear sha, geared manifest asbuilt_xg + bind dir, ungeared twin on same ready12b base, gear plan + gen.py latency output, plan rel path. Default: wait for their step-5 READY.

## 8 Gotchas
- ot-run refuses commands naming paths outside --dir unless --stage'd (ISOLATION step 3).
- s81tok scripts `cp -al` the 35 GB TYPE-SAFE-5 src_bs into froot (hardlinks; TOK-VERIFY-1 recipe). Do not edit froot files in place.
- compose_tok_ds.py prices committed layer cycles + the --lat table, NOT the cc output; the per-sha signal is the compile rc/op counts + cdiff calendars.
- Default inputs are TYPE-SAFE-5 cand (11-10 plan_h2_2249); fine for regression A/B, not for gear (gear lanes only exist on r12g plans).
- queue post grep: pattern starting with "- " needs `grep -e`.
