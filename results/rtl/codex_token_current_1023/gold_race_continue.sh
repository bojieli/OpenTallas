#!/usr/bin/env bash
set -u
S=/home/ubuntu/scratch/codex-tok-0355-1023
B=/srv/opentallas-scratch/claude/tokd-hbm2/r18h5_src
L=/home/ubuntu/claude-takeover-20261007/lanes/CODEX-TOK-0355-1023.md
while :; do
  if timeout 25 ssh -o ControlPath=none ot-epyc9 "test -x $B/out/obj/Vtb_hbm_slice"; then
    printf '%s EP9 binary ready; existing source driver owns all15 replay sets.\n' "$(date -Is)" >> "$S/race.log"
    exit 0
  fi
  if timeout 25 ssh -o ControlPath=none ot-gold1 "test -x $B/out/obj/Vtb_hbm_slice"; then
    printf '%s GOLD binary ready; launch exact frozen fifteen sets via supported reuse.\n' "$(date -Is)" >> "$S/race.log"
    env OUT="$S/gold_reuse" FROZEN=/home/ubuntu/scratch/tokd-hbm2/r18h5_src/bundle/slice BIN_HOST=ot-gold1 BIN_ROOT="$B" SRC_REV=d34578d6f CONTRACT=/home/ubuntu/scratch/codex-hbm-chain-2140-1022/r18h5/contract_pre.json RUNROOT=/srv/opentallas-scratch/codex/tok-0355-1023/gold_reuse RUN_PAR=8 RUN_MEM=64 TAG=codex_tok0355_gold bash /home/ubuntu/wt/tokd-hbm2-tools/tools/hbm_layer_vehicle/tok_func_hbm.sh --reuse > "$S/gold_reuse.log" 2>&1
    rc=$?
    { flock 9; printf -- '- [CODEX TOK %s] Gold1 exact r18h5 SOURCE fifteen-set replay terminal rc=%s; classify %s/gold_reuse/report.json. EP9 original build preserved.\n' "$(date +%H:%M)" "$rc" "$S" >&9; } 9>>"$L"
    exit "$rc"
  fi
  sleep 60
done
