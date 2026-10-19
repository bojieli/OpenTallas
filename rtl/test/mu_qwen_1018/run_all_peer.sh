#!/bin/bash
# MU-KV-PEER 10-19: every die-0 coordinator-chain MU case.  usage: run_all_peer.sh ROOT OUT
set -u
R=$(cd "${1:?root}" && pwd); O=${2:?out}; mkdir -p "$O"; O=$(cd "$O" && pwd)
B=$(dirname "$(readlink -f "$0")")
# at most 6 cases at once (each Verilator C++ build -j 4): fits a 16 GB ot-heavy reservation
{ for t in tb_mu_peer_e2e tb_mu_peer_abort lint_peer_mu; do echo "mu $t"; done
  for t in ex_peer_lifecycle ex_peer_lifecycle_mu0 ex_lifecycle ex_lifecycle_mu0 ex_tsvc ex_tsvc_mu0; do echo "ex $t"; done
  for m in ts1 ts2 co1 lc1 cd1 cd2 pc1 ep3 sv1 ab1; do echo "mut $m"; done; } |
  xargs -P 6 -L 1 bash -c '"$0" "$1" "$2/$3" "$4" > "$2/s_$4.txt" 2>&1' "$B/run_mu_peer.sh" "$R" "$O"
cat "$O"/s_*.txt | sort > "$O/summary.txt"; cat "$O/summary.txt"
