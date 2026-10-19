#!/bin/bash
# MU-ADOPT-HROOT 10-19: every host-root MU case.  usage: run_all_hroot.sh ROOT OUT
set -u
R=$(cd "${1:?root}" && pwd); O=${2:?out}; mkdir -p "$O"; O=$(cd "$O" && pwd)
B=$(dirname "$(readlink -f "$0")")
for t in tb_mu_hroot_e2e tb_mu_hroot_collide tb_mu_lprg_lockstep tb_mu_lprg_lockstep_s2 lint_guard_mu; do
  "$B/run_mu_hroot.sh" "$R" "$O/mu" $t > "$O/s_$t.txt" 2>&1 & done
for t in ex_endpoint ex_endpoint_mu0 ex_lifecycle ex_lifecycle_mu0; do "$B/run_mu_hroot.sh" "$R" "$O/ex" $t > "$O/s_$t.txt" 2>&1 & done
for m in ep1 ep2 al1 al2 kp1 kp2 kp3; do "$B/run_mu_hroot.sh" "$R" "$O/mut" $m > "$O/s_$m.txt" 2>&1 & done
wait
cat "$O"/s_*.txt | sort > "$O/summary.txt"; cat "$O/summary.txt"
