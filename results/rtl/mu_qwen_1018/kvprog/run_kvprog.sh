#!/usr/bin/env bash
# MU-KV-PROG 10-19: tb_kvprog_mu on the fleet, Verilator 5.050 (the closure daemon's).  From the repository root:
#   bash results/rtl/mu_qwen_1018/kvprog/run_kvprog.sh WORK
# Builds: b0 = MU 0 (original lprg, ownership _mu MU 0 = original); b1 = lprg_mu MU 1 + ownership _mu MU 1;
#         b5 / b6 / b7 = b1 with the ownership _mu mutants 5 (shared window) / 6 (enter re-check each go) / 7 (no re-arm).
# Cases (runs/<case>.log): PASS cases + cross-run identity (alone == together per user; MU 1 user 0 == MU 0, every
# record cycle-stamped) and the negative controls, each with its fail regex (lists in runs/summary.txt).
set -u
WORK=$1
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
D=results/rtl/mu_qwen_1018/kvprog; R=$D/runs; mkdir -p "$R" "$WORK"
verilator --version > "$R/verilator_version.txt"
SRC=$(grep '\.sv$' $D/lists/tb_kvprog_mu.f | tr '\n' ' ')
build() { # name LMU OMU OMUT
  verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 \
    --top-module tb_kvprog_mu -GLMU=$2 -GOMU=$3 -GOMUT=$4 -Mdir "$WORK/$1" -o sim $SRC > "$WORK/$1.build.log" 2>&1 \
    || { echo "BUILD FAIL $1"; tail -40 "$WORK/$1.build.log"; }
}
build b0 0 0 0 & build b1 1 1 0 & build b5 1 1 5 & build b6 1 1 6 & build b7 1 1 7 & wait
for b in b0 b1 b5 b6 b7; do tail -3 "$WORK/$b.build.log" | sed "s/^/[$b] /"; done
run() { # case build args...
  local c=$1 b=$2; shift 2
  { echo "# case $c build $b args $* host $(hostname) $(date -Is) commit $(cat SOURCE_COMMIT 2>/dev/null)";
    ( cd $D && "$WORK/$b/sim" "$@" ); echo "# exit $?"; } > "$R/$c.log" 2>&1
}
run mu0_u0  b0 +USERS=1 +ROOTS=0 +OWNCHK=1 &
run mu1_u0  b1 +USERS=1 +ROOTS=0 +OWNCHK=1 &
run mu1_all b1 +USERS=15 +ROOTS=1 +OWNCHK=1 &
run mu1_a0  b1 +USERS=1 +ROOTS=1 +OWNCHK=1 &
run mu1_a1  b1 +USERS=2 +ROOTS=1 +OWNCHK=1 &
run mu1_a2  b1 +USERS=4 +ROOTS=1 +OWNCHK=1 &
run mu1_a3  b1 +USERS=8 +ROOTS=1 +OWNCHK=1 &
run m_shared    b0 +USERS=15 +ROOTS=1 +OWNCHK=1 &
run m_epochbits b1 +USERS=15 +ROOTS=1 +OWNCHK=1 +XMUT=2 &
run m_prevowner b1 +USERS=15 +ROOTS=1 +OWNCHK=1 +XMUT=1 &
run m_envelope  b1 +USERS=15 +ROOTS=1 +OWNCHK=1 +CAL=kvprog_cal_bad.hex &
run m_own5 b5 +USERS=15 +ROOTS=1 +OWNCHK=1 &
run m_own6 b6 +USERS=15 +ROOTS=1 +OWNCHK=1 &
run m_own7 b7 +USERS=15 +ROOTS=1 +OWNCHK=1 &
wait
python3 - "$R" <<'PY'
import re, sys, pathlib
R = pathlib.Path(sys.argv[1]); out = []
def h(c):
    t = (R / f'{c}.log').read_text(); d = {}
    for m in re.finditer(r'HASH u(\d) writer (\w+) attention (\w+)', t): d[int(m[1])] = (m[2], m[3])
    m = re.search(r'HASH own (\w+)', t); d['own'] = m[1] if m else None
    return t, d
ok = True
for c in ('mu0_u0', 'mu1_u0', 'mu1_all', 'mu1_a0', 'mu1_a1', 'mu1_a2', 'mu1_a3'):
    t, _ = h(c); p = 'PASS KVPROG_MU' in t; ok &= p
    out.append(f'{c}: {"PASS" if p else "FAIL"} {(re.findall(r"^(?:PASS|FAIL) KVPROG_MU.*$", t, re.M) or ["(no verdict)"])[0]}')
_, a = h('mu1_all'); _, m0 = h('mu0_u0'); _, m1 = h('mu1_u0')
for u in range(4):
    _, x = h(f'mu1_a{u}'); e = x.get(u) == a.get(u) and a.get(u) is not None; ok &= e
    out.append(f'identity user {u}: alone == together (writer + attention records, cycle-stamped): {e}')
e = m0.get(0) == m1.get(0) == a.get(0) and m0.get(0) is not None; ok &= e
out.append(f'identity user 0: MU 0 == MU 1 alone == MU 1 together: {e}')
e = m0['own'] == m1['own'] and m0['own'] is not None; ok &= e
out.append(f'identity ownership (single-user roots): MU 0 == MU 1 every edge: {e}')
NEG = {'m_shared': r'layer programme fault code 08', 'm_epochbits': r'FAIL cyc \d+: (writer slot identity|attention request|layer programme fault)',
       'm_prevowner': r'FAIL cyc \d+: (attention calendar generator fault|writer slot identity|attention request)', 'm_envelope': r'FAIL cyc \d+: attention programme fault',
       'm_own5': r'ownership calendar fault code 04', 'm_own6': r'ownership calendar fault code 08',
       'm_own7': r'(not natively reserved|not in native mode|ownership calendar fault code 10)'}
for c, rx in NEG.items():
    t, _ = h(c); f = 'FAIL KVPROG_MU' in t and re.search(rx, t) is not None; ok &= f
    out.append(f'{c}: {"FAIL as required" if f else "NOT FAILED"} regex /{rx}/ {(re.findall(r"^FAIL cyc.*$", t, re.M) or ["-"])[0]}')
out.append('ALL ' + ('PASS' if ok else 'FAIL'))
(R / 'summary.txt').write_text('\n'.join(out) + '\n'); print('\n'.join(out))
PY
