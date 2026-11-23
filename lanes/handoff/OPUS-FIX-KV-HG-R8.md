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
