#!/bin/bash
set -eu
cd /srv/opentallas-scratch/claude/codex-cap-contract-1020
KIND=$1
test "$KIND" = wrong_rbase -o "$KIND" = late_cfg
test ! -e "$KIND"
mkdir "$KIND"
cp -a candidate/images candidate/expected_xq.mem candidate/expected_reads.mem "$KIND/"
python3 - "$KIND" <<'PY'
import sys
from pathlib import Path
kind=sys.argv[1]
c={int(l.split()[0]):int(l.split()[1],16) for l in Path('candidate/source_ctl.txt').read_text().splitlines()}
if kind=='wrong_rbase':
    # First phase real rows are in flags1; deliberately select flags0.
    c[1700] -= 16384 << (29+26)
else:
    # Positive cfg is effective in the two-edge idle window. Five edges late
    # overlaps the next phase's open FIN pairing store and must trigger F11.
    value=c.pop(1942)
    assert 1947 not in c
    c[1947]=value
Path(kind+'/source_ctl.txt').write_text(''.join(f'{t} {v:047x}\n' for t,v in sorted(c.items())))
PY
cd "$KIND"
sha256sum source_ctl.txt > program.sha256
EXE=/srv/opentallas-scratch/claude/toksim-s81-field/tools/Vtb_fullsix_trace
sha256sum "$EXE" > exe.sha256
set +e
/usr/bin/time -v -o run_time.log "$EXE" +DIR=. +OT_ROM_DIR=images > diagnostic.log 2>&1
rc=$?
set -e
echo "$rc" > simulator.exit
grep -E 'FULLSIX_SOURCE_CHECK|FULLSIX_PREPARATORY_TRACE_END' diagnostic.log
gzip -k diagnostic.log
echo "CAP_NEGATIVE_SIM_EXIT kind=$KIND rc=$rc (causal checker separate)"
