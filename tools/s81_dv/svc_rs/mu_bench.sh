#!/usr/bin/env bash
# MU-S81/SVC (10-18): per-user HBM bases on the dsdv_svc_rs 16-slice exact bench (tb_dsdv_svc_rs, TB-only MU mode; RTL
# unchanged).  Builds the protect-lib bench once (rs_bench_pl.sh, base variant: the mutants are TB plusargs), then runs:
#   single_u0   tail46 alone as user U0 (sb0 = SB0), +trace                        -> PASS, the single-user reference trace
#   mu          job 0 = tail46 as user U0 (SB0), job 1 = short300 as user U1 (SB1), both users' owned rows in ONE HBM image
#               and both users' window rings written by OWN_ROW, +trace            -> SVCRS_MU verdict=PASS, job-0 trace
#               lines identical (cycle and data) to single_u0
#   mut_sb      mu with job 1's WIN_LOAD SB = SB0 (user 0's compressed rows)     -> job 1 FAIL
#   mut_user    mu with job 1's WIN_LOAD user = U0 (user 0's window ring)        -> job 1 FAIL
#   single_u1   short300 alone as user U1 at SB1, +trace                          -> PASS (relocation reference for job 1)
#   default     tail46 with no MU plusargs                                        -> the committed single-user line
# Usage (repo root): tools/s81_dv/svc_rs/mu_bench.sh OUTDIR VECDIR
set -euo pipefail
O=$1; VEC=$2
U0=${U0:-0}; U1=${U1:-1}; SB0=${SB0:-1000}; SB1=${SB1:-a000}
export DIE=0 ST=0 SEEDS=1
tools/s81_dv/svc_rs/rs_bench_pl.sh "$O" "$VEC" base          # build only (no case)
BIN=$O/base_d0s0/obj/Vtb_dsdv_svc_rs
R=$O/mu; mkdir -p "$R"
run() { local n=$1; shift; "$BIN" +seed=1 "$@" > "$R/$n.log" 2>&1 || true; }
run single_u0 +dir="$VEC/tail46" +u0=$U0 +sb0=$SB0 +trace=1 &
run mu        +dir="$VEC/tail46" +u0=$U0 +sb0=$SB0 +dir2="$VEC/short300" +u1=$U1 +sb1=$SB1 +trace=1 &
run mut_sb    +dir="$VEC/tail46" +u0=$U0 +sb0=$SB0 +dir2="$VEC/short300" +u1=$U1 +sb1=$SB1 +mumut=1 &
run mut_user  +dir="$VEC/tail46" +u0=$U0 +sb0=$SB0 +dir2="$VEC/short300" +u1=$U1 +sb1=$SB1 +mumut=2 &
run single_u1 +dir="$VEC/short300" +u0=$U1 +sb0=$SB1 +trace=1 &
run default   +dir="$VEC/tail46" &
wait
for n in single_u0 mu mut_sb mut_user single_u1 default; do
  echo "== $n"; grep -h -E '^SVCRS(_JOB|_MU)? ' "$R/$n.log" || echo "NO VERDICT"
done
# job 0 of the MU run vs the single-user run: every output event, same cycle, same data
grep '^SVCRS_TR 0 ' "$R/single_u0.log" > "$R/tr_single_u0.txt" || true
grep '^SVCRS_TR 0 ' "$R/mu.log" > "$R/tr_mu_job0.txt" || true
if [ -s "$R/tr_single_u0.txt" ] && cmp -s "$R/tr_single_u0.txt" "$R/tr_mu_job0.txt"; then
  echo "TRACE job0 IDENTICAL events=$(wc -l < "$R/tr_single_u0.txt")"
else echo "TRACE job0 DIFFERS"; diff "$R/tr_single_u0.txt" "$R/tr_mu_job0.txt" | head -5; fi
# job 1 vs user 1 alone: same events and data at a constant cycle offset (output events only; PC requests carry no cycle)
awk '$2==1 && $4!="RQ"{ $2=""; print }' "$R/mu.log" | awk '{c=$2; $2=""; print c, $0}' > "$R/tr_mu_job1.txt" || true
awk '$1=="SVCRS_TR" && $4!="RQ"{ $2=""; print }' "$R/single_u1.log" | awk '{c=$2; $2=""; print c, $0}' > "$R/tr_single_u1.txt" || true
python3 - "$R/tr_single_u1.txt" "$R/tr_mu_job1.txt" <<'EOF'
import sys
a=[l.split(' ',1) for l in open(sys.argv[1]).read().splitlines()]
b=[l.split(' ',1) for l in open(sys.argv[2]).read().splitlines()]
if not a or len(a)!=len(b): print('TRACE job1 vs single_u1 DIFFERS: events %d vs %d'%(len(a),len(b))); sys.exit()
offs={int(y[0])-int(x[0]) for x,y in zip(a,b)}; same=all(x[1]==y[1] for x,y in zip(a,b))
print('TRACE job1 vs single_u1 data=%s offsets=%s events=%d'%('IDENTICAL' if same else 'DIFFERS', sorted(offs)[:4], len(a)))
EOF
