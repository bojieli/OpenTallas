#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-s81-idxnet/src
O=/srv/opentallas-scratch2/claude/codex-s81-idxnet/$1
case $1 in
 tree) bash results/s81_idxnet_1025/run_vmtx_tree.sh "$O";;
 qfs) bash rtl/dsrom_sys/s81_dv/idx/test/run_idx_qfs.sh "$O";;
esac
