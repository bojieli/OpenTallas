#!/bin/bash
set -eu
p=/srv/opentallas-scratch2/claude/codex-hbm-l1p-prune
cd "$p"
for spec in "vC_prune_mut 5 3 2 1 0 127 20000 0 -DLDCS_MUT_PRUNE_CARRY"; do
set -- $spec
n=$1; shift
docker run --rm --memory 24g --cpus 8 -v "$HOME/.local/opentallas-tools:$HOME/.local/opentallas-tools:ro" -v "$p:$p" -e HOME="$HOME" -e OBJCACHE= -u "$(id -u):$(id -g)" python:3.12 "$p/run_bench.sh" "$p/src" "$p/runs/$n" "$@"
done
