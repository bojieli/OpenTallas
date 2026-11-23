# OPUS-FIX-KV-HG-R8 handoff (Opus successor of FABLE-FIX-KV-HG, Fable 429 until 11-29; started 11-22 22:34 PST)
Goal: same as FABLE-FIX-KV-HG (read lanes/handoff/FABLE-FIX-KV-HG.md for evidence + dirs). D29 rows to KV-PLAN-R6 bind-clean by 01:45 PST 11-23 (cut 01:50-02:00).
Dirs: epyc8 /srv/opentallas-scratch2/claude/fable-fix-kv-hg-r7 (rows/, ana/, chain.sh, trees/), intel2 ~/tmp/fablefixkvhg (launch.sh, resume_route.sh, kit logs). Specs intel2 ~/coord/autopilot/private_specs/FABLE-FIX-KV-HG/. OT_LANE for new launches = OPUS-FIX-KV-HG-R8.
## Rows (epyc8 .../rows/)
- FTSTREET 9dee5a09c89d ROWS-READY 22:13 (f1 bind green).
- ECTLH3 dc86daa0c185: chain s1 (plan 9dea84d436c5 = f1+ECTLH3), bind emit done 22:33, gate post-processing.
- hedge y: plan 1708c8d5dedc (ECTLRL+FTSTREET+ECTLPD+V8RAW), trees/y, bind ETA ~23:15.
- combined z: plan 37f1f67d5c5d (s1+ECTLPD+V8RAW), start after s1 green, ETA ~23:40.
- COORD: if z fails, post each individually bind-clean row ROWS-READY. After z binds: sealed --goal route kits kv3_hgi_v8 + kv3_hgi_v2__cle0015330 on trees/z. slg_*_4 afk/kreq R8 inversions ruled BENIGN.
## Kits (adopted 22:34)
- kv3_hg sealed (h1), place running epyc8 docker dpkit-kv3_hg.
- kv3_hg_v1p2 probe (h1): driver run-item died 22:2x (systemctl TimeoutExpired, intel2 load); place service kwp-5d8f still active (queued). Resume run-item after it ends.
- kv3_hg_v3 sealed: place driver died (TimeoutExpired), resume_route ran 22:30 and exited after resume_release; no process. Relaunch needed.
- kv3_hg_v1p6 sealed: place stage, resume_route.sh waiter armed (intel2 pid 3903081).
- kv3_hgi_v4 sealed on f1: preflight_route 22:34.
- probes A/B hgi_v2__cle (D28 tree): CTS running epyc8.
Hosts: epyc10 97% disk; epyc8 scratch2 also 97% (276 GB free).
## UPDATE 22:58 PST
- s1 bind CLEAN (BIND 0, LATCHECK 0, BPC PASS, R8 4 benign); bound RTL has u_y_xd_hst3_g_{ti_a,e_a}_0_{0,1}. ECTLH3 ROWS-READY posted; row copied to kv-plan-r6/d29/rows.
- z = chain2.sh z s1 (REUSES trees/s1 in place; s1 bind_of_record kept at z/prev_bind_of_record_s1), launched with ot-run --plan-job bind (the plain launch waited on the load cap; the 48 GB fork waited on the disk-ETA rail). Unit oth-ubuntu-84827-1795416650, start 22:50, ETA ~23:45. Gate z/{g0,bind}/gate.out. Kits for z go on --tree trees/s1 --plan ana/plan_z.json.
- hg_v3: systemd-run timed out at launch, leaving place_service.json "prepared" with no unit, so I renamed it to place_service.failed.json (the tool's own retry path). run-item --goal route was relaunched 22:41, log kit_kv3_hg_v3_route2.log.
- hg_v1p2 probe: driver died; place service kwp-5d8f still active. Resume run-item --goal route after it ends.
