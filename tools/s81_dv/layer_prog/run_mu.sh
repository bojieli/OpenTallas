#!/bin/bash
# MU-S81/TOK (10-19) run_mu.sh <die tree R> <out dir O> <prog L0 base> <prog L0 mu> <prog L2 mu>
# The multi-user bench on the REAL dsdv_seq_host (+ ot_dsdv_fixed_issue): one Verilator 5.050 build of
# tb_dv_prog_seqhost (run_seqhost_prog.sh), then
#   base        the committed single-user L0 programme, default TB (no +mu): check_seqhost PASS (TB default unchanged)
#   L0_all      S000 (not duplicated): all 46 AR users of the --phase-q 4 calendar on one seq_host, vs L0_single (user 0)
#   L2_A / L2_B S002 (duplicated): copy A's 23 users (latency user 0 first) / copy B's 23 users, vs their first user alone
#   mutants (check_mu must FAIL; the issuer must FAULT where stated):
#     m_shift4  users {0, +4}: 2 contexts issue the same V engine on one edge -> fixed_issue code 9 (collision = fault)
#     m_ctx3    users {0, +8, +16}: a 3rd job while both contexts are live -> code 5
#     m_raw     users {0, +21313} (the 1-cycle-grid calendar shift): off the 4-edge start phase -> code 5
#     m_drop    L0_all with +drop_user (issuer job_user forced 0): the user field dropped -> context beats wrong
set -u
R=$(realpath $1); O=$2; mkdir -p $O; O=$(realpath $O)
PB=$(realpath $3); P0=$(realpath $4); P2=$(realpath $5)
H=$(cd "$(dirname "$0")" && pwd)
CK="python3 $H/check_mu.py"
mkdir -p $O/base; CYC=3000 bash $H/run_seqhost_prog.sh $R $PB $O/base > $O/base/summary.txt 2>&1; cat $O/base/summary.txt
TB=$O/base/obj/tb
[ -x $TB ] || { echo "MU BUILD_FAIL"; exit 3; }
run() {  # run <name> <prog> <mu file> [plusargs]
  local n=$1 p=$2 m=$3; shift 3
  mkdir -p $O/$n
  local N=$(grep -c . $p/prog/host_boot.memh)
  /usr/bin/time -v -o $O/$n/run.time $TB +dir=$p +n=$N +cyc=3000 +mu=$m "$@" > $O/$n/run.log 2>&1
}
mk() { $CK --make $1/prog/mu_slots.json --copy $2 --out $3 ${4:+--first $4} > /dev/null; }
mkdir -p $O/mu
mk $P0 A $O/mu/L0_all.txt; head -1 $O/mu/L0_all.txt > $O/mu/L0_single.txt
mk $P2 A $O/mu/L2_A.txt; head -1 $O/mu/L2_A.txt > $O/mu/L2_A_single.txt
mk $P2 B $O/mu/L2_B.txt; head -1 $O/mu/L2_B.txt > $O/mu/L2_B_single.txt
U1=$(sed -n 2p $O/mu/L0_all.txt | cut -d' ' -f2-); U2=$(sed -n 3p $O/mu/L0_all.txt | cut -d' ' -f2-)
U0=$(head -1 $O/mu/L0_all.txt)
printf '%s\n4 %s\n' "$U0" "$U1" > $O/mu/m_shift4.txt
printf '%s\n8 %s\n16 %s\n' "$U0" "$U1" "$U2" > $O/mu/m_ctx3.txt
printf '%s\n21313 %s\n' "$U0" "$U1" > $O/mu/m_raw.txt
run L0_single $P0 $O/mu/L0_single.txt
run L0_all $P0 $O/mu/L0_all.txt
run L2_A_single $P2 $O/mu/L2_A_single.txt
run L2_A $P2 $O/mu/L2_A.txt
run L2_B_single $P2 $O/mu/L2_B_single.txt
run L2_B $P2 $O/mu/L2_B.txt
run m_shift4 $P0 $O/mu/m_shift4.txt
run m_ctx3 $P0 $O/mu/m_ctx3.txt
run m_raw $P0 $O/mu/m_raw.txt
run m_drop $P0 $O/mu/L0_all.txt +drop_user
chk() {  # chk <name> <prog> <single> <mu>
  echo "$1: $($CK --dir $2 --single $O/$3/run.log --multi $O/$1/run.log --mu $O/mu/$4.txt)"
}
{
chk L0_all $P0 L0_single L0_all
chk L2_A $P2 L2_A_single L2_A
chk L2_B $P2 L2_B_single L2_B
chk m_shift4 $P0 L0_single m_shift4
chk m_ctx3 $P0 L0_single m_ctx3
chk m_raw $P0 L0_single m_raw
chk m_drop $P0 L0_single L0_all
for n in m_shift4 m_ctx3 m_raw m_drop; do echo "$n issuer: $(grep -m1 '^PROG FAULT' $O/$n/run.log || echo 'no fault')"; done
} | tee $O/summary.txt
