#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-s81-idxnet/src
O=/srv/opentallas-scratch2/claude/codex-s81-idxnet/$1
bash rtl/dsrom_sys/s81_dv/slice/test/run_lep_idxnet_bench.sh "$O" "$1"
